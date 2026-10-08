from collections.abc import AsyncIterator
from typing import Literal

from pydantic import BaseModel

from pathwiseagenticassistant.agents.front_door.intake_agent import intake_user_request
from pathwiseagenticassistant.agents.pathwiseWorkflow import research_and_compile_stream
from pathwiseagenticassistant.storage.db import get_chat, get_chat_session, attach_lesson_to_chat, save_lesson

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
        # TODO: tutor path. Blocked on tutor grounding: create_tutor_agent needs a
        # vector store id nothing creates yet (see plan.md "Tutor grounding")
        raise NotImplementedError("tutor path not wired yet")

    yield ChatEvent(kind="status", message="Understanding your learning request")
    # TODO: intake always returns a LearningRequest today, so it can't ask a clarifying
    # question back; that needs a LearningRequest | ClarifyingQuestion output type
    request = await intake_user_request(chat.topic, message, session)
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
