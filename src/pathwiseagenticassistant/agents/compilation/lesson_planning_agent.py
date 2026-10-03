from pydantic import BaseModel, Field
from agents import Agent

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

"""
Functions
- load_user_info() --> str of info
- load_summary() --> based on the chat located within, finds the resources (works cited + main points)
- lessonPlanningAgent --> agent that plans out the lesson in a structured manner

"""