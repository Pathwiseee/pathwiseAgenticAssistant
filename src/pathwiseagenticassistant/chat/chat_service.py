from collections.abc import AsyncIterator
from typing import Literal

from agents import InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered
from pydantic import BaseModel, Field

from pathwiseagenticassistant.agents.front_door.intake_agent import intake_user_request
from pathwiseagenticassistant.agents.front_door.tutor_agent import run_tutor_agent
from pathwiseagenticassistant.agents.pathwiseWorkflow import research_and_compile_stream
from pathwiseagenticassistant.schemas import Source
from pathwiseagenticassistant.storage.db import attach_lesson_to_chat, get_chat, get_chat_session, get_lesson, save_lesson

# Overview Description: Handles one user message inside one chat
#
#   chat has lesson? ──yes──> tutor (with chat session)              ──> answer
#          │ no
#          ▼
#   intake (with chat session) ──> research_and_compile_stream ──> save + attach lesson ──> lesson_ready
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
        try:
            answer = await run_tutor_agent(get_lesson(chat.lesson_id), message, session)
        except (InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered) as e:
            yield ChatEvent(kind="answer", message=e.guardrail_result.output.output_info.reason)
            return
        yield ChatEvent(kind="answer", message=answer.answer, sources=answer.sources)
        return

    yield ChatEvent(kind="status", message="Understanding your learning request")
    # TODO: intake always returns a LearningRequest today, so it can't ask a clarifying
    # question back; that needs a LearningRequest | ClarifyingQuestion output type
    try:
        request = await intake_user_request(chat.topic, message, session)
    except InputGuardrailTripwireTriggered as e:
        yield ChatEvent(kind="answer", message=e.guardrail_result.output.output_info.reason)
        return
    yield ChatEvent(
        kind="status",
        message=f"Learning {request.topic} ({request.level.value}, {request.tech_stack}) for: {request.goal}",
    )

    async for event in research_and_compile_stream(request, max_plan_revisions, max_write_revisions):
        if event.result is None:
            yield ChatEvent(kind="status", message=f"{event.stage}: {event.message}")
            continue
        lesson_id = save_lesson(event.result)
        attach_lesson_to_chat(chat_id, lesson_id)
        yield ChatEvent(kind="lesson_ready", message=event.message, lesson_id=lesson_id)
