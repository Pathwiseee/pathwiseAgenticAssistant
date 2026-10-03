from pydantic import BaseModel, Field
from agents import Agent

# Overview Description: Writes the lesson content in the user's stack and tone

#Input: The lesson plan from lesson planning agent
#Output: Writes out the content of the lesson. Fills out the outline made by the planner. Double checks output with page verifier