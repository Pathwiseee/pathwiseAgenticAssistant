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

    Output: 
    - systematic notes following the structure of the plan, noting which areas need to be changed in what way. 
    """

lesson_reviewer_agent = Agent(
    name="lesson_reviewer_agent",
    model="gpt-5-mini",
    instructions=Instructions,
)

async def get_lesson_plan(topic: str, lesson_resources: str):
	result = await Runner.run(lesson_reviewer_agent, lesson_resources, topic)
	return result.final_output