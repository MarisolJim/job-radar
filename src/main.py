"""Orchestrator. Two modes:

    python src/main.py poll     # fetch everything, alert on NEW priority jobs
    python src/main.py digest   # email a summary of the last 24h

`poll` runs often (e.g. every 30 min) so you catch postings early.
`digest` runs once a day.

Both read config from the YAML files in the project root and the seen-store in
data/seen.json (committed back by the workflow so state survives between runs).
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback

import yaml

from filters import JobFilter
from models import Job
from store import SeenStore
import notify
from sources.base import fetch_company

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE_PATH = os.path.join(ROOT, "data", "seen.json")


def _load_yaml(name: str) -> dict:
    path = os.path.join(ROOT, name)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def collect_jobs() -> list[Job]:
    """Poll every configured company ATS. One bad company never kills the run."""
    companies = _load_yaml("companies.yaml").get("companies", []) or []
    all_jobs: list[Job] = []
    for cfg in companies:
        name = cfg.get("name", cfg.get("slug", "?"))
        try:
            jobs = fetch_company(cfg)
            all_jobs.extend(jobs)
            print(f"  [ok] {name}: {len(jobs)} postings")
        except Exception as e:  # noqa: BLE001 - keep going past a single failure
            print(f"  [!!] {name}: {e}", file=sys.stderr)
    return all_jobs


def run_poll() -> int:
    filters_cfg = _load_yaml("filters.yaml")
    jf = JobFilter(filters_cfg)
    store = SeenStore(STORE_PATH)

    print("Polling company ATS feeds...")
    jobs = collect_jobs()
    matched = jf.apply(jobs)
    print(f"{len(jobs)} total postings, {len(matched)} match your filters.")

    new_jobs = store.add_many(matched)
    print(f"{len(new_jobs)} are NEW since last run.")

    # Instant alert only for high-priority companies (priority >= 2 in config),
    # so you're not pinged for every single new posting.
    alert = [j for j in new_jobs if j.priority >= 2]
    if alert:
        try:
            notify.send_instant_alert(alert)
            print(f"Sent instant alert for {len(alert)} priority job(s).")
        except Exception as e:  # noqa: BLE001
            print(f"[!!] alert email failed: {e}", file=sys.stderr)

    store.prune(days=90)
    store.save()
    return 0


def run_digest(hours: int = 24) -> int:
    store = SeenStore(STORE_PATH)
    recent = store.seen_within(hours)
    print(f"{len(recent)} jobs first seen in the last {hours}h.")
    try:
        notify.send_digest(recent, hours=hours)
        print("Digest sent.")
    except Exception as e:  # noqa: BLE001
        print(f"[!!] digest email failed: {e}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="job-radar")
    parser.add_argument("mode", choices=["poll", "digest"])
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()
    try:
        if args.mode == "poll":
            return run_poll()
        return run_digest(args.hours)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
