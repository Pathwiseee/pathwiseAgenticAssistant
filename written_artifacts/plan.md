# Pathwise Local App Plan

## Goal

Run Pathwise as a local, single-user Gradio app:

- Chats are stored in a local SQLite database.
- Each chat has its own tutor memory.
- Compiled lessons live in a lesson directory and can be opened from there; the lesson view is optional and can stay hidden.

The existing agents and orchestrators (`intake_agent`, `ResearchManager`, `compilation_orchestrator`, `pathwiseWorkflow`) stay as they are. This plan only adds pieces around them.

## Architecture

### Layers

```
Gradio UI (ui/app.py)
   │  one call per user message
   ▼
Chat turn handler (chat/turn.py)        ← owns SQLiteSession(chat_id)
   │                         │
   │ no lesson yet           │ chat has a lesson
   ▼                         ▼
intake_user_request        tutor agent
  (session=chat)             (session=chat)
   │ route = research
   ▼
run_pathwise_stream  →  research → compilation   (stateless, no session)
   │ done
   ▼
storage: save lesson, link chat → lesson
```

### Where the session lives

- `SQLiteSession` is created by the **chat turn handler**, one per chat (`session_id = chat_id`).
- It is passed only to the agents that talk to the user: **intake** and **tutor**.
- Research and compilation agents **never** receive the session. Their internal prompts would otherwise end up in the user's chat history and in the tutor's context.
- Agents stay stateless. A "tutor instance per chat" is simply `create_tutor_agent(lesson)` plus that chat's session, built again for each message.

### Chat ↔ lesson relationship

- A chat is linked to **at most one** lesson.
- A new chat starts with intake. When intake routes to `research`, the chat streams compilation progress, saves the lesson and links it to the chat. Messages after that go to the tutor.
- Picking a lesson in the directory opens its chat, or starts a new chat linked to that lesson.

## Storage

### Database file

A single file, `./data/pathwise.db` (git-ignored). `SQLiteSession` stores its message tables in the same file.

### Tables

| Table | Columns | Notes |
|---|---|---|
| `chats` | `id TEXT PK, title TEXT, lesson_id TEXT NULL, created_at` | `title` defaults to the first message, then to the lesson topic |
| `lessons` | `id TEXT PK, topic TEXT, compiled_json TEXT, created_at` | `CompiledLesson.model_dump_json()` |
| `agent_sessions`, `agent_messages` | managed by `SQLiteSession` | keyed by `chat_id` |

### Module: `storage/db.py`

- `init_db()`
- `create_chat()`, `list_chats()`, `get_chat(id)`, `link_lesson(chat_id, lesson_id)`
- `save_lesson(compiled) -> id`, `list_lessons()`, `get_lesson(id) -> CompiledLesson`
- `get_session(chat_id) -> SQLiteSession`

## Changes to Existing Code

### Schemas

- Add `route: RouteEnum` to `LearningRequest`, so intake can choose between `research` and `tutor`.

### Intake

- `intake_user_request(topic, user_prompt, session=None)` passes `session` to `Runner.run`, so clarifying questions carry over between messages.
- Open question: if intake still needs clarification, it has to return a question to the user rather than a `LearningRequest` (for example `LearningRequest | ClarifyingQuestion`).

### Tutor grounding

- `create_tutor_agent` currently uses `FileSearchTool` with an OpenAI vector store, and nothing creates those vector stores yet.
- Recommended: put the lesson content and source summaries directly into the tutor's instructions (`create_tutor_agent(lesson: CompiledLesson)`). Everything then stays local, and one lesson easily fits in context.
- Alternative: keep `FileSearchTool` and add a step that uploads each compiled lesson to a vector store, storing `vector_store_id` on `lessons`.

### Workflow

- `run_pathwise_stream` is unchanged. It is called by the turn handler, not by the UI directly.

## Chat Turn Handler

### Module: `chat/turn.py`

```python
async def handle_turn(chat_id: str, message: str) -> AsyncIterator[TurnEvent]:
    session = get_session(chat_id)
    chat = get_chat(chat_id)
    if chat.lesson_id:
        # tutor path
        tutor = create_tutor_agent(get_lesson(chat.lesson_id))
        result = await Runner.run(tutor, message, session=session)
        yield answer
    else:
        # intake → compile path
        request = await intake_user_request(..., session=session)
        async for event in run_pathwise_stream(request):
            yield status event
        save_lesson + link_lesson
        yield lesson-ready event
```

- `run_pathwise_stream` would need to accept an already-parsed `LearningRequest`; alternatively, split intake out of it.
- Compilation status lines are shown in the UI but are not written to the agent session.

## UI

### Layout

```
┌──────────────┬───────────────────────────────────┬──────────────────────────┐
│ SIDEBAR      │ CHAT                              │ LESSON PANEL (toggle)    │
│              │                                   │                          │
│ [+ New chat] │ you: I want to learn Kafka for    │ ▸ Kafka for Java/Spring  │
│              │      my Spring job                │                          │
│ Chats        │ ⏳ intake: Kafka (beginner, ...)   │  render(UIComponent)     │
│ ● Kafka      │ ⏳ researching: 6 sources          │                          │
│ ○ React hooks│ ⏳ writing: draft 1 ...            │ ▸ Plan / Reviews /       │
│              │ ✅ Lesson verified → [Open lesson]│   Verification accordions│
│ Lessons      │ you: what's a consumer group?     │                          │
│ ▸ Kafka      │ tutor: ... [source: confluent.io] │                          │
│ ▸ React hooks│                                   │                          │
│              │ [ message box              ][Send]│                          │
│              │ [Show lesson ☐]                   │                          │
└──────────────┴───────────────────────────────────┴──────────────────────────┘
```

### Components

- `gr.State`: `active_chat_id` only; everything else is read from SQLite.
- `gr.Sidebar`: a "New chat" button, a chat list (`gr.Radio`) and a lesson directory (`gr.Radio`).
- `gr.Chatbot` + `gr.Textbox`: the send handler is an async generator over `handle_turn`.
- Lesson panel: `gr.Column(visible=False)`, toggled by a checkbox. Inside it, the existing `@gr.render` + `render(UIComponent)` and the plan/review/verification accordions from `ui/renderer.py`.

### Events

- **Select chat:** load its history from the session into the chatbot; load the linked lesson into the panel, if there is one.
- **Select lesson:** open the chat linked to that lesson, or create one.
- **Send:** stream from `handle_turn`; keep the send button disabled while compiling.

## Build Order

1. `storage/db.py` + `init_db`; add `data/` to `.gitignore`.
2. `route` field on `LearningRequest`; `session` parameter on `intake_user_request`.
3. Tutor grounding change (`create_tutor_agent(lesson)`).
4. `chat/turn.py`, tutor path first.
5. `ui/app.py` skeleton: sidebar, chat, send → tutor path.
6. Connect the compile path: stream status, save the lesson, link it to the chat.
7. Move the lesson panel and accordions over from `ui/renderer.py`.

## Open Questions

- Tutor grounding: inline the lesson content (recommended) or use a vector store?
- How intake returns a clarifying question instead of a `LearningRequest`.
- Should a chat be allowed to compile a second lesson, or should the user start a new chat for it?
