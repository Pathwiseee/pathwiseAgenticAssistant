# Pathwise Local App Plan

## Goal

Run Pathwise as a local, single-user Gradio app:

- Chats are stored in a local SQLite database.
- Each chat has its own tutor memory.
- Compiled lessons live in a lesson directory and can be opened from there; the lesson view is optional and can stay hidden.

## Status

| Part | Status | Where |
|---|---|---|
| Storage (chats, lessons, sessions) | Done | `storage/db.py` |
| Intake with chat session | Done | `agents/front_door/intake_agent.py` |
| Tutor grounded in lesson + research pack | Done | `agents/front_door/tutor_agent.py` |
| Input/output guardrails | Done | `guardrails.py` |
| Research + compilation pipeline | Done | `agents/pathwiseWorkflow.py` |
| Chat service (one call per user message) | Done | `chat/chat_service.py` |
| Chat history for display | Done | `storage/db.py` |
| Chat UI | Done (tested in a browser with a stubbed chat service; not yet against the real API) | `ui/app.py` |
| Intake clarifying questions | Open | see Open Questions |

Everything below the UI is tested offline with stubbed agents, not yet against the real API.

## Architecture

### Layers

```
Gradio UI (ui/app.py)                          ← NEXT: only calls chat_service + storage
   │  one call per user message
   ▼
chat_service.respond_to_message(chat_id, message)   ← owns SQLiteSession(chat_id)
   │                                   │
   │ chat has no lesson                │ chat has a lesson
   ▼                                   ▼
_intake_then_build_lesson          _answer_with_tutor
  intake (session=chat)              tutor (session=chat), grounded in the lesson
   │                                   │
   ▼                                   ▼
research_and_compile_stream        answer + sources
  (pathwiseWorkflow, no session)
   │ done
   ▼
save_lesson + attach_lesson_to_chat
```

### Where the session lives

- `SQLiteSession` is created per message by `respond_to_message`, one per chat (`session_id = chat_id`).
- It is passed only to the agents that talk to the user: **intake** and **tutor**.
- Research and compilation agents **never** receive the session. Their internal prompts would otherwise end up in the user's chat history and in the tutor's context.
- Agents stay stateless. A "tutor instance per chat" is `create_tutor_agent(lesson)` plus that chat's session, built again for each message.

### Chat ↔ lesson relationship

- A chat is linked to **at most one** lesson.
- A new chat starts with intake. Intake runs the pipeline, which saves the lesson and attaches it to the chat. Messages after that go to the tutor.
- Routing is by `chat.lesson_id`, not by intake, so `LearningRequest` does not need a `route` field.

## Storage (done)

A single file, `./data/pathwise.db` (git-ignored). `SQLiteSession` stores its message tables in the same file.

| Table | Columns | Notes |
|---|---|---|
| `chats` | `id TEXT PK, title TEXT, topic TEXT, lesson_id TEXT NULL, created_at` | `id` is a uuid; `title` and `topic` are set from the topic at creation |
| `lessons` | `id TEXT PK, topic TEXT, compiled_json TEXT, created_at` | `CompiledLesson.model_dump_json()` |
| `agent_sessions`, `agent_messages` | managed by `SQLiteSession` | keyed by `chat_id` |

`storage/db.py`: `init_db`, `create_chat(topic)`, `list_chats`, `get_chat`, `attach_lesson_to_chat`, `get_chat_session`, `save_lesson`, `list_lessons`, `get_lesson`.

## Chat Service (done)

`chat/chat_service.py` is the only thing the UI calls to run agents.

```python
async def respond_to_message(chat_id: str, message: str) -> AsyncIterator[ChatEvent]
```

It streams `ChatEvent`s:

| `kind` | Meaning | Extra fields |
|---|---|---|
| `status` | Progress line (intake, researching, planning, writing, …) | — |
| `answer` | A reply to show as a chat bubble: tutor answer, or a guardrail's reason for blocking | `sources` (tutor only) |
| `lesson_ready` | Lesson compiled, saved and attached to the chat | `lesson_id` |

