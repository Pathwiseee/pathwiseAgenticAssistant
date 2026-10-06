from agents import trace

async def compile_lesson_stream(
    user_request: str,
) :
    with trace("lesson_compilation"):
        yield CompilationEvent(stage="planning", message="Intake Agent")
        lesson_plan = await get_lesson_plan(research_pack)

        reviews: list[LessonReview] = []
        for attempt in range(max_plan_revisions + 1):
            yield CompilationEvent(stage="reviewing", message=f"Reviewing lesson plan (round {attempt + 1})")
            review = await review_lesson_plan(research_pack, lesson_plan)
            reviews.append(review)
            if review.approved or attempt == max_plan_revisions:
                break
            # Only blocking issues drive a revision; suggestions would keep expanding the plan's scope
            yield CompilationEvent(stage="planning", message="Revising lesson plan to fix blocking issues")
            blocking = "\n".join(f"- {issue}" for issue in review.blocking_issues)
            lesson_plan = await get_lesson_plan(research_pack, lesson_plan, blocking)

        lesson: UIComponent | None = None
        verifications: list[PageVerification] = []
        for attempt in range(max_write_revisions + 1):
            yield CompilationEvent(stage="writing", message=f"Writing lesson (draft {attempt + 1})")
            feedback = verifications[-1].feedback() if verifications else None
            lesson = await write_lesson(research_pack, lesson_plan, lesson, feedback)

            yield CompilationEvent(stage="verifying", message=f"Verifying lesson (draft {attempt + 1})")
            verification = await verify_page(research_pack, lesson_plan, lesson)
            verifications.append(verification)
            if verification.passed:
                break

        result = CompiledLesson(
            research_pack=research_pack,
            lesson_plan=lesson_plan,
            reviews=reviews,
            lesson=lesson,
            verifications=verifications,
        )
        status = "verified" if result.verified else "returned unverified (revisions exhausted)"
        yield CompilationEvent(stage="done", message=f"Lesson {status}", result=result)


async def compile_lesson(research_pack: ResearchPack, **kwargs) -> CompiledLesson:
    async for event in compile_lesson_stream(research_pack, **kwargs):
        if event.result is not None:
            return event.result
    raise RuntimeError("compilation ended without a result")