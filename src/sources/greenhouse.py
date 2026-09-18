"""Greenhouse job boards.

Public feed: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
The slug is the board token in a company's careers URL, e.g.
    boards.greenhouse.io/stripe  ->  slug = "stripe"
"""

from __future__ import annotations

from datetime import datetime, timezone

from models import Job
from sources.base import register, http_get_json

API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def _iso(value: str | None) -> str | None:
    if not value:
        return None
    try:
        # Greenhouse returns e.g. "2024-01-05T12:00:00-05:00"
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            timezone.utc
        ).isoformat()
    except ValueError:
        return value


@register("greenhouse")
def fetch(cfg: dict) -> list[Job]:
    slug = cfg["slug"]
    data = http_get_json(API.format(slug=slug), params={"content": "false"})
    jobs_raw = data.get("jobs", []) if isinstance(data, dict) else []

    jobs: list[Job] = []
    for j in jobs_raw:
        loc = (j.get("location") or {}).get("name")
        jobs.append(
            Job(
                source="greenhouse",
                company=cfg["name"],
                title=j.get("title", "").strip(),
                url=j.get("absolute_url", ""),
                location=loc,
                remote=("remote" in (loc or "").lower()) or None,
                posted_at=_iso(j.get("updated_at")),
                priority=int(cfg.get("priority", 0)),
            )
        )
    return jobs
