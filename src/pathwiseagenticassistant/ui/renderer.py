import gradio as gr
from dotenv import load_dotenv

from pathwiseagenticassistant.agents.compilation.ui_component import UIComponent
from pathwiseagenticassistant.agents.compilation.compilation_orchestrator import CompiledLesson, compile_lesson_stream
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


def build_lesson_ui() -> gr.Blocks:
    with gr.Blocks() as demo:
        lesson_state = gr.State(None)

        topic = gr.Textbox(label="Topic")
        lesson_resources = gr.Textbox(label="Lesson Resources", lines=5)
        generate = gr.Button("Compile Lesson")
        status = gr.Markdown()

        with gr.Accordion("Lesson Plan", open=False):
            plan_md = gr.Markdown()
        with gr.Accordion("Plan Reviews", open=False):
            reviews_md = gr.Markdown()
        with gr.Accordion("Page Verification", open=False):
            verification_md = gr.Markdown()

        async def generate_lesson(topic, lesson_resources):
            log = []
            async for event in compile_lesson_stream(topic, lesson_resources):
                log.append(f"- **{event.stage}**: {event.message}")
                if event.result is None:
                    yield {status: "\n".join(log)}
                    continue
                compiled = event.result
                yield {
                    status: "\n".join(log),
                    plan_md: compiled.lesson_plan,
                    reviews_md: format_reviews(compiled),
                    verification_md: format_verifications(compiled),
                    lesson_state: compiled.lesson.model_dump(),
                }

        generate.click(
            generate_lesson,
            inputs=[topic, lesson_resources],
            outputs=[status, plan_md, reviews_md, verification_md, lesson_state],
        )

        # Re-runs every time lesson_state changes, rebuilding the lesson UI
        @gr.render(inputs=lesson_state)
        def render_lesson(lesson):
            if lesson is None:
                return
            render(UIComponent.model_validate(lesson))

    return demo


if __name__ == "__main__":
    load_dotenv()
    build_lesson_ui().launch()
