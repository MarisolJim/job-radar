"""SmartRecruiters job boards (ServiceNow and many others).

Public API (documented, no auth):
    https://api.smartrecruiters.com/v1/companies/{company}/postings?limit=&offset=
The {company} identifier is the token in the careers URL
    jobs.smartrecruiters.com/{company}/...  ->  slug = company identifier

Config entry:
    - { name: ServiceNow, ats: smartrecruiters, slug: ServiceNow, priority: 1 }
"""

from __future__ import annotations

from datetime import datetime, timezone

from models import Job
from sources.base import register, http_get_json

API = "https://api.smartrecruiters.com/v1/companies/{slug}/postings"
PAGE = 100  # SmartRecruiters allows up to 100 per page
MAX_JOBS = 3000


def _iso(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            timezone.utc
        ).isoformat()
    except ValueError:
        return value


@register("smartrecruiters")
def fetch(cfg: dict) -> list[Job]:
    slug = cfg["slug"]
    url = API.format(slug=slug)

    jobs: list[Job] = []
    offset = 0
    total = None
    while offset < MAX_JOBS:
        data = http_get_json(url, params={"limit": PAGE, "offset": offset})
        if not isinstance(data, dict):
            break
        if total is None:
            total = data.get("totalFound", 0)
        content = data.get("content", []) or []
        if not content:
            break
        for p in content:
            loc = p.get("location") or {}
            full = loc.get("fullLocation") or ", ".join(
                x for x in [loc.get("city"), loc.get("region"), loc.get("country", "").upper()] if x
            )
            jobs.append(
                Job(
                    source="smartrecruiters",
                    company=cfg["name"],
                    title=(p.get("name") or "").strip(),
                    url=f"https://jobs.smartrecruiters.com/{slug}/{p.get('id')}",
                    location=full or None,
                    remote=bool(loc.get("remote")) or None,
                    posted_at=_iso(p.get("releasedDate")),
                    department=(p.get("department") or {}).get("label"),
                    priority=int(cfg.get("priority", 0)),
                )
            )
        offset += PAGE
        if total is not None and offset >= total:
            break
    return jobs
