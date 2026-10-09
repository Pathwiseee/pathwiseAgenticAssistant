# Pathwise Local App Plan

## Goal

Run Pathwise as a local, single-user Gradio app:

- Chats are stored in a local SQLite database.
- Each chat has its own tutor memory.
- Compiled lessons live in a lesson directory and can be opened from there; the lesson view is optional and can stay hidden.
- A help box answers questions about Pathwise itself from an FAQ.

## Status

_Last updated 2026-10-09 (up to commit `a0f494c`)._

| Part | Status | Where |
|---|---|---|
| Storage (chats, lessons, sessions, chat history for display) | Done | `storage/db.py` |
| Intake with chat session | Done | `agents/front_door/intake_agent.py` |
| Tutor grounded in lesson + research pack | Done | `agents/front_door/tutor_agent.py` |
| Input/output guardrails | Done | `guardrails.py` |
| Research (searches, judging, summaries run in parallel) | Done | `agents/research/research_manager.py` |
| Research + compilation pipeline | Done | `agents/pathwiseWorkflow.py` |
| Chat service (one call per user message) | Done | `chat/chat_service.py` |
| Chat UI | Done | `ui/app.py` |
| Lesson panel (shared by chat UI and dev form) | Done | `ui/renderer.py` → `lesson_panel()` |
| Help box (RAG over the FAQ) | Done, needs one-time setup | `agents/front_door/help_agent.py`, `knowledge/pathwise_faq.md` |
| Entry point | Done | `uv run pathwiseagenticassistant` → `ui/app.py` |
| **First real end-to-end run** | **Next** | see Next Steps |
| Intake clarifying questions | Open | see Open Questions |

**Testing so far:** the chat UI was tested in a browser with a stubbed chat service. Everything below it was tested offline with stubbed agents. Nothing has run end to end against the real API yet.

## How to Run

1. `.env` needs `OPENAI_API_KEY`.
2. Help box only, once: `uv run python scripts/build_faq_store.py`, then add the printed `PATHWISE_FAQ_VECTOR_STORE_ID=...` line to `.env`. (Not set in the local `.env` yet; until it is, the help box answers "Something went wrong".)
3. `uv run pathwiseagenticassistant`
4. Dev form for building one lesson without chats: `uv run python -m pathwiseagenticassistant.ui.renderer`

## Architecture

### Layers

```
Gradio UI (ui/app.py)                    only calls chat_service, storage, ask_help
   │                                        │
   │ one call per user message              │ help box
   ▼                                        ▼
chat_service.respond_to_message         help_agent.ask_help(question)
  (chat_id, message)                      FileSearchTool → FAQ vector store (OpenAI)
  owns SQLiteSession(chat_id)             no session, no chat
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
- It is passed only to the agents that talk to the user in a chat: **intake** and **tutor**.
- Research and compilation agents **never** receive the session. Their internal prompts would otherwise end up in the user's chat history and in the tutor's context.
- The help agent has no session: each help question is answered on its own.
- Agents stay stateless. A "tutor instance per chat" is `create_tutor_agent(lesson)` plus that chat's session, built again for each message.

### Chat ↔ lesson relationship

- A chat is linked to **at most one** lesson.
- A new chat starts with intake. Intake runs the pipeline, which saves the lesson and attaches it to the chat. Messages after that go to the tutor.
- Routing is by `chat.lesson_id`, not by intake, so `LearningRequest` does not need a `route` field.

## Storage

A single file, `./data/pathwise.db` (git-ignored). `SQLiteSession` stores its message tables in the same file.

| Table | Columns | Notes |
|---|---|---|
| `chats` | `id TEXT PK, title TEXT, topic TEXT, lesson_id TEXT NULL, created_at` | `id` is a uuid; `title` and `topic` are set from the topic at creation |
| `lessons` | `id TEXT PK, topic TEXT, compiled_json TEXT, created_at` | `CompiledLesson.model_dump_json()` |
| `agent_sessions`, `agent_messages` | managed by `SQLiteSession` | keyed by `chat_id` |

`storage/db.py`:

- Chats: `init_db`, `create_chat(topic)`, `list_chats`, `get_chat`, `get_chat_for_lesson`, `attach_lesson_to_chat`
- Sessions: `get_chat_session`, `get_chat_messages` (session items turned into `{role, content}` for `gr.Chatbot`: strips the intake `Topic: ...` prefix, shows `Answer.as_markdown()` and `LearningRequest.summary()`)
- Lessons: `save_lesson`, `list_lessons`, `get_lesson`

## Chat Service

`chat/chat_service.py` is the only thing the UI calls to run chat agents.

```python
async def respond_to_message(chat_id: str, message: str) -> AsyncIterator[ChatEvent]
```

| `kind` | Meaning | Extra fields |
|---|---|---|
| `status` | Progress line (intake, researching, planning, writing, …) | — |
| `answer` | A reply to show as a chat bubble: tutor answer, or a guardrail's reason for blocking | `sources` (tutor only) |
| `lesson_ready` | Lesson compiled, saved and attached to the chat | `lesson_id` |

Status lines are **not** stored anywhere; they are only for the live view.

## UI (built)

### Layout

```
┌──────────────────┬───────────────────────────────────┬──────────────────────────┐
│ SIDEBAR          │ CHAT                              │ LESSON PANEL (toggle)    │
│                  │                                   │                          │
│ Topic for a new  │ you: I want to learn Kafka for    │ ▸ Lesson Plan            │
│ chat: [Kafka   ] │      my Spring job                │ ▸ Plan Reviews           │
│ [+ New chat]     │ ⏳ researching: Found 6 sources    │ ▸ Page Verification      │
│                  │ Lesson ready. Tick 'Show lesson'  │                          │
│ Chats            │ you: what's a consumer group?     │  render(UIComponent)     │
│ ● Kafka          │ tutor: ... Sources: [confluent]   │                          │
│ ○ React hooks    │                                   │                          │
│                  │ [ Message                   ][➤] │                          │
│ Lessons          │ [Show lesson ☐]                   │                          │
│ ○ Kafka          │                                   │                          │
├──────────────────┴───────────────────────────────────┴──────────────────────────┤
│ ▸ Help: ask about Pathwise   [ e.g. How long does a lesson take?         ][➤]  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Behaviour

