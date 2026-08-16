"""RunPod REST client. Official MCP is the preferred live backend; this wraps REST."""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from typing import Any, Mapping

from echo_runpod.redaction import redact
from echo_runpod.secrets import SecretBroker

REST_V1 = "https://rest.runpod.io/v1"
GRAPHQL = "https://api.runpod.io/graphql"


class RunPodError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status = status
        self.payload = redact(payload)


class RunPodClient:
    def __init__(self, broker: SecretBroker, opener=None):
        self.broker = broker
        self.opener = opener

    def _request(self, method: str, url: str, body: Mapping[str, Any] | None = None) -> Any:
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {
            **self.broker.authorization_header(),
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "echo-runpod/1.0.0",
        }
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            if self.opener:
                resp = self.opener(req)
                raw = resp.read() if hasattr(resp, "read") else resp
                return json.loads(raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw)
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                if not raw:
                    return {"ok": True, "status": resp.status}
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise RunPodError(f"RunPod HTTP {exc.code}", status=exc.code, payload=detail) from None
        except urllib.error.URLError as exc:
            raise RunPodError(f"RunPod connection failed: {exc.reason}") from None

    def list_pods(self) -> Any:
        return self._request("GET", f"{REST_V1}/pods")

    def get_pod(self, pod_id: str) -> Any:
        return self._request("GET", f"{REST_V1}/pods/{pod_id}")

    def list_gpu_types(self) -> Any:
        query = {
            "query": "query GpuTypes { gpuTypes { id displayName memoryInGb secureCloud communityCloud } }"
        }
        return self._request("POST", GRAPHQL, query)

    def billing(self) -> Any:
        return self._request("GET", f"{REST_V1}/billing/pods")


def idempotency_digest(action: str, request: Mapping[str, Any]) -> str:
    blob = json.dumps({"action": action, "request": request}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
