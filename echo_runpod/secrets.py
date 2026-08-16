"""Resolve RUNPOD_API_KEY at runtime. Never return the raw key to callers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

VAULT_REF = "vault://runpod/api-key"
ENV_CANDIDATES = ("RUNPOD_API_KEY",)


class SecretError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResolvedSecret:
    source: str
    reference: str
    present: bool


def _looks_like_key(value: str) -> bool:
    return bool(value) and len(value.strip()) >= 16


class SecretBroker:
    """In-process resolver. The key never leaves this object as a logged value."""

    def __init__(self, env: dict[str, str] | None = None, vault_get: Callable[[str], str | None] | None = None):
        self._env = env if env is not None else dict(os.environ)
        self._vault_get = vault_get
        self._cached: str | None = None
        self._source = "unresolved"

    def status(self) -> ResolvedSecret:
        try:
            self.resolve()
            return ResolvedSecret(self._source, VAULT_REF, True)
        except SecretError:
            return ResolvedSecret("missing", VAULT_REF, False)

    def resolve(self) -> str:
        if self._cached:
            return self._cached
        if self._vault_get:
            value = self._vault_get(VAULT_REF)
            if value and _looks_like_key(value):
                self._cached = value.strip()
                self._source = "vault"
                return self._cached
        for name in ENV_CANDIDATES:
            value = self._env.get(name)
            if value and _looks_like_key(value):
                self._cached = value.strip()
                self._source = f"env:{name}"
                return self._cached
        raise SecretError("RUNPOD_API_KEY not available via Vault or environment")

    def authorization_header(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.resolve()}"}

    def forget(self) -> None:
        self._cached = None
        self._source = "unresolved"
