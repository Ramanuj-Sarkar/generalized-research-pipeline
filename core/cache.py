"""
Lightweight cache so re-running the pipeline for the same entity+connector
within a short window doesn't re-hit external APIs. Deliberately simple:
JSON files on disk, keyed by a hash of (connector name, entity, config).
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class FileCache:
    def __init__(self, cache_dir: str = ".cache", ttl_seconds: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds

    def _key(self, connector_name: str, entity: str, config: dict) -> str:
        raw = json.dumps({"c": connector_name, "e": entity, "cfg": config}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def get(self, connector_name: str, entity: str, config: dict) -> Any | None:
        path = self.cache_dir / f"{self._key(connector_name, entity, config)}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text())
        if time.time() - payload["cached_at"] > self.ttl_seconds:
            return None
        return payload["data"]

    def set(self, connector_name: str, entity: str, config: dict, data: Any) -> None:
        path = self.cache_dir / f"{self._key(connector_name, entity, config)}.json"
        path.write_text(json.dumps({"cached_at": time.time(), "data": data}, default=str))
