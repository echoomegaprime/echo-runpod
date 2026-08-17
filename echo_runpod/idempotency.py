"""Durable idempotency for spend/mutation actions.

Binds idempotency_key to a digest of (action + normalized request).
Same key + same request replays the stored receipt.
Same key + different request raises IdempotencyConflict.

In-memory by default (tests). Optional JSON file for a process-local durable store.
This is the smallest store consistent with the pack; it does not invent a second
Nexus persistence plane.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from echo_runpod.client import idempotency_digest


class IdempotencyConflict(ValueError):
    error_type = "idempotency_conflict"


@dataclass(frozen=True)
class IdempotencyRecord:
    key: str
    action: str
    digest: str
    result: dict[str, Any]


class IdempotencyStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self._lock = threading.Lock()
        self._records: dict[str, IdempotencyRecord] = {}
        if self.path and self.path.is_file():
            self._load()

    def _load(self) -> None:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return
        for key, item in raw.items():
            if not isinstance(item, dict):
                continue
            self._records[str(key)] = IdempotencyRecord(
                key=str(key),
                action=str(item.get("action") or ""),
                digest=str(item.get("digest") or ""),
                result=dict(item.get("result") or {}),
            )

    def _persist(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            rec.key: {"action": rec.action, "digest": rec.digest, "result": rec.result}
            for rec in self._records.values()
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)

    def normalize(self, action: str, request: Mapping[str, Any]) -> dict[str, Any]:
        skip = {"confirm", "approved_manifest", "full_lane", "idempotency_key"}
        return {k: request[k] for k in sorted(request) if k not in skip}

    def digest_for(self, action: str, request: Mapping[str, Any]) -> str:
        return idempotency_digest(action, self.normalize(action, request))

    def recall(self, key: str, action: str, request: Mapping[str, Any]) -> dict[str, Any] | None:
        digest = self.digest_for(action, request)
        with self._lock:
            rec = self._records.get(key)
            if rec is None:
                return None
            if rec.digest != digest or rec.action != action:
                raise IdempotencyConflict(
                    f"idempotency_conflict: key {key!r} is bound to a different request"
                )
            return dict(rec.result)

    def record(self, key: str, action: str, request: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
        digest = self.digest_for(action, request)
        stored = dict(result)
        with self._lock:
            existing = self._records.get(key)
            if existing is not None:
                if existing.digest != digest or existing.action != action:
                    raise IdempotencyConflict(
                        f"idempotency_conflict: key {key!r} is bound to a different request"
                    )
                return dict(existing.result)
            self._records[key] = IdempotencyRecord(key=key, action=action, digest=digest, result=stored)
            self._persist()
        return stored

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            if self.path and self.path.is_file():
                self.path.unlink()


_STORE: IdempotencyStore | None = None


def get_store() -> IdempotencyStore:
    global _STORE
    if _STORE is None:
        _STORE = IdempotencyStore()
    return _STORE


def set_store(store: IdempotencyStore | None) -> None:
    global _STORE
    _STORE = store
