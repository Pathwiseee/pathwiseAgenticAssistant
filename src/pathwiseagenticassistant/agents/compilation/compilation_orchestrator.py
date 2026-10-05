from collections.abc import AsyncIterator
from agents import trace

from pathwiseagenticassistant.agents.compilation.lesson_planning_agent import get_lesson_plan
from pathwiseagenticassistant.agents.compilation.lesson_reviewer_agent import LessonReview, review_lesson_plan
from pathwiseagenticassistant.agents.compilation.lesson_writing_agent import write_lesson
from pathwiseagenticassistant.agents.compilation.page_verifier_agent import PageVerification, verify_page
from pathwiseagenticassistant.agents.compilation.ui_component import UIComponent
from pathwiseagenticassistant.schemas import CompilationEvent, CompiledLesson

# Overview Description: Runs the compilation module end to end for one lesson
#
#   lesson planning ──> lesson reviewer ──(not approved)──> lesson planning (revise)
#                              │ approved / out of revisions
#                              ▼
#   lesson writing ──> page verifier ──(not passed)──> lesson writing (revise)
#                              │ passed / out of revisions
#                              ▼
#                        CompiledLesson
#
# Both loops are bounded so a picky reviewer/verifier can't spin forever;
# if revisions run out, the last draft is returned with verified=False.

#Input: topic, lesson resources (from the research module)
#Output: stream of CompilationEvents, the last one carrying the CompiledLesson



async def compile_lesson_stream(
    topic: str,
    lesson_resources: str,
    max_plan_revisions: int = 1,
    max_write_revisions: int = 1,
) -> AsyncIterator[CompilationEvent]:
    with trace("lesson_compilation"):
        yield CompilationEvent(stage="planning", message="Drafting lesson plan")
        lesson_plan = await get_lesson_plan(topic, lesson_resources)

        reviews: list[LessonReview] = []
        for attempt in range(max_plan_revisions + 1):
            yield CompilationEvent(stage="reviewing", message=f"Reviewing lesson plan (round {attempt + 1})")
            review = await review_lesson_plan(topic, lesson_plan, lesson_resources)
            reviews.append(review)
            if review.approved or attempt == max_plan_revisions:
                break
            # Only blocking issues drive a revision; suggestions would keep expanding the plan's scope
            yield CompilationEvent(stage="planning", message="Revising lesson plan to fix blocking issues")
            blocking = "\n".join(f"- {issue}" for issue in review.blocking_issues)
            lesson_plan = await get_lesson_plan(topic, lesson_resources, lesson_plan, blocking)

        lesson: UIComponent | None = None
        verifications: list[PageVerification] = []
        for attempt in range(max_write_revisions + 1):
            yield CompilationEvent(stage="writing", message=f"Writing lesson (draft {attempt + 1})")
            feedback = verifications[-1].feedback() if verifications else None
            lesson = await write_lesson(topic, lesson_plan, lesson_resources, lesson, feedback)

            yield CompilationEvent(stage="verifying", message=f"Verifying lesson (draft {attempt + 1})")
            verification = await verify_page(topic, lesson_plan, lesson)
            verifications.append(verification)
            if verification.passed:
                break

        result = CompiledLesson(
            topic=topic,
            lesson_plan=lesson_plan,
            reviews=reviews,
            lesson=lesson,
            verifications=verifications,
        )
        status = "verified" if result.verified else "returned unverified (revisions exhausted)"
        yield CompilationEvent(stage="done", message=f"Lesson {status}", result=result)


async def compile_lesson(topic: str, lesson_resources: str, **kwargs) -> CompiledLesson:
    async for event in compile_lesson_stream(topic, lesson_resources, **kwargs):
        if event.result is not None:
            return event.result
    raise RuntimeError("compilation ended without a result")
