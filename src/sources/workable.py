"""Workable job boards (Hugging Face and many nonprofits/small orgs).

Public embed API (no auth):
    POST https://apply.workable.com/api/v3/accounts/{account}/jobs
The {account} is the subdomain in the careers URL
    apply.workable.com/{account}/  ->  slug = account

Config entry:
    - { name: Hugging Face, ats: workable, slug: huggingface, priority: 1 }
"""

from __future__ import annotations

import time

import requests

from models import Job
from sources.base import register, HEADERS, TIMEOUT

API = "https://apply.workable.com/api/v3/accounts/{slug}/jobs"
MAX_PAGES = 20  # safety; each page returns up to 100 jobs


def _post_with_retry(url, json_body, headers, retries=3):
    """Workable's embed API rate-limits bursts (429). Back off and retry."""
    for attempt in range(retries):
        resp = requests.post(url, json=json_body, headers=headers, timeout=TIMEOUT)
        if resp.status_code == 429 and attempt < retries - 1:
            time.sleep(2 * (attempt + 1))
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return resp.json()


@register("workable")
def fetch(cfg: dict) -> list[Job]:
    slug = cfg["slug"]
    url = API.format(slug=slug)
    headers = {**HEADERS, "Content-Type": "application/json"}

    jobs: list[Job] = []
    token = None
    for _ in range(MAX_PAGES):
        body = {"query": "", "location": [], "department": [], "worktype": [], "remote": []}
        if token:
            body["token"] = token
        data = _post_with_retry(url, body, headers)
        results = data.get("results", []) or []
        if not results:
            break
        for p in results:
            loc = p.get("location") or {}
            city = loc.get("city")
            country = loc.get("country")
            loc_str = ", ".join(x for x in [city, loc.get("region"), country] if x) or None
            jobs.append(
                Job(
                    source="workable",
                    company=cfg["name"],
                    title=(p.get("title") or "").strip(),
                    url=f"https://apply.workable.com/{slug}/j/{p.get('shortcode')}/",
                    location=loc_str,
                    remote=bool(p.get("remote")) or None,
                    priority=int(cfg.get("priority", 0)),
                )
            )
        token = data.get("nextPage") or data.get("token")
        if not token:
            break
    return jobs
