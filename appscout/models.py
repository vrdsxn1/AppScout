"""Pydantic models for AppScout's structured research records."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class SourceAttempt(BaseModel):
    """A fetched or blocked candidate URL, used to make a free pass resumable."""

    url: HttpUrl
    status: Literal["retrieved", "inaccessible", "blocked_robots", "rate_limited", "not_found", "error"]
    note: str | None = None


class EvidenceRecord(BaseModel):
    """One source-backed claim associated with an app assessment."""

    claim: str = Field(min_length=1, description="The specific claim supported by the source.")
    field: Literal[
        "description", "auth_methods", "access_model", "api_type", "api_breadth",
        "mcp_status", "buildability", "blockers", "category",
    ] | None = Field(default=None, description="The one record field this evidence claim relates to.")
    url: HttpUrl = Field(description="An HTTP or HTTPS URL that supports the claim.")
    source_type: str = Field(min_length=1, description="A short label for the source, such as docs or pricing page.")
    source_title: str | None = None
    excerpt: str | None = Field(default=None, description="A short exact excerpt retrieved from the source page.")
    retrieval_status: Literal["not_attempted", "retrieved", "inaccessible", "rate_limited"] = "not_attempted"
    claim_supported: Literal["supported", "partially_supported", "unsupported", "unverified"] = "unverified"
    retrieval_note: str | None = None
    evidence_quality: Literal["usable", "page_shell", "navigation", "insufficient"] = "insufficient"
    evidence_quality_note: str | None = None
    human_verdict: Literal[
        "supported", "partially_supported", "unsupported", "source_unavailable", "unclear"
    ] | None = None
    review_method: str | None = None
    reviewer_notes: str | None = None

    @field_validator("claim", "source_type")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must contain non-whitespace text")
        return value


class AppResearchRecord(BaseModel):
    """Structured integration-readiness assessment for one software app."""

    app_name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    description: str = Field(min_length=1, description="A one-line description of the app.")
    auth_methods: list[str]
    access_model: str = Field(
        min_length=1,
        description="How a developer obtains access, or 'unknown' when not established.",
    )
    api_type: str = Field(min_length=1, description="For example REST, GraphQL, both, or unknown.")
    api_breadth: str = Field(min_length=1, description="Observed API coverage or known limitations.")
    mcp_status: str = Field(min_length=1, description="Observed MCP integration status, or unknown.")
    buildability: Literal["build_now", "build_with_restrictions", "needs_outreach", "unclear"]
    blockers: list[str]
    evidence: list[EvidenceRecord]
    confidence: Literal["high", "medium", "low"]
    last_checked: date
    research_status: Literal["researched", "partial", "not_researched", "blocked"] | None = None
    research_note: str | None = None
    source_attempts: list[SourceAttempt] = Field(default_factory=list)
    source_queue: list[HttpUrl] = Field(default_factory=list)

    @field_validator(
        "app_name",
        "category",
        "description",
        "access_model",
        "api_type",
        "api_breadth",
        "mcp_status",
    )
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must contain non-whitespace text")
        return value

    @field_validator("description")
    @classmethod
    def description_must_be_one_line(cls, value: str) -> str:
        if "\n" in value or "\r" in value:
            raise ValueError("description must be one line")
        return value

    @field_validator("auth_methods", "blockers")
    @classmethod
    def list_items_must_not_be_blank(cls, values: list[str]) -> list[str]:
        if any(not item.strip() for item in values):
            raise ValueError("list items must contain non-whitespace text")
        return values
