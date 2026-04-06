"""Pydantic models for ElevenLabs webhook payloads and API responses."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class TranscriptTurn(BaseModel):
    role: str
    message: str = ""
    time_in_call_secs: float | None = None


class DataCollection(BaseModel):
    """Dynamically extracted fields from the conversation."""

    current_status: str | None = None
    core_skills: str | None = None
    target_industry: str | None = None
    availability: str | None = None
    salary_expectation: str | None = None
    german_level: str | None = None
    work_location: str | None = None
    work_methodology: str | None = None

    class Config:
        extra = "allow"  # Accept additional fields from ElevenLabs


class EvaluationResult(BaseModel):
    result: str | None = None
    rationale: str | None = None

    class Config:
        extra = "allow"


class Analysis(BaseModel):
    data_collection: dict[str, Any] = Field(default_factory=dict)
    evaluation_criteria_results: dict[str, Any] = Field(default_factory=dict)
    transcript_summary: str | None = None
    call_successful: str | None = None

    class Config:
        extra = "allow"


class PostCallPayload(BaseModel):
    """ElevenLabs post-call webhook payload."""

    conversation_id: str
    agent_id: str
    status: str | None = None
    analysis: Analysis = Field(default_factory=Analysis)
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class PostCallAudioPayload(BaseModel):
    """ElevenLabs post-call audio webhook payload."""

    conversation_id: str
    agent_id: str | None = None
    audio: str | None = None  # base64-encoded MP3

    class Config:
        extra = "allow"


class ConversationSummary(BaseModel):
    """Summary for the conversations list API."""

    conversation_id: str
    agent_id: str
    timestamp: str
    turns: int
    data_collected: list[str]
    screening_complete: bool | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "0.1.0"
