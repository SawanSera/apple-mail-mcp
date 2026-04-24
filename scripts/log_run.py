#!/usr/bin/env python3
"""
Append a morning-email run record to docs/guides/run-log.csv.

Usage:
    echo '<json>' | python3 scripts/log_run.py

JSON fields (all optional except date/duration_mins):
    date            YYYY-MM-DD
    day             e.g. Thursday
    start_time      HH:MM
    end_time        HH:MM
    duration_mins   float — calculated from /tmp/morning_email_start.txt if omitted
    emails_scanned  int
    auto_skipped    int
    orders_reviewed int
    order_issues    int
    threads_drafted int   — owner-flagged threads where a draft was saved
    drafts_saved    int   — total green-flagged drafts (unflagged + flagged)
    purple_flagged  int
    already_replied int   — skipped because replied_to was true
    clickup_tasks   int
    notes           str   — free text, e.g. token estimate or anything unusual
"""

import csv
import json
import os
import sys
import time
from datetime import datetime

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "guides", "run-log.csv")
LOG_PATH = os.path.normpath(LOG_PATH)
START_FILE = "/tmp/morning_email_start.txt"

FIELDNAMES = [
    "date",
    "day",
    "start_time",
    "end_time",
    "duration_mins",
    "emails_scanned",
    "auto_skipped",
    "orders_reviewed",
    "order_issues",
    "threads_drafted",
    "drafts_saved",
    "purple_flagged",
    "already_replied",
    "clickup_tasks",
    "notes",
]


def main() -> None:
    data = json.loads(sys.stdin.read())

    # Calculate duration from start file if not provided
    if "duration_mins" not in data and os.path.exists(START_FILE):
        with open(START_FILE) as f:
            start_epoch = int(f.read().strip())
        elapsed = time.time() - start_epoch
        data["duration_mins"] = round(elapsed / 60, 1)

    # Fill date/day if missing
    now = datetime.now()
    data.setdefault("date", now.strftime("%Y-%m-%d"))
    data.setdefault("day", now.strftime("%A"))
    data.setdefault("end_time", now.strftime("%H:%M"))

    # Read start time from file if not in payload
    if "start_time" not in data and os.path.exists(START_FILE + "_time"):
        with open(START_FILE + "_time") as f:
            data["start_time"] = f.read().strip()

    # Write row
    file_exists = os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: data.get(k, "") for k in FIELDNAMES})

    print(f"Run logged → {LOG_PATH}")

    # Clean up temp files
    for path in (START_FILE, START_FILE + "_time"):
        if os.path.exists(path):
            os.remove(path)


if __name__ == "__main__":
    main()
