"""Shared HTTP helper and the source registry.

Each ATS module registers a fetcher under its key ("greenhouse", "lever",
"ashby"). `fetch_company` dispatches to the right one based on companies.yaml.
"""

from __future__ import annotations

from typing import Callable

import requests

from models import Job

# Be a polite, identifiable client. Some ATS endpoints reject empty UAs.
HEADERS = {
    "User-Agent": "job-radar/1.0 (+personal job tracker)",
    "Accept": "application/json",
}

TIMEOUT = 20

_REGISTRY: dict[str, Callable[[dict], list[Job]]] = {}


def register(ats: str):
    def deco(fn: Callable[[dict], list[Job]]):
        _REGISTRY[ats] = fn
        return fn

    return deco


def http_get_json(url: str, params: dict | None = None) -> dict | list:
    resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_company(company_cfg: dict) -> list[Job]:
    """Dispatch one company config entry to its ATS fetcher.

    company_cfg = {name, ats, slug, priority?}
    """
    ats = company_cfg.get("ats", "").lower()
    if ats not in _REGISTRY:
        raise ValueError(f"Unknown ATS '{ats}' for company '{company_cfg.get('name')}'")
    return _REGISTRY[ats](company_cfg)


# Import concrete sources so they register themselves.
from sources import greenhouse, lever, ashby  # noqa: E402,F401
