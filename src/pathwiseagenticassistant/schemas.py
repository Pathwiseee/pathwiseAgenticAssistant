from typing import Literal

from pydantic import BaseModel, Field
from enum import Enum

from pathwiseagenticassistant.agents.compilation.ui_component import UIComponent


# INTAKE 
class LevelEnum(str, Enum):
    """User's current knowledge level"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class RouteEnum(str, Enum):
    """Routing decision from Intake Agent"""
    RESEARCH = "research"
    TUTOR = "tutor"


class LearningRequest(BaseModel):
    """Structured learning goal with context. Output of Intake Agent."""
    topic: str = Field(description="The technology/concept to learn (e.g., 'Kafka', 'React Hooks')")
    level: LevelEnum = Field(description="User's current knowledge level")
    tech_stack: str = Field(description="User's primary tech stack (e.g., 'Java/Spring', 'Python/Django')")
    goal: str = Field(description="Learning purpose: job, project, exam, or general knowledge")


# Research

class ArticleSummary(BaseModel):
    title: str
    url: str
    key_points: list[str]
    subtopics_covered: list[str]

class ResearchPack(BaseModel):
    topic: str
    summaries: list[ArticleSummary]
    gaps: list[str]


# Tutoring
class UserProfile(BaseModel):
    """User preferences and history. Persistent across sessions."""
    user_id: str = Field(description="Unique user identifier")
    default_level: LevelEnum = Field(default=LevelEnum.INTERMEDIATE)
    primary_stack: str = Field(default="", description="Primary tech stack")
    preferred_format: str = Field(default="html")
    preferred_tone: str = Field(default="technical", description="Tone preference: technical, casual, etc.")

class Answer(BaseModel):
    """Grounded answer from Tutor Agent"""
    answer: str = Field(description="The tutor's answer, grounded in lesson sources")
    citations: list[Citation] = Field(description="Sources used to answer the question")
    lesson_id: str = Field(description="ID of the lesson being tutored on")

# Search Agent

class SearchResult(BaseModel):
    """A single candidate article found by the Web Search Agent"""
    title: str = Field(description="Article title")
    url: str = Field(description="Article URL")
    snippet: str = Field(description="One-sentence snippet of what the article covers")


class SearchResults(BaseModel):
    """Output of the Web Search Agent for one query"""
    results: list[SearchResult] = Field(description="Candidate articles found for the query")



# Compilation


class LessonReview(BaseModel):
    blocking_issues: list[str] = Field(description="Problems that make the lesson wrong or unlearnable; usually empty")
    suggestions: str = Field(description="Non-blocking notes following the structure of the plan")

    @property
    def approved(self) -> bool:
        return not self.blocking_issues

class PageReview(BaseModel):
    blocking_gaps: list[str] = Field(description="Core goals missing entirely or taught incorrectly; usually empty")
    suggestions: str = Field(description="Non-blocking add/rephrase edits for the lesson writer")

    @property
    def passed(self) -> bool:
        return not self.blocking_gaps


class PageVerification(BaseModel):
    structural_issues: list[str]
    review: PageReview | None  # None when structural checks failed and the LLM review was skipped

    @property
    def passed(self) -> bool:
        return not self.structural_issues and self.review is not None and self.review.passed

    # Only blocking problems go back to the writer; suggestions would grow the lesson every revision
    def feedback(self) -> str:
        parts = []
        if self.structural_issues:
            parts.append("Structural issues:\n" + "\n".join(f"- {i}" for i in self.structural_issues))
        if self.review is not None and self.review.blocking_gaps:
            parts.append("Blocking gaps:\n" + "\n".join(f"- {g}" for g in self.review.blocking_gaps))
        return "\n\n".join(parts)

class CompiledLesson(BaseModel):
    research_pack: ResearchPack
    reviews: list[LessonReview] = Field(default_factory=list)
    lesson: UIComponent
    verifications: list[PageVerification] = Field(default_factory=list)

    @property
    def verified(self) -> bool:
        return bool(self.verifications) and self.verifications[-1].passed


class CompilationEvent(BaseModel):
    stage: Literal["planning", "reviewing", "writing", "verifying", "done"]
    message: str
    result: CompiledLesson | None = None  # only set on the "done" event



