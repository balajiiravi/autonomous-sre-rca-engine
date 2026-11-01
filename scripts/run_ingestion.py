
import json
from pathlib import Path

from ingestion.log_parser import parse_log_file
from ingestion.normalizer import normalize_events
from ingestion.incident_correlator import correlate_events


PROJECT_ROOT = Path(__file__).resolve().parent.parent

LOG_FILE = PROJECT_ROOT / "production_telemetry.log"

OUTPUT_DIR = PROJECT_ROOT / "data" / "incidents"


def main():

    print("\n=== AUTONOMOUS SRE TELEMETRY INGESTION ===")

    if not LOG_FILE.exists():
        print("ERROR: Telemetry log file not found.")
        return

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # STEP 1: Parse
    print("\n[1/5] Parsing raw telemetry...")

    events = parse_log_file(str(LOG_FILE))

    print(f"Parsed events: {len(events)}")

    if not events:
        print("No valid telemetry events found.")
        return

    # STEP 2: Normalize
    print("\n[2/5] Normalizing events...")

    events = normalize_events(events)

    for event in events:
        print(
            f"{event.service:<20} "
            f"{event.severity:<10} "
            f"{event.event_type}"
        )

    # STEP 3: Correlate
    print("\n[3/5] Correlating incidents...")

    incidents = correlate_events(events)

    print(f"Incidents detected: {len(incidents)}")

    # STEP 4: Persist
    print("\n[4/5] Persisting incident reports...")

    for incident in incidents:

        output_file = (
            OUTPUT_DIR /
            f"{incident.incident_id}.json"
        )

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                incident.model_dump(mode="json"),
                file,
                indent=4,
                default=str
            )

        print(f"Saved: {output_file.name}")

    # STEP 5: Summary
    print("\n[5/5] Pipeline summary")

    for incident in incidents:

        print(f"\nIncident: {incident.incident_id}")
        print(f"Alerting service: {incident.alerting_service}")
        print(f"Root cause candidate: {incident.root_cause_candidate}")
        print(f"Severity: {incident.severity}")
        print(f"Confidence heuristic: {incident.confidence}")

    print("\n=== INGESTION COMPLETED ===")


if __name__ == "__main__":
    main()
