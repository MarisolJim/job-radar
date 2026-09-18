"""Core job record and normalization helpers.

Every source (Greenhouse, Lever, Ashby, a board scraper) converts its raw
payload into a `Job`. Downstream code only ever deals with `Job`, so adding a
new source never touches the store, filters, or notifier.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    # Identity / source
    source: str  # "greenhouse", "lever", "ashby", board name, ...
    company: str  # display name of the company/org
    title: str
    url: str  # the apply / posting URL

    # Optional metadata (best-effort per source)
    location: Optional[str] = None
    remote: Optional[bool] = None
    posted_at: Optional[str] = None  # ISO8601, when the SOURCE says it went live
    department: Optional[str] = None
    priority: int = 0  # copied from the company config; higher = alert faster

    # Filled in by us, not the source
    first_seen: str = field(default_factory=_now)

    @property
    def id(self) -> str:
        """Stable id used to decide 'have we seen this posting before?'.

        Keyed on source + company + url. If a company reposts the exact same
        role at a new URL we treat it as new (which is what we want for a
        'be first' tool).
        """
        raw = f"{self.source}|{self.company}|{self.url}".lower()
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["id"] = self.id
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Job":
        d = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**d)
