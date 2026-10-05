from pydantic import BaseModel, Field
from agents import Agent, Runner, trace

# Overview Description: Sets learning goals, preconditions and postconditions for one step

#Input:
# User information (if applicable): Tech Stack, specific experience (which technologies proficient with)
# Sources Report: Main Sources, Topics, and Main Points from that Source.

#Output:
# Flagged sections for review — they "don't match the topic" or lesson goals "aren't sufficient" for learning the main topic

Instructions = """
    Goal: Critique lesson plan for learning a given technology or technological concept.

    Given:
    - Topic
    - Lesson Plan
    - Lesson Resources


    Instructions:
    View the entire lesson plan, noting which portions of the lesson plan are insufficient for learning the given technology or technological concept.
    A good strategy is to first view the main topic, the lesson subtopics, and how they flow. Do they flow well? Are there important missing key terms or concepts that are not noted in the subtopics?
    Assess the lesson goals.
    Verify the prerequisites are accurate and appropriate for the entire lesson.

    Be pragmatic: a plan does not need to be perfect or exhaustive, it needs to be teachable as one lesson.
    Do NOT ask for extra scope (more subtopics, tooling, benchmarks, testing, advanced extensions);
    those belong in suggestions or in a later lesson.

    Output:
    - blocking_issues: only problems that would make the lesson wrong or unlearnable:
        - factually incorrect content
        - a concept essential to the topic that is missing entirely
        - inaccurate or missing prerequisites
        - subtopics in an order where one depends on a later one
      Leave empty if there are none. Most reasonable plans should have none.
    - suggestions: systematic, non-blocking notes following the structure of the plan.
    """


class LessonReview(BaseModel):
    blocking_issues: list[str] = Field(description="Problems that make the lesson wrong or unlearnable; usually empty")
    suggestions: str = Field(description="Non-blocking notes following the structure of the plan")

    @property
    def approved(self) -> bool:
        return not self.blocking_issues


lesson_reviewer_agent = Agent(
    name="lesson_reviewer_agent",
    model="gpt-5-mini",
    instructions=Instructions,
    output_type=LessonReview,
)

async def review_lesson_plan(topic: str, lesson_plan: str, lesson_resources: str) -> LessonReview:
    prompt = f"Topic: {topic}\n\nLesson Plan:\n{lesson_plan}\n\nLesson Resources:\n{lesson_resources}"
    result = await Runner.run(lesson_reviewer_agent, prompt)
    return result.final_output
