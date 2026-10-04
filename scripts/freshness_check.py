import json
import os
import sys
from datetime import datetime, timezone

# Locate repository root (whether script runs from scripts/ or from root)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(SCRIPT_DIR) == "scripts":
    REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
else:
    REPO_ROOT = SCRIPT_DIR

EVENTS_FILE = os.path.join(REPO_ROOT, "events.json")
REPORT_FILE = os.path.join(REPO_ROOT, "schedule_status.json")

def load_existing_events(filepath):
    """Loads existing events.json safely."""
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found. Creating a starter dataset.")
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        sys.exit(1)

def validate_event_record(event, index):
    """Ensures each event has required fields and valid dates within the festival window."""
    errors = []
    required_keys = ["id", "title", "date", "dayLabel", "time", "venue", "area", "category"]
    
    for key in required_keys:
        if not event.get(key):
            errors.append(f"Event #{index} missing required field '{key}'")
            
    # Validate date range (2026 Cork Jazz runs Oct 22-26)
    valid_dates = ["2026-10-22", "2026-10-23", "2026-10-24", "2026-10-25", "2026-10-26"]
    if event.get("date") and event.get("date") not in valid_dates:
        errors.append(f"Event '{event.get('title')}' has invalid date {event.get('date')}")
        
    return errors

def run_check():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting Cork Jazz Schedule Freshness Check...")
    
    events = load_existing_events(EVENTS_FILE)
    total_events = len(events)
    print(f"Loaded {total_events} events from {EVENTS_FILE}")
    
    # 1. Check for Duplicate IDs
    seen_ids = set()
    duplicate_ids = []
    for ev in events:
        eid = ev.get("id")
        if eid in seen_ids:
            duplicate_ids.append(eid)
        seen_ids.add(eid)
        
    if duplicate_ids:
        print(f"WARNING: Detected duplicate event IDs: {duplicate_ids}")

    # 2. Schema Validation
    all_validation_errors = []
    for idx, ev in enumerate(events):
        errs = validate_event_record(ev, idx)
        if errs:
            all_validation_errors.extend(errs)

    if all_validation_errors:
        print("Schema Validation Warnings:")
        for err in all_validation_errors:
            print(f"  - {err}")
    else:
        print("All event schemas passed validation.")

    # 3. Known Lineup Normalizations & Accuracy Rules
    updates_made = 0
    for ev in events:
        # Enforce Coughlan's ticketed pricing correction
        if ev.get("id") == "fri-5" or ("Paddy Dennehy" in ev.get("title", "") and "Coughlan" in ev.get("venue", "")):
            if "free" in ev.get("price", "").lower():
                ev["price"] = "Ticketed (€20)"
                updates_made += 1
                print("Applied fix: Coughlan's Paddy Dennehy corrected to Ticketed (€20)")

        # Enforce Cantys Hollyz start time
        if ev.get("id") == "sat-26" and ev.get("time") == "9:00pm":
            ev["time"] = "9:30pm"
            updates_made += 1
            print("Applied fix: Cantys The Hollyz adjusted to 9:30pm")

        # Enforce Crane Lane Hollyz start time
        if ev.get("id") == "sun-35" and ev.get("time") == "9:00pm":
            ev["time"] = "9:30pm"
            updates_made += 1
            print("Applied fix: Crane Lane The Hollyz adjusted to 9:30pm")

    # 4. Save updated events if adjustments were made
    if updates_made > 0:
        with open(EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
        print(f"Saved {updates_made} schedule updates back to {EVENTS_FILE}")

    # 5. Write Health Report metadata
    report = {
        "lastCheckedUtc": datetime.now(timezone.utc).isoformat(),
        "totalGigsIndexed": total_events,
        "uniqueVenuesCount": len(set(e.get("venue") for e in events if e.get("venue"))),
        "duplicateIdsFound": duplicate_ids,
        "validationErrors": all_validation_errors,
        "status": "healthy" if not all_validation_errors and not duplicate_ids else "review_needed"
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Freshness status report written to {REPORT_FILE}")
    print("Daily freshness check complete.")

if __name__ == "__main__":
    run_check()