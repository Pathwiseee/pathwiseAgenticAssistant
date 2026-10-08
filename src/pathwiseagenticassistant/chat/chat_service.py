from collections.abc import AsyncIterator
from typing import Literal

from agents import InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered, SQLiteSession
from pydantic import BaseModel, Field

from pathwiseagenticassistant.agents.front_door.intake_agent import intake_user_request
from pathwiseagenticassistant.agents.front_door.tutor_agent import run_tutor_agent
from pathwiseagenticassistant.agents.pathwiseWorkflow import research_and_compile_stream
from pathwiseagenticassistant.schemas import Source
from pathwiseagenticassistant.storage.db import Chat, attach_lesson_to_chat, get_chat, get_chat_session, get_lesson, save_lesson

# Overview Description: Handles one user message inside one chat
#
#   respond_to_message: chat has lesson?
#     ├─ yes ─> _answer_with_tutor:        tutor (with chat session) ──> answer
#     └─ no ──> _intake_then_build_lesson: intake (with chat session) ──> research_and_compile_stream
#                                           ──> save + attach lesson ──> lesson_ready
#
# The UI creates chats with storage.db.create_chat(topic) and calls this for every
# message. Only intake and tutor see the SQLiteSession; research/compilation run
# stateless so their internal prompts never land in the chat history.

#Input: existing chat id + the user's message
#Output: stream of ChatEvents for the UI


class ChatEvent(BaseModel):
    kind: Literal["status", "answer", "lesson_ready"]
    message: str
    lesson_id: str | None = None  # only set on "lesson_ready"
    sources: list[Source] = Field(default_factory=list)  # only set on "answer" from the tutor


async def respond_to_message(
    chat_id: str,
    message: str,
    *,
    max_plan_revisions: int = 1,  # updatable by settings later on
    max_write_revisions: int = 1,
) -> AsyncIterator[ChatEvent]:
    chat = get_chat(chat_id)
    session = get_chat_session(chat_id)

    if chat.lesson_id:
        steps = _answer_with_tutor(chat, message, session)
    else:
        steps = _intake_then_build_lesson(chat, message, session, max_plan_revisions, max_write_revisions)
    async for event in steps:
        yield event


# ---------- steps ----------

async def _answer_with_tutor(chat: Chat, message: str, session: SQLiteSession) -> AsyncIterator[ChatEvent]:
    try:
        answer = await run_tutor_agent(get_lesson(chat.lesson_id), message, session)
    except (InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered) as e:
        yield _blocked_reply(e)
        return
    yield ChatEvent(kind="answer", message=answer.answer, sources=answer.sources)


async def _intake_then_build_lesson(
    chat: Chat,
    message: str,
    session: SQLiteSession,
    max_plan_revisions: int,
    max_write_revisions: int,
) -> AsyncIterator[ChatEvent]:
    yield ChatEvent(kind="status", message="Understanding your learning request")
    # TODO: intake always returns a LearningRequest today, so it can't ask a clarifying
    # question back; that needs a LearningRequest | ClarifyingQuestion output type
    try:
        request = await intake_user_request(chat.topic, message, session)
    except InputGuardrailTripwireTriggered as e:
        yield _blocked_reply(e)
        return
    yield ChatEvent(kind="status", message=request.summary())

    # No session past this point: research/compilation prompts stay out of the chat history
    async for event in research_and_compile_stream(request, max_plan_revisions, max_write_revisions):
        if event.result is None:
            yield ChatEvent(kind="status", message=f"{event.stage}: {event.message}")
            continue
        lesson_id = save_lesson(event.result)
        attach_lesson_to_chat(chat.id, lesson_id)
        yield ChatEvent(kind="lesson_ready", message=event.message, lesson_id=lesson_id)


def _blocked_reply(e: InputGuardrailTripwireTriggered | OutputGuardrailTripwireTriggered) -> ChatEvent:
    """Turn a tripped guardrail into a chat reply carrying the judge's user-safe reason."""
    return ChatEvent(kind="answer", message=e.guardrail_result.output.output_info.reason)
