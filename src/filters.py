"""Turn the raw firehose of postings into YOUR shortlist.

All rules come from filters.yaml so you can tune without touching code.
A job is kept only if it passes every enabled rule.
"""

from __future__ import annotations

import re

from models import Job


def _any_match(patterns: list[str], text: str) -> bool:
    text = text.lower()
    return any(p.lower() in text for p in patterns)


class JobFilter:
    def __init__(self, cfg: dict):
        f = cfg or {}
        self.title_include = f.get("title_include", []) or []
        self.title_exclude = f.get("title_exclude", []) or []
        self.location_include = f.get("location_include", []) or []
        self.location_exclude = f.get("location_exclude", []) or []
        self.remote_only = bool(f.get("remote_only", False))

    def match(self, job: Job) -> bool:
        title = job.title or ""
        loc = job.location or ""

        # Title must contain at least one wanted keyword (if any are set)...
        if self.title_include and not _any_match(self.title_include, title):
            return False
        # ...and none of the excluded ones (e.g. "Senior", "Staff", "Manager").
        if self.title_exclude and _any_match(self.title_exclude, title):
            return False

        if self.remote_only and not job.remote:
            # Fall back to a location text check if the source didn't flag remote.
            if "remote" not in loc.lower():
                return False

        if self.location_include and loc:
            if not _any_match(self.location_include, loc):
                return False
        if self.location_exclude and _any_match(self.location_exclude, loc):
            return False

        return True

    def apply(self, jobs: list[Job]) -> list[Job]:
        return [j for j in jobs if self.match(j)]
