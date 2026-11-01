
from datetime import datetime
from typing import Any, Optional, Literal

from pydantic import BaseModel, Field


Severity = Literal[
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL"
]


class ResourceMetadata(BaseModel):
    resource_type: Optional[str] = None
    used: Optional[int] = None
    capacity: Optional[int] = None


class TelemetryEvent(BaseModel):
    event_id: str

    timestamp: datetime

    service: str

    severity: Severity

    request_id: str

    message: str

    sequence: int = 0

    event_type: str = "GENERAL"

    resource: ResourceMetadata = Field(
        default_factory=ResourceMetadata
    )

    source: str = "application_log"


class IncidentNode(BaseModel):
    service: str

    event_ids: list[str] = Field(
        default_factory=list
    )

    failure_type: Optional[str] = None

    severity: Optional[str] = None

    evidence: list[str] = Field(
        default_factory=list
    )

    children: list["IncidentNode"] = Field(
        default_factory=list
    )


class IncidentReport(BaseModel):
    incident_id: str

    started_at: datetime

    ended_at: datetime

    alerting_service: str

    severity: str

    request_ids: list[str]

    events: list[TelemetryEvent]

    root_cause_candidate: Optional[str] = None

    propagation_tree: Optional[IncidentNode] = None

    correlation_method: str = "request_id"

    confidence: Optional[float] = None

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )
