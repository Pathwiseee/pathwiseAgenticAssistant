from collections.abc import AsyncIterator

from pathwiseagenticassistant.agents.compilation.compilation_orchestrator import compile_lesson_stream
from pathwiseagenticassistant.agents.research.research_manager import ResearchManager
from pathwiseagenticassistant.schemas import CompilationEvent, LearningRequest
from pathwiseagenticassistant.tools.summarizer import summarizer_agent
from pathwiseagenticassistant.tools.web_search_agent import web_search_agent

# Overview Description: Builds one lesson from an already-understood learning request
#
#   LearningRequest ──> research manager ──> compilation orchestrator ──> CompiledLesson
#                         (ResearchPack)        (CompilationEvents)
#
# Intake is not part of this: the caller runs it first (chat_service.respond_to_message)
# or builds the LearningRequest from form fields (ui/renderer.py). Research and
# compilation never see the chat session, so their internal prompts stay out of chat history.
# Each sub-workflow opens its own trace, so this only sequences them and forwards
# their progress as one event stream.

#Input: LearningRequest
#Output: stream of CompilationEvents, the last one carrying the CompiledLesson


async def research_and_compile_stream(
    request: LearningRequest,
    max_plan_revisions: int = 1,
    max_write_revisions: int = 1,
) -> AsyncIterator[CompilationEvent]:
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
