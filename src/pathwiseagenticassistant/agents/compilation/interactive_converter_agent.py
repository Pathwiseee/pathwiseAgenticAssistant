from pydantic import BaseModel, Field
from agents import Agent

# Overview Description: Turns the lesson into an interactive page: code blocks, expandable sections, a short quiz

#Input: Lesson from page verifier or lesson writing agent
#Output: For each sublesson, creates interactive examples. this could include
# - runnable code blocks
# - outside resources

# Helper functions
# - Different kinds of components:
#   - code blocks
#   - Web search resource finder, either interactive pages or other learning resources
#   - 