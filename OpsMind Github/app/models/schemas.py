"""Pydantic data models for OpsMind."""

from datetime import datetime
from typing import Literal, Optional, List
from pydantic import BaseModel, Field


class IncidentInput(BaseModel):
    """Payload for submitting an incident for investigation."""

    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Concise description of the incident",
    )
    service: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Affected service or component identifier",
    )
    severity: Literal["SEV-1", "SEV-2", "SEV-3"] = Field(
        "SEV-2", description="Incident severity classification"
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Detailed observation of symptoms and impact",
    )
    log_excerpt: Optional[str] = Field(
        None,
        max_length=3000,
        description="Relevant log excerpt or error stack trace",
    )


class SampleScenario(BaseModel):
    """Fictional scenario fixture for demonstration."""

    id: str
    label: str
    category: Literal["related", "unseen"]
    has_historical_match: bool
    incident: IncidentInput


class MemoryEvidenceItem(BaseModel):
    """A memory record retrieved from Hindsight persistent memory."""

    incident_id: str
    title: str
    service: str
    excerpt: str
    relevance_reason: str
    historical_verification_status: Literal["VERIFIED", "UNCONFIRMED", "FAILED"]
    recorded_at: str
    source_type: Literal["hindsight_cloud", "hindsight_local", "simulated"]


class DiagnosticCheck(BaseModel):
    """A recommended safe, read-only diagnostic check."""

    step: int
    action: str
    purpose: str
    command_example: Optional[str] = None


class InvestigationResult(BaseModel):
    """The structured 6-section investigation response."""

    incident_summary: str
    relevant_past_incidents: List[str]
    what_history_suggests: str
    recommended_diagnostic_checks: List[DiagnosticCheck]
    differences_and_uncertainty: str
    suggested_next_step: str
    memory_evidence: List[MemoryEvidenceItem]
    provenance_summary: dict


class OutcomeInput(BaseModel):
    """Engineer-verified outcome submission for persistent retention."""

    incident_id: Optional[str] = None
    service: str = Field(..., min_length=2, max_length=100)
    confirmed_root_cause: str = Field(..., min_length=10, max_length=1500)
    resolution_fix: str = Field(..., min_length=10, max_length=1500)
    verification_status: Literal["VERIFIED", "UNCONFIRMED"] = "VERIFIED"
    notes: Optional[str] = Field(None, max_length=1000)


class TraceEvent(BaseModel):
    """An event logged in the real execution trace."""

    timestamp: str
    stage: str
    detail: str
    status: Literal["info", "success", "warning", "error"]
