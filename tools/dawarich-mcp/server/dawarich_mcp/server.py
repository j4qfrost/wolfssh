from __future__ import annotations

from collections import defaultdict
from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import DawarichClient

mcp = FastMCP("dawarich")


def _client() -> DawarichClient:
    return DawarichClient()


@mcp.tool()
async def get_points(
    start_at: str | None = None,
    end_at: str | None = None,
    page: int = 1,
    per_page: int = 100,
) -> dict[str, Any]:
    """Return raw GPS points for the authenticated user.

    Dates are ISO 8601 (e.g. "2025-01-01" or "2025-01-01T00:00:00Z").
    Response includes pagination metadata; call again with page+1 to walk the rest.
    """
    client = _client()
    try:
        return await client.points(start_at, end_at, page, per_page)
    finally:
        await client.aclose()


@mcp.tool()
async def get_visits(start_at: str | None = None, end_at: str | None = None) -> list[dict[str, Any]]:
    """Return stays at named places (visits) in the given range. ISO 8601 dates."""
    client = _client()
    try:
        return await client.visits(start_at, end_at)
    finally:
        await client.aclose()


@mcp.tool()
async def get_stats(year: int | None = None, month: int | None = None) -> dict[str, Any]:
    """Return aggregate stats: distance traveled, countries, cities, point count.

    Omit args for all-time; pass year (and optionally month) to scope.
    """
    client = _client()
    try:
        return await client.stats(year, month)
    finally:
        await client.aclose()


@mcp.tool()
async def list_imports() -> list[dict[str, Any]]:
    """List the Timeline/Takeout imports that have been uploaded and their status."""
    client = _client()
    try:
        return await client.imports()
    finally:
        await client.aclose()


@mcp.tool()
async def list_areas() -> list[dict[str, Any]]:
    """List user-defined areas (geofences) configured in Dawarich."""
    client = _client()
    try:
        return await client.areas()
    finally:
        await client.aclose()


@mcp.tool()
async def summarize_trips(start_at: str, end_at: str, max_days: int = 60) -> dict[str, Any]:
    """Day-by-day summary of visits between two dates.

    Buckets visits by local date and returns a compact list per day: place names
    and visit count. Capped at max_days to keep responses model-friendly.
    """
    client = _client()
    try:
        visits = await client.visits(start_at, end_at)
    finally:
        await client.aclose()

    by_day: dict[str, list[str]] = defaultdict(list)
    for v in visits:
        started = v.get("started_at") or v.get("start_at") or ""
        day = started[:10] if started else "unknown"
        name = (
            v.get("name")
            or (v.get("place") or {}).get("name")
            or v.get("address")
            or "unnamed"
        )
        by_day[day].append(name)

    days_sorted = sorted(by_day.keys())[:max_days]
    return {
        "range": {"start_at": start_at, "end_at": end_at},
        "day_count": len(days_sorted),
        "truncated": len(by_day) > max_days,
        "days": [
            {"date": d, "visit_count": len(by_day[d]), "places": by_day[d]}
            for d in days_sorted
        ],
    }
