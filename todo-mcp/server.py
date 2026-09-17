"""todo-mcp — a deadline/task tracker exposed as an MCP server.

Tasks live in tasks.json next to this file (not committed — see .gitignore).
`due` is a plain ISO date ('2026-09-22') or datetime ('2026-09-22T13:30');
keeping it ISO now is what makes syncing to a real calendar later a
translation step, not a rewrite.
"""
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from mcp.server.fastmcp import FastMCP

DATA_FILE = Path(__file__).parent / "tasks.json"

mcp = FastMCP(
    "todo-mcp",
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8001)),
)


def _load() -> list[dict]:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return []


def _save(tasks: list[dict]) -> None:
    DATA_FILE.write_text(json.dumps(tasks, indent=2))


def _parse_due(due: str) -> datetime | None:
    if not due:
        return None
    d = datetime.fromisoformat(due)
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def _format(t: dict, now: datetime) -> str:
    d = _parse_due(t["due"])
    overdue = d is not None and d < now and not t["done"]
    marker = "[x]" if t["done"] else ("[!]" if overdue else "[ ]")
    cat = f"{t['category']}: " if t["category"] else ""
    due_str = ""
    if t["due"]:
        due_str = f" — due {t['due']}" + (" (OVERDUE)" if overdue else "")
    return f"{marker} {t['id']} {cat}{t['title']}{due_str}"


@mcp.tool()
def add_task(title: str, category: str = "", due: str = "", notes: str = "", source: str = "manual") -> str:
    """Add a task. due is an ISO date/datetime ('2026-09-22' or '2026-09-22T13:30'); leave blank if unknown."""
    tasks = _load()
    task = {
        "id": uuid.uuid4().hex[:8],
        "title": title,
        "category": category,
        "due": due,
        "notes": notes,
        "source": source,
        "done": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    tasks.append(task)
    _save(tasks)
    return "Added " + _format(task, datetime.now(timezone.utc))


@mcp.tool()
def list_tasks(scope: str = "all", include_done: bool = False) -> str:
    """List tasks. scope: 'today', 'week' (next 7 days + overdue), 'urgent' (overdue or due within 48h), or 'all'."""
    now = datetime.now(timezone.utc)

    def matches(t: dict) -> bool:
        if t["done"] and not include_done:
            return False
        d = _parse_due(t["due"])
        if scope == "all":
            return True
        if d is None:
            return False
        if scope == "today":
            return d.date() == now.date()
        if scope == "week":
            return d < now or d <= now + timedelta(days=7)
        if scope == "urgent":
            return d <= now + timedelta(hours=48)
        return True

    filtered = [t for t in _load() if matches(t)]
    filtered.sort(key=lambda t: (_parse_due(t["due"]) is None, _parse_due(t["due"]) or now))

    if not filtered:
        return f"Nothing in '{scope}'."
    return "\n".join(_format(t, now) for t in filtered)


@mcp.tool()
def complete_task(task_id: str) -> str:
    """Mark a task done by its id."""
    tasks = _load()
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = True
            _save(tasks)
            return f"Completed: {t['title']}"
    return f"No task with id {task_id}"


@mcp.tool()
def delete_task(task_id: str) -> str:
    """Delete a task by its id."""
    tasks = _load()
    remaining = [t for t in tasks if t["id"] != task_id]
    if len(remaining) == len(tasks):
        return f"No task with id {task_id}"
    _save(remaining)
    return f"Deleted task {task_id}"


@mcp.tool()
def update_task(task_id: str, title: str = "", category: str = "", due: str = "", notes: str = "") -> str:
    """Update fields of an existing task. Leave a field blank to keep its current value."""
    tasks = _load()
    for t in tasks:
        if t["id"] == task_id:
            if title:
                t["title"] = title
            if category:
                t["category"] = category
            if due:
                t["due"] = due
            if notes:
                t["notes"] = notes
            _save(tasks)
            return "Updated " + _format(t, datetime.now(timezone.utc))
    return f"No task with id {task_id}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
