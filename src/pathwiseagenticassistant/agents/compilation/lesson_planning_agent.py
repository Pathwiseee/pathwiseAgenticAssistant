from agents import Agent, Runner, trace

# Overview Description: Sets learning goals, preconditions and postconditions for one step

#Input: 
# User information (if applicable): Tech Stack, specific experience (which technologies proficient with)
# Sources Report: Main Sources, Topics, and Main Points from that Source.

#Output:
# Lesson Prerequisites
# Learning Goals
# Topology of Lesson
# Main theme of Lesson
# Sub-goals for sub-lessons, and how it connects to overarching theme of main lesson
# Which sources are related to which lessons

Instructions = """
    Goal: Create a lesson plan for the given topic.

    Given: 
    - topic, the topic the user is trying to learn
    - lesson_resources, which includes for each resource, a topic, a link, a rating for how high-quality the source is, and a summary of the resource,
    - lesson_plan, if a lesson plan is given, modify the lesson plan.

    Output: 
    - an (Lesson_name)_outline.md with an intentional topology. Main Topic at the highest level, and subtopics below that. 
    Here is the general flow of the outline: Main Topic --> Subtopics --> Lesson Summary/Assignment
    - for the main topic, list:
        - overall lesson goals
        - theme for topic
        - summary of lesson (written after entire draft)
        - citations: resources used
    - For each subtopic (should relate to main topic)
        - subtopic name
        - subtopic goals
        - potential examples 
        - summary of subtopic
        - citations: resources used 
    - Assignment: can be a variety of things, including:
        - further reading of external sources
        - a grounded technical mini-project based on the lesson material
    """

lesson_planning_agent = Agent(
    name="lesson_planning_agent",
    model="gpt-5-mini",
    instructions=Instructions,
)

async def get_lesson_plan(topic: str, lesson_resources: str, lesson_plan: str):
	result = await Runner.run(lesson_planning_agent, lesson_resources, topic, lesson_plan)
	return result.final_output