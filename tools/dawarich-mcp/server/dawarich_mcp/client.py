from __future__ import annotations

import os
from typing import Any

import httpx


class DawarichError(RuntimeError):
    pass


class DawarichClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        base_url = base_url or os.environ.get("DAWARICH_BASE_URL")
        api_key = api_key or os.environ.get("DAWARICH_API_KEY")
        if not base_url:
            raise DawarichError("DAWARICH_BASE_URL is not set")
        if not api_key:
            raise DawarichError("DAWARICH_API_KEY is not set")
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        merged: dict[str, Any] = {"api_key": self._api_key}
        if params:
            merged.update({k: v for k, v in params.items() if v is not None})
        url = f"{self._base_url}/api/v1/{path.lstrip('/')}"
        resp = await self._client.get(url, params=merged)
        if resp.status_code >= 400:
            raise DawarichError(
                f"GET {path} -> {resp.status_code}: {resp.text[:200]}"
            )
        return resp

    async def points(
        self,
        start_at: str | None = None,
        end_at: str | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> dict[str, Any]:
        resp = await self._get(
            "points",
            {"start_at": start_at, "end_at": end_at, "page": page, "per_page": per_page},
        )
        return {
            "points": resp.json(),
            "total_pages": int(resp.headers.get("X-Total-Pages", "1")),
            "current_page": int(resp.headers.get("X-Current-Page", str(page))),
        }

    async def visits(
        self,
        start_at: str | None = None,
        end_at: str | None = None,
    ) -> list[dict[str, Any]]:
        resp = await self._get("visits", {"start_at": start_at, "end_at": end_at})
        return resp.json()

    async def stats(self, year: int | None = None, month: int | None = None) -> dict[str, Any]:
        path = "stats"
        if year is not None:
            path = f"stats/{year}"
            if month is not None:
                path = f"stats/{year}/{month}"
        resp = await self._get(path)
        return resp.json()

    async def imports(self) -> list[dict[str, Any]]:
        resp = await self._get("imports")
        return resp.json()

    async def areas(self) -> list[dict[str, Any]]:
        resp = await self._get("areas")
        return resp.json()
