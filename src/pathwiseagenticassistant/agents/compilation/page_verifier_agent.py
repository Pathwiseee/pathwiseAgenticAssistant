from pydantic import BaseModel, Field
from agents import Agent

# Overview Description: Checks the page has every required section, renders, and has no unsafe script

#Input: The actual lesson made by the Writer agent (or the interactive converter agent)
#Output: Focuses on main points/learning goals that were not delivered effectively, 
# and places notes where the lesson writing agent can add or rephrase to finalize the lesson. 
# provides suggestions, and maps out blindspots