from pydantic import BaseModel, Field
from enum import Enum


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
    format: str = Field(default="html", description="Preferred output format: html, markdown, or components")
    route: RouteEnum = Field(description="Where to route: 'research' for new topic, 'tutor' for lesson question")


class UserProfile(BaseModel):
    """User preferences and history. Persistent across sessions."""
    user_id: str = Field(description="Unique user identifier")
    default_level: LevelEnum = Field(default=LevelEnum.INTERMEDIATE)
    primary_stack: str = Field(default="", description="Primary tech stack")
    preferred_format: str = Field(default="html")
    preferred_tone: str = Field(default="technical", description="Tone preference: technical, casual, etc.")


class Citation(BaseModel):
    """A source citation for a lesson or answer"""
    title: str = Field(description="Article/source title")
    url: str = Field(description="Source URL")
    summary: str = Field(description="Brief summary of relevant content")


class Answer(BaseModel):
    """Grounded answer from Tutor Agent"""
    answer: str = Field(description="The tutor's answer, grounded in lesson sources")
    citations: list[Citation] = Field(description="Sources used to answer the question")
    lesson_id: str = Field(description="ID of the lesson being tutored on")


class SearchResult(BaseModel):
    """A single candidate article found by the Web Search Agent"""
    title: str = Field(description="Article title")
    url: str = Field(description="Article URL")
    snippet: str = Field(description="One-sentence snippet of what the article covers")


class SearchResults(BaseModel):
    """Output of the Web Search Agent for one query"""
    results: list[SearchResult] = Field(description="Candidate articles found for the query")


class ArticleSummary(Citation):
    """Output of the Summarizer Agent: a kept article reduced to key points.

    Extends Citation (title, url, summary) so a list[ArticleSummary] can be used
    directly wherever list[Citation] is expected (e.g. Answer.citations) with no
    conversion step.
    """
    key_points: list[str] = Field(description="3-5 key takeaways a learner should remember")
