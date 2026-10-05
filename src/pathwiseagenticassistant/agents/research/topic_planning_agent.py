from typing import Literal
from pydantic import BaseModel, Field
from agents import Agent

HOW_MANY_SEARCHES = 5


# ---------- Output data ----------

class SearchItem(BaseModel):
    angle: Literal["what_it_is", "problem_it_solves", "pros_and_cons", "real_world_example", "how_to"]
    query: str = Field(description="Short web search query, under 12 words")
    reason: str = Field(description="Why this search matters for the learner")


class TopicPlan(BaseModel):
    subtopics: list[str] = Field(description="4-8 subtopics the learner must cover, in learning order")
    searches: list[SearchItem]


# ---------- Instructions ----------

INSTRUCTIONS = f"""
You are a research planner for a learning app for software engineers.

Given a learner's request (topic, level, tech stack, goal):

1. List 4-8 subtopics the learner must cover, in the order they should learn them.
   Skip basics the learner already knows for their level.

2. Write exactly {HOW_MANY_SEARCHES} web search queries, one for each angle:
   - what_it_is: what the technology is and how it works
   - problem_it_solves: what problem it solves and why it was created
   - pros_and_cons: its advantages, disadvantages and alternatives
   - real_world_example: how real companies or projects use it
   - how_to: how to use it with the learner's tech stack (name the stack in the query)

Rules:
- Every query must include the topic name.
- Queries are short, like a person types into a search engine (under 12 words).
- Do not explain the topic yourself. Only plan the research.
"""


# ---------- Agent ----------

topic_planning_agent = Agent(
    name="Topic Planning Agent",
    instructions=INSTRUCTIONS,
    output_type=TopicPlan,
    model="gpt-4o-mini",
)