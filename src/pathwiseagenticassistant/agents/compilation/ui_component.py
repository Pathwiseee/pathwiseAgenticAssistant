from pydantic import BaseModel, Field
from typing import Literal


# Field usage per type:
# - markdown, text: content
# - textbox: label (scratch space for the learner)
# - code: content, language
# - accordion: label (header), children (collapsed by default; good for answers/solutions)
# - quiz: content (question), options, answer (must be one of options), explanation
# - row, column: children
class UIComponent(BaseModel):
    type: Literal["markdown", "text", "textbox", "code", "accordion", "quiz", "row", "column"]
    content: str | None = None
    label: str | None = None
    language: str | None = None
    options: list[str] = Field(default_factory=list)
    answer: str | None = None
    explanation: str | None = None
    children: list["UIComponent"] = Field(default_factory=list)


CONTAINER_TYPES = {"row", "column", "accordion"}

UIComponent.model_rebuild()
