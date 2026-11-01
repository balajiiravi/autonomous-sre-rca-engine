
import hashlib

from collections import deque
from collections import defaultdict
from datetime import timezone
from typing import Optional

from ingestion.schemas import (
    TelemetryEvent,
    IncidentNode,
    IncidentReport
)


# A temporary topology contract.
# Phase 3 will retrieve this from Neo4j.

DEPENDENCIES = {
    "frontend-service": ["payment-service"],
    "payment-service": ["inventory-db"],
    "inventory-db": []
}

SEVERITY_RANK = {
    "DEBUG": 0,
    "INFO": 1,
    "WARNING": 2,
    "ERROR": 3,
    "CRITICAL": 4
}


def build_reverse_dependencies():

    reverse = defaultdict(list)

    for service, dependencies in DEPENDENCIES.items():

        for dependency in dependencies:
            reverse[dependency].append(service)

    return reverse


def get_dependency_distance(
    start_service: str,
    target_service: str
) -> Optional [int ]:
    """
    Calculate distance from the alerting service
    by traversing its dependencies.

    Returns None if target is not reachable.
    """

    queue = deque([(start_service, 0)])
    visited = set()

    while queue:

        current_service, distance = queue.popleft()

        if current_service == target_service:
            return distance

        if current_service in visited:
            continue

        visited.add(current_service)

        for dependency in DEPENDENCIES.get(
            current_service, []
        ):
            if dependency not in visited:
                queue.append(
                    (dependency, distance + 1)
                )

    return None


def get_dependency_depth(service: str) -> int:

    dependencies = DEPENDENCIES.get(service, [])

    if not dependencies:
        return 0

    return 1 + max(
        get_dependency_depth(dependency)
        for dependency in dependencies
    )


def build_incident_tree(
    root_service: str,
    events_by_service: dict,
    reverse_dependencies: dict,
    visited=None
) -> IncidentNode:

    if visited is None:
        visited = set()

    if root_service in visited:
        return IncidentNode(service=root_service)

    visited.add(root_service)

    service_events = events_by_service.get(
        root_service, []
    )

    failed_events = [
        event for event in service_events
        if event.severity in ("ERROR", "CRITICAL")
    ]

    representative = (
        max(
            failed_events,
            key=lambda event: (
                SEVERITY_RANK[event.severity],
                event.sequence
            )
        )
        if failed_events else None
    )

    children = []

    for dependent_service in reverse_dependencies.get(
        root_service, []
    ):

        if dependent_service in events_by_service:

            children.append(
                build_incident_tree(
                    dependent_service,
                    events_by_service,
                    reverse_dependencies,
                    visited
                )
            )

    return IncidentNode(
        service=root_service,
        event_ids=[
            event.event_id for event in service_events
        ],
        failure_type=(
            representative.event_type
            if representative else None
        ),
        severity=(
            representative.severity
            if representative else None
        ),
        evidence=[
            event.message for event in service_events
        ],
        children=children
    )


def correlate_events(
    events: list[TelemetryEvent]
) -> list[IncidentReport]:

    # Group events by request ID.
    grouped = defaultdict(list)

    for event in events:

        # Never combine unrelated events with missing IDs.
        if event.request_id == "untracked":
            continue

        grouped[event.request_id].append(event)

    incidents = []

    reverse_dependencies = build_reverse_dependencies()

    for request_id, request_events in grouped.items():

        # Ignore healthy requests.
        failed_events = [
            event for event in request_events
            if event.severity in ("ERROR", "CRITICAL")
        ]

        if not failed_events:
            continue

        events_by_service = defaultdict(list)

        for event in request_events:
             if event.service in DEPENDENCIES:
                events_by_service[event.service].append(event)

       
        failed_services = {
            event.service for event in failed_events
        }

        # Identify the service at the entry point of this request.
        alerting_service = (
            "frontend-service"
            if "frontend-service" in failed_services
            else next(iter(failed_services))
        )

        # Calculate each failing service's distance
        # from the alerting service along dependency edges.
        alerting_service = (
            "frontend-service"
            if "frontend-service" in failed_services
            else next(iter(failed_services))
        )
        reachable_candidates = []

        for service in failed_services:

            distance = get_dependency_distance(
                alerting_service,
                service
            )


            print(
                f"DEBUG: service={service}, "
                f"distance={distance}"
            )


            if distance is not None:
                reachable_candidates.append(
                    (service, distance)
                )

            print("DEBUG: reachable_candidates =", reachable_candidates)

        # Prefer the furthest downstream failing dependency.
        if reachable_candidates:

            root_candidate = max(
                reachable_candidates,
                key=lambda item: (
                    item[1],
                    max(
                        SEVERITY_RANK[event.severity]
                        for event in failed_events
                        if event.service == item[0]
                    )
                )
            )[0]

            candidate_method = (
                "furthest_reachable_failing_dependency"
            )

        else:

            # No dependency path established.
            # Use severity only as a fallback candidate.
            root_candidate = max(
                failed_services,
                key=lambda service: max(
                    SEVERITY_RANK[event.severity]
                    for event in failed_events
                    if event.service == service
                )
            )
            print("\n--- FINAL ROOT SELECTION ---")
            print("Candidates:", reachable_candidates)
            print("Selected root:", root_candidate)
            print("Selection method:", candidate_method)
            candidate_method = (
                "highest_severity_fallback_no_topology_path"
            )


        tree = build_incident_tree(
            root_candidate,
            events_by_service,
            reverse_dependencies
        )

        highest_severity = max(
            failed_events,
            key=lambda event: SEVERITY_RANK[event.severity]
        ).severity

        critical_root = any(
            event.service == root_candidate
            and event.severity == "CRITICAL"
            for event in failed_events
        )

        downstream_failure = any(
            event.service != root_candidate
            for event in failed_events
        )

        # This is a heuristic score, not a calibrated probability.
        confidence = (
            0.85 if critical_root and downstream_failure
            else 0.65 if critical_root
            else 0.40
        )

        incident_id = "INC-" + hashlib.sha256(
            request_id.encode()
        ).hexdigest()[:12].upper()

        print("\n--- REPORT CONSTRUCTION ---")
        print("Root candidate being saved:", root_candidate)
        incidents.append(
            IncidentReport(
                incident_id=incident_id,
                started_at=min(
                    event.timestamp for event in request_events
                ),
                ended_at=max(
                    event.timestamp for event in request_events
                ),
                alerting_service=alerting_service,
                severity=highest_severity,
                request_ids=[request_id],
                events=request_events,
                root_cause_candidate=root_candidate,
                propagation_tree=tree,
                correlation_method="request_id",
                confidence=confidence,
                metadata={
                    "candidate_method": candidate_method,
                    "is_confirmed_root_cause": False,
                    "heuristic_confidence": True
                }
            )
        )

    return incidents
