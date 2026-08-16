#!/usr/bin/env python3
"""Read-only live verification. Writes redacted JSON. Never prints secrets."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from echo_runpod.client import RunPodClient, RunPodError
from echo_runpod.governor import idle_paid_resources
from echo_runpod.redaction import redact
from echo_runpod.secrets import SecretBroker, SecretError


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("live_verify.json")
    broker = SecretBroker()
    status = broker.status()
    payload = {
        "ok": False,
        "auth": {"source": status.source, "reference": status.reference, "present": status.present},
        "account_status": None,
        "pods": None,
        "gpu_catalog": None,
        "billing": None,
        "errors": [],
    }
    if not status.present:
        payload["errors"].append("RUNPOD_API_KEY not available via Vault or environment")
        out_path.write_text(json.dumps(redact(payload), indent=2), encoding="utf-8")
        return 3
    client = RunPodClient(broker)
    try:
        pods = client.list_pods()
        payload["pods"] = pods
        idle = idle_paid_resources(pods if isinstance(pods, list) else (pods or {}).get("pods") or [])
        payload["account_status"] = {
            "pod_count": len(pods) if isinstance(pods, list) else None,
            "idle_paid_resources": idle,
        }
    except (RunPodError, SecretError) as exc:
        payload["errors"].append(str(exc))
    try:
        payload["gpu_catalog"] = client.list_gpu_types()
    except (RunPodError, SecretError) as exc:
        payload["errors"].append(f"gpu: {exc}")
    try:
        payload["billing"] = client.billing()
    except (RunPodError, SecretError) as exc:
        payload["errors"].append(f"billing: {exc}")
    payload["ok"] = payload["pods"] is not None
    out_path.write_text(json.dumps(redact(payload), indent=2, default=str), encoding="utf-8")
    return 0 if payload["ok"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
