import gradio as gr
from dotenv import load_dotenv

from pathwiseagenticassistant.agents.pathwiseWorkflow import research_and_compile_stream
from pathwiseagenticassistant.schemas import CompiledLesson, LearningRequest, LevelEnum
from pathwiseagenticassistant.ui.components import render


def bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def format_reviews(compiled: CompiledLesson) -> str:
    sections = []
    for i, r in enumerate(compiled.reviews):
        section = f"**Round {i + 1}: {'approved' if r.approved else 'changes requested'}**"
        if r.blocking_issues:
            section += f"\n\nBlocking issues:\n{bullets(r.blocking_issues)}"
        section += f"\n\nSuggestions:\n\n{r.suggestions}"
        sections.append(section)
    return "\n\n---\n\n".join(sections)


def format_verifications(compiled: CompiledLesson) -> str:
    sections = []
    for i, v in enumerate(compiled.verifications):
        section = f"**Draft {i + 1}: {'passed' if v.passed else 'failed'}**"
        if v.feedback():
            section += f"\n\n{v.feedback()}"
        if v.review is not None:
            section += f"\n\nSuggestions:\n\n{v.review.suggestions}"
        sections.append(section)
    return "\n\n---\n\n".join(sections)


def lesson_panel() -> gr.State:
    """Plan, reviews, verification and the interactive lesson.

    Set the returned state to a CompiledLesson dump (or None to clear) to show it.
    Must be called inside a gr.Blocks() context.
    """
    lesson_state = gr.State(None)

    # Re-runs every time lesson_state changes, rebuilding the lesson UI
    @gr.render(inputs=lesson_state)
    def render_lesson(lesson):
        if lesson is None:
            return
        compiled = CompiledLesson.model_validate(lesson)
        with gr.Accordion("Lesson Plan", open=False):
            gr.Markdown(compiled.lesson_plan)
        with gr.Accordion("Plan Reviews", open=False):
            gr.Markdown(format_reviews(compiled))
        with gr.Accordion("Page Verification", open=False):
            gr.Markdown(format_verifications(compiled))
        render(compiled.lesson)

    return lesson_state


def build_lesson_ui() -> gr.Blocks:
    with gr.Blocks() as demo:
        topic = gr.Textbox(label="Topic")
        level = gr.Dropdown([l.value for l in LevelEnum], value=LevelEnum.INTERMEDIATE.value, label="Level")
        tech_stack = gr.Textbox(label="Tech Stack")
        goal = gr.Textbox(label="Goal")
        generate = gr.Button("Compile Lesson")
        status = gr.Markdown()
        lesson_state = lesson_panel()

        async def generate_lesson(topic, level, tech_stack, goal):
            log = []
            request = LearningRequest(topic=topic, level=LevelEnum(level), tech_stack=tech_stack, goal=goal)
            async for event in research_and_compile_stream(request):
                log.append(f"- **{event.stage}**: {event.message}")
                if event.result is None:
                    yield {status: "\n".join(log)}
                    continue
                yield {status: "\n".join(log), lesson_state: event.result.model_dump()}

        generate.click(generate_lesson, inputs=[topic, level, tech_stack, goal], outputs=[status, lesson_state])

    return demo


if __name__ == "__main__":
    load_dotenv()
    build_lesson_ui().launch()
