"""Ashby job boards.

Public feed: https://api.ashbyhq.com/posting-api/job-board/{slug}
The slug is the org name in the careers URL, e.g.
    jobs.ashbyhq.com/openai  ->  slug = "openai"

Ashby gives publishedAt, a real posting time.
"""

from __future__ import annotations

from datetime import datetime, timezone

from models import Job
from sources.base import register, http_get_json

API = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


def _iso(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            timezone.utc
        ).isoformat()
    except ValueError:
        return value


@register("ashby")
def fetch(cfg: dict) -> list[Job]:
    slug = cfg["slug"]
    data = http_get_json(API.format(slug=slug))
    postings = data.get("jobs", []) if isinstance(data, dict) else []

    jobs: list[Job] = []
    for p in postings:
        loc = p.get("location")
        jobs.append(
            Job(
                source="ashby",
                company=cfg["name"],
                title=p.get("title", "").strip(),
                # jobUrl is the public posting; applyUrl is the apply form.
                url=p.get("jobUrl") or p.get("applyUrl", ""),
                location=loc,
                remote=bool(p.get("isRemote")) or ("remote" in (loc or "").lower()) or None,
                posted_at=_iso(p.get("publishedAt")),
                department=p.get("department") or p.get("team"),
                priority=int(cfg.get("priority", 0)),
            )
        )
    return jobs