Status lines are **not** stored anywhere; they are only for the live view.

## UI (next)

The current `ui/renderer.py` is a one-shot form (topic/level/stack/goal → compile) with no chats or storage. It stays as a dev tool. The chat app is a new file, `ui/app.py`, that reuses its pieces.

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
- `gr.Sidebar`: a "New chat" button, a chat list (`gr.Radio` over `list_chats()`) and a lesson directory (`gr.Radio` over `list_lessons()`).
- `gr.Chatbot` + `gr.Textbox`: the send handler is an async generator over `respond_to_message`.
- Lesson panel: `gr.Column(visible=False)`, toggled by a checkbox. Inside it, the existing `@gr.render` + `ui/components.render(UIComponent)` and the plan/review/verification accordions (`format_reviews`, `format_verifications` from `ui/renderer.py`).

### Events: what each one calls

| Event | Calls | UI update |
|---|---|---|
| App start | `init_db()`, `list_chats()`, `list_lessons()` | Fill sidebar |
| New chat | `create_chat(topic)` | Set `active_chat_id`, empty chatbot, refresh chat list |
| Select chat | `get_chat(id)`, `get_chat_messages(id)`, `get_lesson(lesson_id)` if linked | Fill chatbot; fill lesson panel |
| Select lesson | find its chat, or `create_chat(topic)` + `attach_lesson_to_chat` | Same as select chat |
| Send | `respond_to_message(active_chat_id, text)` | See below |

**Send, per `ChatEvent`:**

- Before streaming: append the user's message to the chatbot; disable the send button.
- `status` → show as a temporary progress line under the user's message (replace it on each new status).
- `answer` → append an assistant bubble; render `sources` as markdown links under it.
- `lesson_ready` → append "Lesson ready" bubble, load `get_lesson(lesson_id)` into the lesson panel, refresh the lesson directory.
- After streaming: re-enable the send button.

### Gaps to close before the UI works

1. **`get_chat_messages(chat_id)` in `storage/db.py`** (needed for "Select chat").
   The session stores items for the model, not for display:
   - User messages to intake are stored as `"Topic: X, User Prompt: ..."`.
   - Intake and tutor replies are stored as JSON (`LearningRequest`, `Answer`).
   `get_chat_messages` reads `get_chat_session(id).get_items()` and returns `[{role, content}]` for `gr.Chatbot`: strip the `Topic:` prefix, show `Answer.answer` (+ sources), turn a `LearningRequest` into "Learning Kafka (beginner, Java) for: job".
2. **New chat needs a topic.** `create_chat(topic)` requires one. Simplest: a topic textbox next to "New chat". Alternative: create the chat on the first message and use that message as the topic.
3. **Find the chat for a lesson** (needed for "Select lesson"): `get_chat_for_lesson(lesson_id) -> Chat | None` in `storage/db.py`.
4. **Entry point:** point `main()` in `__init__.py` at `ui/app.py` so `uv run pathwiseagenticassistant` launches the chat app (it currently prints "Hello").

## Build Order (remaining)

1. `get_chat_messages`, `get_chat_for_lesson` in `storage/db.py`.
2. `ui/app.py` skeleton: sidebar (new chat + chat list), chatbot, send → `respond_to_message`. Test with a chat that already has a lesson (tutor path) first, since it is fast.
3. Compile path in the UI: status lines, `lesson_ready`, send button disabled while compiling.
4. Lesson panel + accordions, moved over from `ui/renderer.py`.
5. Lesson directory: select lesson → open or create its chat.
6. `main()` entry point.
7. First real end-to-end run against the API (check the guardrail model name `gpt-6-luna` works).

## Open Questions

- How intake returns a clarifying question instead of a `LearningRequest` (e.g. `LearningRequest | ClarifyingQuestion`). Until then, a vague first message goes straight to compiling.
- Should a chat be allowed to compile a second lesson, or should the user start a new chat for it?
- Should the learner's level/stack (from `LearningRequest`) be saved with the lesson so the tutor gets it in its prompt, not only through the chat history?
