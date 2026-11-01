
import re

from ingestion.schemas import (
    TelemetryEvent,
    ResourceMetadata
)


def classify_event(message: str, severity: str) -> str:

    text = message.lower()

    if "connection pool exhausted" in text:
        return "RESOURCE_EXHAUSTION"

    if "timed out" in text or "timeout" in text:
        return "TIMEOUT"

    if "dependency failed" in text or "dependency returned" in text:
        return "DEPENDENCY_FAILURE"

    if "gateway" in text and severity == "ERROR":
        return "UPSTREAM_FAILURE"

    if "checkout completed" in text:
        return "REQUEST_SUCCESS"

    if "chaos injection" in text:
        return "FAULT_INJECTION"

    return "GENERAL"


def extract_resource_metadata(message: str) -> ResourceMetadata:

    match = re.search(
        r"(\d+)/(\d+)\s+(?:sessions|connections)",
        message,
        re.IGNORECASE
    )

    if not match:
        return ResourceMetadata()

    return ResourceMetadata(
        resource_type="DATABASE_CONNECTION_POOL",
        used=int(match.group(1)),
        capacity=int(match.group(2))
    )


def normalize_event(event: TelemetryEvent) -> TelemetryEvent:

    event.event_type = classify_event(
        event.message,
        event.severity
    )

    event.resource = extract_resource_metadata(
        event.message
    )

    return event


def normalize_events(
    events: list[TelemetryEvent]
) -> list[TelemetryEvent]:

    return [
        normalize_event(event)
        for event in events
    ]
