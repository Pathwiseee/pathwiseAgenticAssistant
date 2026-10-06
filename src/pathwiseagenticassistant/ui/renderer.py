import gradio as gr
from dotenv import load_dotenv

from pathwiseagenticassistant.agents.compilation.ui_component import UIComponent
from pathwiseagenticassistant.agents.compilation.compilation_orchestrator import compile_lesson_stream
from pathwiseagenticassistant.agents.research.research_manager import ResearchManager
from pathwiseagenticassistant.schemas import CompiledLesson, LearningRequest, LevelEnum
from pathwiseagenticassistant.tools.summarizer import summarizer_agent
from pathwiseagenticassistant.tools.web_search_agent import web_search_agent
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
        level = gr.Dropdown([l.value for l in LevelEnum], value=LevelEnum.INTERMEDIATE.value, label="Level")
        tech_stack = gr.Textbox(label="Tech Stack")
        goal = gr.Textbox(label="Goal")
        generate = gr.Button("Compile Lesson")
        status = gr.Markdown()

        with gr.Accordion("Lesson Plan", open=False):
            plan_md = gr.Markdown()
        with gr.Accordion("Plan Reviews", open=False):
            reviews_md = gr.Markdown()
        with gr.Accordion("Page Verification", open=False):
            verification_md = gr.Markdown()

        async def generate_lesson(topic, level, tech_stack, goal):
            # Research takes a few minutes and has no event stream, so show a single status line for it
            log = ["- **researching**: Gathering and summarizing sources"]
            yield {status: "\n".join(log)}
            request = LearningRequest(topic=topic, level=LevelEnum(level), tech_stack=tech_stack, goal=goal)
            research_pack = await ResearchManager(web_search_agent, summarizer_agent).run(request)
            log.append(f"- **researching**: Found {len(research_pack.summaries)} sources")

            async for event in compile_lesson_stream(research_pack):
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
            inputs=[topic, level, tech_stack, goal],
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
