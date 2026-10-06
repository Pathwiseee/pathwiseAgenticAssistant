import re

import gradio as gr
from agents import Agent, Runner

from pathwiseagenticassistant.agents.compilation.ui_component import CONTAINER_TYPES, UIComponent
from pathwiseagenticassistant.schemas import PageReview, PageVerification, ResearchPack
from pathwiseagenticassistant.ui.components import render

# Overview Description: Checks the page has every required section, renders, and has no unsafe script

#Input: The actual lesson made by the Writer agent (or the interactive converter agent)
#Output: Focuses on main points/learning goals that were not delivered effectively,
# and places notes where the lesson writing agent can add or rephrase to finalize the lesson.
# provides suggestions, and maps out blindspots

# Two halves:
# - check_structure: deterministic (tree shape, unsafe markup, actually renders in Gradio)
# - page_verifier_agent: LLM judgement on whether the plan's goals were delivered

Instructions = """
    Goal: Verify a written lesson delivers its lesson plan.

    Given:
    - Topic
    - Lesson Plan
    - Lesson, as a JSON tree of UI components

    Instructions:
    Walk the lesson plan section by section: main topic goals, each subtopic, and the assignment.
    For each, find where the lesson covers it.

    Be pragmatic: the bar is "a learner could reach the core goals from this page", not "every detail
    in the plan is shown". Optional extensions, "potential examples", extra depth, and polish are never blocking.

    Output:
    - blocking_gaps: only core goals or subtopics that are missing entirely or taught incorrectly.
      Leave empty if there are none.
    - suggestions: non-blocking edits for the lesson writer: where in the lesson to add or rephrase, and what.
    """


page_verifier_agent = Agent(
    name="page_verifier_agent",
    model="gpt-5-mini",
    instructions=Instructions,
    output_type=PageReview,
)


UNSAFE_PATTERN = re.compile(r"<\s*(script|iframe|object|embed)\b|javascript:|<[^>]*\bon\w+\s*=", re.IGNORECASE)


def check_structure(lesson: UIComponent) -> list[str]:
    issues = []

    def walk(node: UIComponent, path: str):
        if node.type in CONTAINER_TYPES:
            if not node.children:
                issues.append(f"{path}: empty {node.type}")
        elif node.children:
            issues.append(f"{path}: {node.type} cannot have children")

        if node.type in {"markdown", "text", "code", "quiz"} and not (node.content or "").strip():
            issues.append(f"{path}: {node.type} has no content")
        if node.type in {"textbox", "accordion"} and not (node.label or "").strip():
            issues.append(f"{path}: {node.type} has no label")
        if node.type == "quiz":
            if len(node.options) < 2:
                issues.append(f"{path}: quiz needs at least 2 options")
            if node.answer not in node.options:
                issues.append(f"{path}: quiz answer {node.answer!r} is not one of its options")

        # code is displayed, never executed, so example markup inside it is fine
        prose = [node.label, node.explanation, *node.options]
        if node.type != "code":
            prose.append(node.content)
        for field in prose:
            if field and UNSAFE_PATTERN.search(field):
                issues.append(f"{path}: unsafe markup in {node.type}")

        for i, child in enumerate(node.children):
            walk(child, f"{path}.children[{i}]")

    walk(lesson, "root")

    try:
        with gr.Blocks():
            render(lesson)
    except Exception as e:
        issues.append(f"lesson failed to render: {e!r}")

    return issues


async def verify_page(research_pack: ResearchPack, lesson_plan: str, lesson: UIComponent) -> PageVerification:
    structural_issues = check_structure(lesson)
    if structural_issues:
        # Don't spend an LLM call reviewing content of a page that needs rewriting anyway
        return PageVerification(structural_issues=structural_issues, review=None)

    prompt = f"Topic: {research_pack.topic}\n\nLesson Plan:\n{lesson_plan}\n\nLesson:\n{lesson.model_dump_json()}"
    result = await Runner.run(page_verifier_agent, prompt)
    return PageVerification(structural_issues=[], review=result.final_output)
