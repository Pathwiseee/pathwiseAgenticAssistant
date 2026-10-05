from agents import Agent, Runner, trace

from pathwiseagenticassistant.agents.compilation.ui_component import UIComponent

# Overview Description: Writes the lesson content in the user's stack and tone

#Input: lesson plan
#Output: fully-functional gradio lesson


Instructions = """
    Goal: Write lesson as UI components in Gradio based on a lesson plan. 

    Given: 
    - Lesson Plan
    - Lesson Resources
    - Topic

    Output: 
    - Gradio Components that will be rendered into dynamic UI
    - Return a single root UIComponent (usually a "column") whose children make up the lesson.
      Only "row", "column" and "accordion" may have children. Leave unused fields null/empty.

    Component types:
    - "markdown": lesson prose (content). Headings, lists, inline code.
    - "code": a standalone code example (content, language e.g. "python"). Prefer this over code fences in markdown.
    - "accordion": collapsed section (label = header, children = body). Use for worked solutions,
      answers to exercises, and optional deep dives, so the learner tries first and reveals after.
    - "quiz": multiple-choice check (content = question, options = 2-5 choices, answer = the exact
      text of the correct option, explanation = why). End each subtopic with one quiz.
    - "textbox": scratch space for the learner to attempt an exercise (label = the prompt).
    - "text": short read-only callout (content).
    - "row" / "column": layout.

    Exercise pattern: markdown prompt -> textbox to attempt -> accordion "Solution" containing code + markdown.
    """


# Runner.run(agent)
#  │
#  ▼
# OpenAI model
#  │
#  │ structured output
#  ▼
# UIComponent
#  │
#  ▼
# gr.render()
#  │
#  ▼
# actual Gradio components


lesson_writing_agent = Agent(
    name="lesson_writing_agent",
    model="gpt-5-mini",
    instructions=Instructions,
    output_type=UIComponent,
)

async def write_lesson(
    topic: str,
    lesson_plan: str,
    lesson_resources: str,
    previous_draft: UIComponent | None = None,
    feedback: str | None = None,
) -> UIComponent:
    prompt = f"Topic: {topic}\n\nLesson Plan:\n{lesson_plan}\n\nLesson Resources:\n{lesson_resources}"
    if previous_draft is not None:
        prompt += f"\n\nPrevious Draft (revise this, keep what works):\n{previous_draft.model_dump_json()}"
    if feedback:
        prompt += f"\n\nVerifier Feedback (address every point):\n{feedback}"
    result = await Runner.run(lesson_writing_agent, prompt)
    return result.final_output