- `gr.State` holds only the active chat id; everything else is read from SQLite through `show_chat(chat_id)`.
- **New chat:** needs the topic box filled (warns otherwise) → `create_chat(topic)`.
- **Select chat:** `show_chat` loads history (`get_chat_messages`) and the linked lesson.
- **Select lesson:** opens the chat linked to it (`get_chat_for_lesson`), or creates one if the lesson was saved but never attached.
- **Send:** locks message box, topic, new chat and both lists while answering. `status` events show as one temporary `⏳` line; `answer` adds a bubble with sources; `lesson_ready` adds "Lesson ready" and reloads the sidebar and lesson panel. Any exception shows "⚠️ Something went wrong" and unlocks the controls.
- **Help box:** `ask_help(question)`; a guardrail block shows its reason.

## Next Steps

1. **First real end-to-end run** with `uv run pathwiseagenticassistant`: new chat → lesson built → tutor question → reopen the chat after restarting the app. Check in particular:
   - the guardrail model name `gpt-6-luna` (`GUARDRAIL_MODEL` in `guardrails.py`) exists for this API key. If not, every guardrail fails closed and **every message is blocked**.
   - `get_chat_messages` with real session items.
   - research with the new parallel calls stays under the API rate limits.
2. **Set up the FAQ store** (How to Run, step 2) and try the help box.
3. **Intake clarifying questions** (Open Questions).

## Known Issues

- **Parallel research has no limit or error isolation.** `asyncio.gather` runs every search/judge/summary call at once, and one failure fails the whole research step. If rate limits show up, add an `asyncio.Semaphore`; consider `return_exceptions=True` and skipping failed articles.
- **The help box needs a vector store id** that isn't in `.env` yet; `os.environ[...]` raises until it is (shown to the user as "Something went wrong").

## Fixed

- **Blocked messages no longer stay in the chat session** (2026-10-09). The SDK saves the user's message even when a guardrail blocks it, so the tutor would have read blocked text on the next message. `chat_service._forget_since` now rolls the session back to its length before the blocked run.
- **`get_chat_messages` no longer breaks on unexpected items** (2026-10-09). Refusals and non-JSON replies are shown as plain text; items with no text are skipped.

## Open Questions

- How intake returns a clarifying question instead of a `LearningRequest` (e.g. `LearningRequest | ClarifyingQuestion`). Until then, a vague first message goes straight to compiling.
- Should a chat be allowed to compile a second lesson, or should the user start a new chat for it?
- Should the learner's level/stack (from `LearningRequest`) be saved with the lesson so the tutor gets it in its prompt, not only through the chat history?
