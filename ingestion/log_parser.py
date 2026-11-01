
import hashlib
import re

from datetime import datetime
from typing import Optional

from ingestion.schemas import TelemetryEvent


LOG_PATTERN = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\]\s+"
    r"\[(?P<service>[^\]]+)\]\s+"
    r"\[(?P<severity>[^\]]+)\]\s+"
    r"(?:\[request_id=(?P<request_id>[^\]]+)\]\s+)?"
    r"(?P<message>.*)$"
)


def parse_log_line(
    line: str,
    line_number: int
) -> Optional[TelemetryEvent]:

    match = LOG_PATTERN.match(line.strip())

    if not match:
        return None

    data = match.groupdict()

    try:
        timestamp = datetime.strptime(
            data["timestamp"],
            "%Y-%m-%d %H:%M:%S"
        )

        severity = data["severity"].upper()

        if severity not in {
            "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
        }:
            return None

        request_id = data["request_id"] or "untracked"

        event_id = hashlib.sha256(
            f"{line_number}:{line.strip()}".encode()
        ).hexdigest()[:16]

        return TelemetryEvent(
            event_id=event_id,
            sequence=line_number,
            timestamp=timestamp,
            service=data["service"],
            severity=severity,
            request_id=request_id,
            message=data["message"]
        )

    except (ValueError, TypeError):
        return None


def parse_log_file(file_path: str):

    events = []

    with open(file_path, encoding="utf-8") as log_file:

        for line_number, line in enumerate(
            log_file, start=1
        ):

            event = parse_log_line(
                line,
                line_number
            )

            if event:
                events.append(event)

    return events
