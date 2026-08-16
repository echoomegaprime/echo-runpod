"""Secret redaction for logs, receipts, exceptions, and tool responses."""

from __future__ import annotations

import re
from typing import Any

SECRET_ENV_NAMES = (
    "RUNPOD_API_KEY",
    "HF_TOKEN",
    "HUGGING_FACE_HUB_TOKEN",
    "VAULT_TOKEN",
    "ECHO_VAULT_TOKEN",
    "OAUTH_TOKEN",
    "ACCESS_TOKEN",
    "REGISTRY_PASSWORD",
    "GITHUB_TOKEN",
    "OPENAI_API_KEY",
    "XAI_API_KEY",
)

_BEARER_RE = re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._\-+/=]{8,})")
_KEY_ASSIGN_RE = re.compile(
    r"(?i)\b("
    + "|".join(re.escape(n) for n in SECRET_ENV_NAMES)
    + r")\b(\s*[:=]\s*)([^\s,;\"']+)"
)
_JSON_SECRET_RE = re.compile(
    r'(?i)("(?:'
    + "|".join(re.escape(n) for n in SECRET_ENV_NAMES)
    + r'|api[_-]?key|authorization|password|token|secret)"\s*:\s*")([^"]+)"'
)
_RP_KEY_RE = re.compile(r"\bRP_[A-Za-z0-9]{16,}\b")
_LONG_TOKEN_RE = re.compile(r"\b(?:sk-|r8_|hf_|ghp_|gho_|xai-)[A-Za-z0-9_\-]{12,}\b")


def redact_text(value: str) -> str:
    if not value:
        return value
    out = _BEARER_RE.sub(r"\1[REDACTED]", value)
    out = _KEY_ASSIGN_RE.sub(r"\1\2[REDACTED]", out)
    out = _JSON_SECRET_RE.sub(r'\1[REDACTED]"', out)
    out = _RP_KEY_RE.sub("[REDACTED]", out)
    out = _LONG_TOKEN_RE.sub("[REDACTED]", out)
    return out


def redact(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {
            str(k): "[REDACTED]"
            if str(k).upper() in SECRET_ENV_NAMES
            or str(k).lower()
            in {
                "api_key",
                "apikey",
                "authorization",
                "password",
                "token",
                "secret",
                "access_token",
                "refresh_token",
            }
            else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return type(value)(redact(v) for v in value)
    return value


def assert_no_secrets(payload: Any) -> None:
    text = payload if isinstance(payload, str) else repr(payload)
    lowered = text.lower()
    if "bearer " in lowered and "[redacted]" not in lowered:
        if re.search(r"bearer\s+[A-Za-z0-9._\-+/=]{12,}", text, re.I):
            raise AssertionError("unredacted bearer token")
    if re.search(r"\bRP_[A-Za-z0-9]{16,}\b", text):
        raise AssertionError("unredacted RUNPOD-shaped key")
