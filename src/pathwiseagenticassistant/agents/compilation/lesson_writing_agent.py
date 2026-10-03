from agents import Agent, Runner, trace

# Overview Description: Writes the lesson content in the user's stack and tone

#Input: lesson plan
#Output: fully-functional gradio lesson


Instructions = """
    Goal: Write

    Given: 
    - Topic
    - Lesson Resources, which includes for each resource, a topic, a link, a rating for how high-quality the source is, and a summary of the resource,

    Output: 
    - an (Lesson_name)_outline.md with an intentional topology. Main Topic at the highest level, and subtopics below that. 
    Here is the general flow of the outline: Main Topic --> Subtopics --> Lesson Summary/Assignment
    - for the main topic, list:
        - overall lesson goals
        - theme for topic
        - summary of lesson (written after entire draft)
        - citatoins: resources used
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

async def get_lesson_plan(topic: str, lesson_resources: str):
	result = await Runner.run(lesson_planning_agent, lesson_resources, topic)
	return result.final_output