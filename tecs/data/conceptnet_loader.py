# tecs/data/conceptnet_loader.py
"""Thin ConceptNet loader — fetches from API or reads from local cache JSON.
Falls back to synthetic data when the actual data is unavailable.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONCEPTNET_API = "https://api.conceptnet.io"


class ConceptNetLoader:
    """Load concept relations from ConceptNet (API or local cache).

    When neither the API nor a local cache is available the loader raises
    ``ConceptNetUnavailable`` so callers can fall back gracefully.
    """

    class ConceptNetUnavailable(RuntimeError):
        """Raised when ConceptNet data cannot be obtained."""

    def __init__(self, cache_dir: str = "data/"):
        self.cache_dir = Path(cache_dir)
        self._cache_file = self.cache_dir / "conceptnet_cache.json"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_concept_relations(self, n: int = 100) -> list[dict]:
        """Return up to *n* concept triples from cache or API."""
        data = self._load_cache()
        if data:
            return data[:n]
        try:
            data = self._fetch_from_api(n)
            self._save_cache(data)
            return data[:n]
        except Exception as exc:
            raise self.ConceptNetUnavailable(
                f"ConceptNet unavailable (cache miss, API error: {exc})"
            ) from exc

    def download(self, n: int = 1000) -> None:
        """Download *n* concept relations from the ConceptNet API and cache them."""
        data = self._fetch_from_api(n)
        self._save_cache(data)
        logger.info("Cached %d ConceptNet relations to %s", len(data), self._cache_file)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_cache(self) -> list[dict]:
        if not self._cache_file.exists():
            return []
        try:
            with self._cache_file.open() as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load ConceptNet cache: %s", exc)
            return []

    def _save_cache(self, data: list[dict]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with self._cache_file.open("w") as f:
            json.dump(data, f)

    def _fetch_from_api(self, n: int) -> list[dict]:
        """Fetch concept edges from the ConceptNet REST API."""
        import requests  # lazy import so missing package gives a clear error

        url = f"{CONCEPTNET_API}/query"
        params = {"limit": min(n, 1000), "offset": 0}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        payload: dict[str, Any] = resp.json()

        triples: list[dict] = []
        for edge in payload.get("edges", []):
            try:
                head = edge["start"]["label"]
                tail = edge["end"]["label"]
                relation = edge["rel"]["label"]
                triples.append({"head": head, "relation": relation, "tail": tail})
            except (KeyError, TypeError):
                continue
        return triples
