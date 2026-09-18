"""Lever job boards.

Public feed: https://api.lever.co/v0/postings/{slug}?mode=json
The slug is the company handle in the careers URL, e.g.
    jobs.lever.co/netflix  ->  slug = "netflix"

Lever gives a real posting timestamp (createdAt, ms epoch), which is ideal for
the 'how fresh is this?' signal.
"""

from __future__ import annotations

from datetime import datetime, timezone

from models import Job
from sources.base import register, http_get_json

API = "https://api.lever.co/v0/postings/{slug}"


def _iso_from_ms(ms: int | None) -> str | None:
    if not ms:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()
    except (ValueError, OSError):
        return None


@register("lever")
def fetch(cfg: dict) -> list[Job]:
    slug = cfg["slug"]
    data = http_get_json(API.format(slug=slug), params={"mode": "json"})
    postings = data if isinstance(data, list) else []

    jobs: list[Job] = []
    for p in postings:
        cats = p.get("categories") or {}
        loc = cats.get("location")
        workplace = (p.get("workplaceType") or "").lower()
        jobs.append(
            Job(
                source="lever",
                company=cfg["name"],
                title=p.get("text", "").strip(),
                url=p.get("hostedUrl", ""),
                location=loc,
                remote=(workplace == "remote") or ("remote" in (loc or "").lower()) or None,
                posted_at=_iso_from_ms(p.get("createdAt")),
                department=cats.get("team"),
                priority=int(cfg.get("priority", 0)),
            )
        )
    return jobs
