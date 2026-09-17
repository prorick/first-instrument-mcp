"""your-first-instrument — a sense of time for a model that has none.

Why time? Ask your Claude "how long have we been talking?" WITHOUT this
connected. It can only guess: no clock lives in a context window. This
server is the smallest honest fix — and the pattern generalizes to any
instrument you can imagine. See docs/adr/ for every choice made here.
"""
import os
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "your-first-instrument",
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8000)),
)

@mcp.tool()
def current_time() -> str:
    """The current date and time (UTC and local)."""
    now = datetime.now(timezone.utc)
    return f"UTC: {now.isoformat()} · local: {datetime.now().isoformat()}"

@mcp.tool()
def seconds_since(iso_timestamp: str) -> str:
    """Seconds elapsed since an ISO timestamp (e.g. '2026-09-10T17:15:00')."""
    then = datetime.fromisoformat(iso_timestamp)
    if then.tzinfo is None:
        # Naive timestamps are read as LOCAL time, not UTC. (Bug caught in-room
        # during the R5 leveling test, session 3: a student read the code with
        # their collaborator and noticed line-2 assumed UTC while now() was
        # offset-aware — the audit test, passing in the wild. Thank you.)
        then = then.replace(tzinfo=datetime.now().astimezone().tzinfo)
    delta = datetime.now(timezone.utc) - then
    return f"{delta.total_seconds():.0f} seconds ({delta})"

@mcp.tool()
def percent_of_year_complete(date: str = "") -> str:
    """Percentage of 2026 elapsed, as of now or a given ISO date (e.g. '2026-09-17')."""
    year = 2026
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    if date:
        when = datetime.fromisoformat(date)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
    else:
        when = datetime.now(timezone.utc)
    pct = (when - start).total_seconds() / (end - start).total_seconds() * 100
    return f"{pct:.2f}% of {year} complete (as of {when.isoformat()})"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
