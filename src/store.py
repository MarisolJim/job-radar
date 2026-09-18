"""Persistent record of every job we've already seen.

GitHub Actions runs are stateless, so we persist this file and commit it back
to the repo after each run (the workflow does the commit). That's how we know
which postings are genuinely NEW on the next run.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Iterable

from models import Job


class SeenStore:
    def __init__(self, path: str):
        self.path = path
        self._jobs: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
            self._jobs = data.get("jobs", {})

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        payload = {"updated_at": datetime.now(timezone.utc).isoformat(), "jobs": self._jobs}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def is_new(self, job: Job) -> bool:
        return job.id not in self._jobs

    def add(self, job: Job) -> None:
        """Record a job. Preserves the original first_seen if already present."""
        if job.id in self._jobs:
            job.first_seen = self._jobs[job.id].get("first_seen", job.first_seen)
        self._jobs[job.id] = job.to_dict()

    def add_many(self, jobs: Iterable[Job]) -> list[Job]:
        """Add jobs, returning the ones that were new (not seen before)."""
        new_jobs: list[Job] = []
        for job in jobs:
            if self.is_new(job):
                new_jobs.append(job)
            self.add(job)
        return new_jobs

    def seen_within(self, hours: int) -> list[Job]:
        """Jobs first seen within the last `hours` (for the daily digest)."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        out: list[Job] = []
        for d in self._jobs.values():
            try:
                fs = datetime.fromisoformat(d["first_seen"])
            except (KeyError, ValueError):
                continue
            if fs.tzinfo is None:
                fs = fs.replace(tzinfo=timezone.utc)
            if fs >= cutoff:
                out.append(Job.from_dict(d))
        return out

    def prune(self, days: int = 90) -> None:
        """Drop very old records so the file doesn't grow forever."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        keep = {}
        for jid, d in self._jobs.items():
            try:
                fs = datetime.fromisoformat(d["first_seen"])
                if fs.tzinfo is None:
                    fs = fs.replace(tzinfo=timezone.utc)
            except (KeyError, ValueError):
                fs = datetime.now(timezone.utc)
            if fs >= cutoff:
                keep[jid] = d
        self._jobs = keep
