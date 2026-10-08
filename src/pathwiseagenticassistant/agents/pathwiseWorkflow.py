from collections.abc import AsyncIterator

from agents import SQLiteSession

from pathwiseagenticassistant.agents.compilation.compilation_orchestrator import compile_lesson_stream
from pathwiseagenticassistant.agents.front_door.intake_agent import intake_user_request
from pathwiseagenticassistant.agents.research.research_manager import ResearchManager
from pathwiseagenticassistant.schemas import CompilationEvent, CompiledLesson
from pathwiseagenticassistant.tools.summarizer import summarizer_agent
from pathwiseagenticassistant.tools.web_search_agent import web_search_agent

# Overview Description: Runs the whole Pathwise pipeline for one user request
#
#   intake agent ──> research manager ──> compilation orchestrator ──> CompiledLesson
#   (LearningRequest)   (ResearchPack)       (CompilationEvents)
#
# Each sub-workflow opens its own trace, so this orchestrator only sequences them
# and forwards their progress as one event stream.

#Input: topic + free-text user request
#Output: stream of CompilationEvents, the last one carrying the CompiledLesson


async def run_pathwise_stream(
    topic: str,
    user_request: str,
    max_plan_revisions: int = 1,
    max_write_revisions: int = 1,
    session: SQLiteSession | None = None,
) -> AsyncIterator[CompilationEvent]:
    # Only intake sees the chat session; research/compilation stay stateless so
    # their internal prompts never land in the user's chat history
    yield CompilationEvent(stage="intake", message="Understanding your learning request")
    request = await intake_user_request(topic, user_request, session)
    yield CompilationEvent(
        stage="intake",
        message=f"Learning {request.topic} ({request.level.value}, {request.tech_stack}) for: {request.goal}",
    )

    # Research takes a few minutes and has no event stream, so it reports start and finish only
    yield CompilationEvent(stage="researching", message="Gathering and summarizing sources")
    research_pack = await ResearchManager(web_search_agent, summarizer_agent).run(request)
    yield CompilationEvent(stage="researching", message=f"Found {len(research_pack.summaries)} sources")

    async for event in compile_lesson_stream(
        research_pack,
        max_plan_revisions=max_plan_revisions,
        max_write_revisions=max_write_revisions,
    ):
        yield event


async def run_pathwise(topic: str, user_request: str, **kwargs) -> CompiledLesson:
    async for event in run_pathwise_stream(topic, user_request, **kwargs):
        if event.result is not None:
            return event.result
    raise RuntimeError("workflow ended without a result")
