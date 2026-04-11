#!/usr/bin/env python3
"""
Push morning email run results to ClickUp.

Reads a JSON payload from stdin and creates/updates tasks in the
'Morning Email Log > Email Inbox' list in the Ruwi's Cakes Orders space.

Usage:
    echo '<json>' | python3 scripts/clickup_push.py

Input JSON schema:
{
  "tasks": [
    {
      "thread_id": "...",          # unique ID for matching (message-id or thread id)
      "name": "...",               # task name shown in ClickUp
      "category": "Order Review",  # Order Review | Draft Saved | Needs Attention | Ongoing Thread | Already Flagged
      "status": "Active",          # Active | Drafted | Resolved
      "sender": "...",             # email address of sender
      "description": "...",        # full detail block shown in task body
      "order_number": "...",       # optional, orders only
      "delivery_date": "YYYY-MM-DD"  # optional, orders only
    }
  ]
}
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from typing import Optional

API_BASE = "https://api.clickup.com/api/v2"
WORKSPACE_ID = "9003020649"
SPACE_ID = os.environ.get("CLICKUP_DEV_SPACE_ID", "90030047191")
FOLDER_NAME = "Morning Email Log"
LIST_NAME = "Email Inbox"

# The entire Ruwi's Cakes Orders space is off-limits — no folders, lists, or tasks
# may be created or modified there by this script under any circumstances.
PROTECTED_SPACE_IDS = {
    "90030046549": "Ruwi's Cakes Orders",
}

# Individual production lists within protected spaces (belt-and-suspenders).
PROTECTED_LIST_IDS = {
    "900300267915": "Orders 2023",
    "900300318766": "Inventory",
    "900303153935": "Wedding Cake Orders",
    "901603426422": "New - Pending Orders",
}


def _assert_space_not_protected(space_id: str) -> None:
    """Raise immediately if space_id is a protected production space."""
    if space_id in PROTECTED_SPACE_IDS:
        name = PROTECTED_SPACE_IDS[space_id]
        raise RuntimeError(
            f"SAFETY BLOCK: attempted to write to protected space '{name}' ({space_id}). "
            "This script may only write to the Ruwi's Cakes Development space."
        )


def _assert_not_protected(list_id: str) -> None:
    """Raise immediately if list_id is a protected production list."""
    if list_id in PROTECTED_LIST_IDS:
        name = PROTECTED_LIST_IDS[list_id]
        raise RuntimeError(
            f"SAFETY BLOCK: attempted to write to protected list '{name}' ({list_id}). "
            "This script may only write to the Morning Email Log > Email Inbox list."
        )

CATEGORY_OPTIONS = [
    {"name": "Order Review",    "color": "#BF4ACC", "orderindex": 0},
    {"name": "Needs Attention", "color": "#f50000", "orderindex": 1},
    {"name": "Ongoing Thread",  "color": "#f8ae00", "orderindex": 2},
    {"name": "Already Flagged", "color": "#87909e", "orderindex": 3},
    {"name": "Owner Replied",   "color": "#0075ff", "orderindex": 4},
]

CATEGORY_INDEX = {opt["name"]: opt["orderindex"] for opt in CATEGORY_OPTIONS}

# Status names are resolved dynamically from the list at runtime — see _get_status_names()
_STATUS_CACHE: dict[str, str] = {}  # list_id → (open_status, closed_status)


def _get_status_names(list_id: str) -> tuple[str, str]:
    """Return (open_status_name, closed_status_name) for the given list."""
    if list_id in _STATUS_CACHE:
        return _STATUS_CACHE[list_id]  # type: ignore[return-value]
    statuses = _request("GET", f"/list/{list_id}").get("statuses", [])
    open_status   = next((s["status"] for s in statuses if s["type"] == "open"),   "to do")
    closed_status = next((s["status"] for s in statuses if s["type"] == "closed"), "complete")
    _STATUS_CACHE[list_id] = (open_status, closed_status)
    return open_status, closed_status



def _request(method: str, path: str, data: Optional[dict] = None) -> dict:
    api_key = os.environ.get("CLICKUP_API_KEY")
    if not api_key:
        raise EnvironmentError("CLICKUP_API_KEY is not set")

    url = f"{API_BASE}{path}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        raise RuntimeError(f"ClickUp {exc.code} on {method} {path}: {detail}") from exc


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------

def _get_or_create_folder(space_id: str, name: str) -> str:
    _assert_space_not_protected(space_id)
    folders = _request("GET", f"/space/{space_id}/folder?archived=false").get("folders", [])
    for f in folders:
        if f["name"] == name:
            return f["id"]
    result = _request("POST", f"/space/{space_id}/folder", {"name": name})
    print(f"  Created folder: {name} ({result['id']})", file=sys.stderr)
    return result["id"]


def _get_or_create_list(folder_id: str, name: str) -> str:
    lists = _request("GET", f"/folder/{folder_id}/list?archived=false").get("lists", [])
    for lst in lists:
        if lst["name"] == name:
            _assert_not_protected(lst["id"])
            return lst["id"]
    result = _request("POST", f"/folder/{folder_id}/list", {"name": name})
    list_id = result["id"]
    _assert_not_protected(list_id)
    print(f"  Created list: {name} ({list_id})", file=sys.stderr)
    return list_id


def _get_or_create_fields(list_id: str) -> dict[str, str]:
    """Ensure required custom fields exist. Returns {field_name: field_id}."""
    existing = {f["name"]: f["id"] for f in _request("GET", f"/list/{list_id}/field").get("fields", [])}

    wanted: list[tuple[str, str, Optional[dict]]] = [
        ("Thread ID",     "short_text", None),
        ("Sender",        "short_text", None),
        ("Order Number",  "short_text", None),
        ("Delivery Date", "date",       None),
        ("Category",      "drop_down",  {"options": CATEGORY_OPTIONS}),
    ]

    for name, ftype, type_config in wanted:
        if name not in existing:
            payload: dict = {"name": name, "type": ftype}
            if type_config:
                payload["type_config"] = type_config
            try:
                result = _request("POST", f"/list/{list_id}/field", payload)
                # Response wraps the field object under a "field" key
                field_obj = result.get("field", result)
                existing[name] = field_obj["id"]
                print(f"  Created custom field: {name}", file=sys.stderr)
            except RuntimeError as exc:
                if "already exists" in str(exc).lower():
                    # Field exists at space level — re-fetch to get its ID
                    refreshed = _request("GET", f"/list/{list_id}/field").get("fields", [])
                    for f in refreshed:
                        if f["name"] == name:
                            existing[name] = f["id"]
                            break
                else:
                    raise

    return existing


def setup() -> tuple[str, dict[str, str]]:
    """Ensure folder/list/fields exist. Returns (list_id, field_ids)."""
    folder_id = _get_or_create_folder(SPACE_ID, FOLDER_NAME)
    list_id   = _get_or_create_list(folder_id, LIST_NAME)
    field_ids = _get_or_create_fields(list_id)
    return list_id, field_ids


# ---------------------------------------------------------------------------
# Task upsert
# ---------------------------------------------------------------------------

def _find_task(list_id: str, thread_id: str, thread_field_id: str) -> Optional[tuple[str, bool]]:
    """Return (task_id, is_manually_closed) for a matching task, or None."""
    page = 0
    while True:
        resp = _request("GET", f"/list/{list_id}/task?page={page}&include_closed=true")
        tasks = resp.get("tasks", [])
        if not tasks:
            break
        for t in tasks:
            for cf in t.get("custom_fields", []):
                if cf["id"] == thread_field_id and cf.get("value") == thread_id:
                    is_closed = t.get("status", {}).get("type") == "closed"
                    return t["id"], is_closed
        if not resp.get("last_page"):
            page += 1
        else:
            break
    return None


def _build_custom_fields(field_ids: dict, task: dict) -> list[dict]:
    cf = [
        {"id": field_ids["Thread ID"], "value": task["thread_id"]},
        {"id": field_ids["Sender"],    "value": task.get("sender", "")},
    ]

    if task.get("order_number"):
        cf.append({"id": field_ids["Order Number"], "value": task["order_number"]})

    if task.get("delivery_date"):
        try:
            dt = datetime.strptime(task["delivery_date"], "%Y-%m-%d")
            cf.append({"id": field_ids["Delivery Date"], "value": int(dt.timestamp() * 1000)})
        except ValueError:
            pass

    category = task.get("category", "Draft Saved")
    if category in CATEGORY_INDEX:
        cf.append({"id": field_ids["Category"], "value": CATEGORY_INDEX[category]})

    return cf


def upsert_task(list_id: str, field_ids: dict, task: dict) -> None:
    _assert_not_protected(list_id)
    thread_field_id = field_ids["Thread ID"]
    found = _find_task(list_id, task["thread_id"], thread_field_id)

    open_status, closed_status = _get_status_names(list_id)
    resolved = task.get("status") == "Resolved"

    payload = {
        "name":          task["name"],
        "description":   task.get("description", ""),
        "custom_fields": _build_custom_fields(field_ids, task),
    }

    if found:
        existing_id, is_manually_closed = found
        # Never reopen a task the owner has manually marked complete
        if is_manually_closed:
            payload["status"] = closed_status
            print(f"  Updated (kept closed): {task['name']}", file=sys.stderr)
        else:
            payload["status"] = closed_status if resolved else open_status
            print(f"  Updated: {task['name']}", file=sys.stderr)
        _request("PUT", f"/task/{existing_id}", payload)
    else:
        payload["status"] = closed_status if resolved else open_status
        _request("POST", f"/list/{list_id}/task", payload)
        print(f"  Created: {task['name']}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    raw = sys.stdin.read().strip()
    if not raw:
        print("Error: no input provided via stdin", file=sys.stderr)
        sys.exit(1)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON — {exc}", file=sys.stderr)
        sys.exit(1)

    tasks = payload.get("tasks", [])
    if not tasks:
        print("No tasks to push.", file=sys.stderr)
        return

    print(f"Setting up ClickUp list...", file=sys.stderr)
    list_id, field_ids = setup()

    print(f"Pushing {len(tasks)} task(s)...", file=sys.stderr)
    errors = []
    for task in tasks:
        try:
            upsert_task(list_id, field_ids, task)
        except Exception as exc:
            errors.append(f"{task.get('name', '?')}: {exc}")
            print(f"  ERROR: {exc}", file=sys.stderr)

    list_url = f"https://app.clickup.com/{WORKSPACE_ID}/v/l/{list_id}"
    result = {"list_url": list_url, "pushed": len(tasks) - len(errors), "errors": errors}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
