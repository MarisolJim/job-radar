"""Turn the raw firehose of postings into YOUR shortlist.

All rules come from filters.yaml so you can tune without touching code.
A job is kept only if it passes every enabled rule.
"""

from __future__ import annotations

import re

from models import Job
from usa import is_usa


def _any_match(patterns: list[str], text: str) -> bool:
    text = text.lower()
    return any(p.lower() in text for p in patterns)


def _any_word(patterns: list[str], text: str) -> bool:
    """Whole-word/phrase match. 'engineer i' matches "Engineer I" but NOT
    "Engineer II"; 'ii' matches "Engineer II" but not "iii"."""
    t = text.lower()
    for p in patterns:
        p = p.lower().strip()
        if p and re.search(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])", t):
            return True
    return False


class JobFilter:
    def __init__(self, cfg: dict):
        f = cfg or {}
        self.title_include = f.get("title_include", []) or []
        # Two required groups: a title must match at least one from EACH.
        # title_role_any = it's a software/eng role; title_level_any = it's early-career.
        self.title_role_any = f.get("title_role_any", []) or []
        self.title_level_any = f.get("title_level_any", []) or []
        self.title_exclude = f.get("title_exclude", []) or []
        self.location_include = f.get("location_include", []) or []
        self.location_exclude = f.get("location_exclude", []) or []
        self.remote_only = bool(f.get("remote_only", False))
        # US filtering
        self.us_only = bool(f.get("us_only", False))
        # When us_only is on, keep postings whose location is ambiguous (e.g. a
        # bare "Remote") so we never drop a likely US remote role. Set false to
        # require an explicit US signal.
        self.keep_ambiguous_location = bool(f.get("keep_ambiguous_location", True))

    def match(self, job: Job) -> bool:
        title = job.title or ""
        loc = job.location or ""

        # Optional single include list (legacy).
        if self.title_include and not _any_word(self.title_include, title):
            return False
        # Must be a software/engineering role...
        if self.title_role_any and not _any_word(self.title_role_any, title):
            return False
        # ...AND carry an early-career signal.
        if self.title_level_any and not _any_word(self.title_level_any, title):
            return False
        # ...and none of the excluded ones (e.g. "Senior", "Staff", "Manager").
        if self.title_exclude and _any_word(self.title_exclude, title):
            return False

        # US-only filter (three-way: True keep, False drop, None depends on config)
        if self.us_only:
            verdict = is_usa(loc)
            if verdict is False:
                return False
            if verdict is None and not self.keep_ambiguous_location:
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
