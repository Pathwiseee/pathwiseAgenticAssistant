from agents import Agent, FileSearchTool
from pathwiseagenticassistant.guardrails import make_input_guardrail
from pathwiseagenticassistant.schemas import Answer

INSTRUCTIONS = """You are Pathwise's tutor agent. Your role is to answer student questions about a specific lesson using only the lesson's vetted sources.

**Your workflow:**
1. Use the FileSearchTool to search for relevant content from the lesson materials.
2. Ground your answer exclusively in the search results - do not use general knowledge.
3. Explain the concept clearly and relate it to the student's learning context.
4. Cite specific sources for every claim:
   - When you reference information, note the source title and URL
   - If a claim comes from multiple sources, cite all of them
5. Format your final answer with clear citations.

**Important constraints:**
- ONLY answer based on lesson materials found via FileSearchTool
- If the search returns no relevant results, acknowledge the limitation and suggest alternative resources
- Be concise but thorough - adapt complexity to what a learner at their level would understand
- Correct any misconceptions gently with source-backed explanation"""

tutor_input_guardrail = make_input_guardrail("questions about a software technology or programming concept being studied")


def create_tutor_agent(vector_store_id: str) -> Agent:
    """Build a Tutor Agent scoped to one lesson's vector store.

    FileSearchTool requires a concrete vector_store_ids list at construction time,
    and each lesson has its own vector store, so the agent is created per lesson
    rather than as a single shared module-level instance.
    """
    return Agent(
        name="Tutor Agent",
        instructions=INSTRUCTIONS,
        tools=[FileSearchTool(vector_store_ids=[vector_store_id])],
        model="gpt-5-mini",
        output_type=Answer,
        input_guardrails=[tutor_input_guardrail],
    )