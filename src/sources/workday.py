"""Workday job boards (Adobe, Nvidia, and many enterprise leaders).

Unlike Greenhouse/Lever/Ashby, Workday needs three coordinates, taken from the
company's careers URL, e.g.:
    https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced
        host = adobe.wd5.myworkdayjobs.com
        site = external_experienced
The tenant is the first label of the host ("adobe"). The public API is a POST
with offset pagination:
    POST https://{host}/wday/cxs/{tenant}/{site}/jobs

Config entry:
    - { name: Adobe, ats: workday, host: adobe.wd5.myworkdayjobs.com,
        site: external_experienced, priority: 1 }
"""

from __future__ import annotations

import re

import requests

from models import Job
from sources.base import register, HEADERS, TIMEOUT

# Workday's list view collapses multi-location jobs to "2 Locations", which
# tells the US filter nothing. The real primary location is in the URL path,
# e.g. /job/US-CA-Santa-Clara/... or /job/Taiwan-Taipei/... — use that instead.
_MULTI = re.compile(r"^\d+\s+locations", re.IGNORECASE)


def _loc_from_path(path: str) -> str | None:
    m = re.search(r"/job/([^/]+)/", path or "")
    return m.group(1).replace("-", " ") if m else None

PAGE = 20  # Workday caps the list endpoint at 20 per request
MAX_JOBS = 3000  # safety ceiling so a huge board can't loop forever


def _post(url: str, offset: int) -> dict:
    body = {"appliedFacets": {}, "limit": PAGE, "offset": offset, "searchText": ""}
    headers = {**HEADERS, "Content-Type": "application/json"}
    resp = requests.post(url, json=body, headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


@register("workday")
def fetch(cfg: dict) -> list[Job]:
    host = cfg["host"].strip().rstrip("/")
    site = cfg["site"].strip().strip("/")
    tenant = cfg.get("tenant") or host.split(".")[0]
    api = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"

    jobs: list[Job] = []
    offset = 0
    total = None
    while offset < MAX_JOBS:
        data = _post(api, offset)
        if total is None:
            total = data.get("total", 0)
        postings = data.get("jobPostings", []) or []
        if not postings:
            break
        for p in postings:
            path = p.get("externalPath", "")
            loc = p.get("locationsText")
            # If the list view hid the real location behind "N Locations"
            # (or gave none), fall back to the location in the URL path.
            if not loc or _MULTI.match(loc.strip()):
                loc = _loc_from_path(path) or loc
            jobs.append(
                Job(
                    source="workday",
                    company=cfg["name"],
                    title=(p.get("title") or "").strip(),
                    url=f"https://{host}/en-US/{site}{path}" if path else host,
                    location=loc,
                    remote=("remote" in (loc or "").lower()) or None,
                    priority=int(cfg.get("priority", 0)),
                )
            )
        offset += PAGE
        if total is not None and offset >= total:
            break
    return jobs
