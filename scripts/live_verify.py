#!/usr/bin/env python3
"""Read-only live verification. Writes redacted JSON. Never prints secrets."""
from __future__ import annotations

import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from echo_runpod.client import RunPodClient, RunPodError, normalize_pods, parse_gpu_catalog
from echo_runpod.governor import idle_paid_resources
from echo_runpod.mcp import RESOURCE_PATH, RESOURCE_URL, resource_catalog
from echo_runpod.redaction import redact
from echo_runpod.secrets import SecretBroker, SecretError

MCP_BASE = RESOURCE_URL
WELL_KNOWN = f"https://mcp.echo-op.com/.well-known/oauth-protected-resource{RESOURCE_PATH}"


def _http_json(url: str, timeout: int = 12) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "echo-runpod-live-verify/1.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
            raw = resp.read().decode("utf-8", "replace")
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                data = {"raw": raw[:500], "parse": "non_json"}
            return {"ok": 200 <= resp.status < 300, "status": resp.status, "data": data}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:500]
        return {"ok": False, "status": exc.code, "data": {"error": body}}
    except Exception as exc:  # noqa: BLE001 — live probe must not crash
        return {"ok": False, "status": None, "data": {"error": str(exc)}}


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("live_verify.json")
    broker = SecretBroker()
    status = broker.status()
    catalog = resource_catalog()
    payload = {
        "ok": False,
        "auth": {"source": status.source, "reference": status.reference, "present": status.present},
        "account_status": None,
        "pods": None,
        "gpu_catalog": None,
        "billing": None,
        "mcp": {
            "resource": catalog,
            "endpoint": None,
            "well_known": None,
            "health": None,
            "tools": None,
        },
        "errors": [],
    }
    payload["mcp"]["endpoint"] = _http_json(MCP_BASE)
    payload["mcp"]["well_known"] = _http_json(WELL_KNOWN)
    payload["mcp"]["health"] = _http_json(f"{MCP_BASE}/health")
    if not status.present:
        payload["errors"].append("RUNPOD_API_KEY not available via Vault or environment")
    else:
        client = RunPodClient(broker)
        try:
            pods = client.list_pods()
            payload["pods"] = pods
            norm = normalize_pods(pods)
            idle = idle_paid_resources(norm)
            payload["account_status"] = {
                "pod_count": len(norm),
                "idle_paid_resources": idle,
            }
        except (RunPodError, SecretError) as exc:
            payload["errors"].append(str(exc))
        try:
            payload["gpu_catalog"] = parse_gpu_catalog(client.list_gpu_types())
        except (RunPodError, SecretError) as exc:
            payload["errors"].append(f"gpu: {exc}")
        try:
            payload["billing"] = client.billing()
        except (RunPodError, SecretError) as exc:
            payload["errors"].append(f"billing: {exc}")
    mcp_ok = bool(payload["mcp"]["endpoint"] and payload["mcp"]["endpoint"].get("ok"))
    payload["ok"] = payload["pods"] is not None and mcp_ok
    if not mcp_ok:
        payload["errors"].append("MCP endpoint not healthy")
    out_path.write_text(json.dumps(redact(payload), indent=2, default=str), encoding="utf-8")
    return 0 if payload["ok"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
