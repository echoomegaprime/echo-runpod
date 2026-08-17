"""RunPod REST client. Official MCP is the preferred live backend; this wraps REST."""

from __future__ import annotations

import hashlib
import json
import socket
import urllib.error
import urllib.request
from typing import Any, Callable, Mapping

from echo_runpod.redaction import redact
from echo_runpod.secrets import SecretBroker

REST_V1 = "https://rest.runpod.io/v1"
GRAPHQL = "https://api.runpod.io/graphql"

Transport = Callable[[str, str, Mapping[str, Any] | None], Any]


class RunPodError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status = status
        self.payload = redact(payload)


class RunPodClient:
    def __init__(self, broker: SecretBroker, opener=None, transport: Transport | None = None):
        self.broker = broker
        self.opener = opener
        self.transport = transport

    def _request(self, method: str, url: str, body: Mapping[str, Any] | None = None) -> Any:
        if self.transport:
            return self.transport(method, url, body)
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {
            **self.broker.authorization_header(),
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "echo-runpod/1.1.1",
        }
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            if self.opener:
                resp = self.opener(req)
                raw = resp.read() if hasattr(resp, "read") else resp
                return _decode_json(raw)
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                if not raw:
                    return {"ok": True, "status": resp.status}
                return _decode_json(raw)
        except TimeoutError as exc:
            raise RunPodError(f"RunPod timeout: {exc}", status=None) from None
        except socket.timeout as exc:
            raise RunPodError(f"RunPod timeout: {exc}", status=None) from None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise RunPodError(f"RunPod HTTP {exc.code}", status=exc.code, payload=detail) from None
        except urllib.error.URLError as exc:
            reason = str(getattr(exc, "reason", exc))
            if "timed out" in reason.lower() or "timeout" in reason.lower():
                raise RunPodError(f"RunPod timeout: {reason}", status=None) from None
            raise RunPodError(f"RunPod connection failed: {reason}") from None

    def list_pods(self) -> Any:
        return self._request("GET", f"{REST_V1}/pods")

    def get_pod(self, pod_id: str) -> Any:
        return self._request("GET", f"{REST_V1}/pods/{pod_id}")

    def create_pod(self, body: Mapping[str, Any]) -> Any:
        return self._request("POST", f"{REST_V1}/pods", body)

    def start_pod(self, pod_id: str) -> Any:
        return self._request("POST", f"{REST_V1}/pods/{pod_id}/start")

    def stop_pod(self, pod_id: str) -> Any:
        return self._request("POST", f"{REST_V1}/pods/{pod_id}/stop")

    def restart_pod(self, pod_id: str) -> Any:
        return self._request("POST", f"{REST_V1}/pods/{pod_id}/reset")

    def terminate_pod(self, pod_id: str) -> Any:
        return self._request("DELETE", f"{REST_V1}/pods/{pod_id}")

    def update_pod(self, pod_id: str, body: Mapping[str, Any]) -> Any:
        return self._request("PATCH", f"{REST_V1}/pods/{pod_id}", body)

    def pod_logs(self, pod_id: str, lines: int = 200) -> Any:
        # Official MCP stream-pod-logs; REST exposes a logs resource when available.
        try:
            return self._request("GET", f"{REST_V1}/pods/{pod_id}/logs?limit={int(lines)}")
        except RunPodError as exc:
            if exc.status in {404, 405}:
                pod = self.get_pod(pod_id)
                return {"source": "pod_runtime", "pod": pod, "logs": None, "note": "REST logs path not available"}
            raise

    def list_gpu_types(self) -> Any:
        query = {
            "query": (
                "query GpuTypes { gpuTypes { id displayName memoryInGb secureCloud communityCloud "
                "securePrice communityPrice lowestPrice(input: { gpuCount: 1 }) { "
                "minimumBidPrice uninterruptablePrice stockStatus } } }"
            )
        }
        return self._request("POST", GRAPHQL, query)

    def list_volumes(self) -> Any:
        return self._request("GET", f"{REST_V1}/networkvolumes")

    def get_volume(self, volume_id: str) -> Any:
        return self._request("GET", f"{REST_V1}/networkvolumes/{volume_id}")

    def list_endpoints(self) -> Any:
        return self._request("GET", f"{REST_V1}/endpoints")

    def get_endpoint(self, endpoint_id: str) -> Any:
        return self._request("GET", f"{REST_V1}/endpoints/{endpoint_id}")

    def list_jobs(self, endpoint_id: str | None) -> Any:
        if not endpoint_id:
            return {"note": "endpoint_id required for official job listing", "jobs": []}
        return self._request("GET", f"{REST_V1}/endpoints/{endpoint_id}/jobs")

    def get_job(self, endpoint_id: str, job_id: str) -> Any:
        if endpoint_id:
            return self._request("GET", f"{REST_V1}/endpoints/{endpoint_id}/jobs/{job_id}")
        return self._request("GET", f"{REST_V1}/jobs/{job_id}")

    def cancel_job(self, endpoint_id: str, job_id: str) -> Any:
        if endpoint_id:
            return self._request("POST", f"{REST_V1}/endpoints/{endpoint_id}/jobs/{job_id}/cancel")
        return self._request("POST", f"{REST_V1}/jobs/{job_id}/cancel")

    def billing(self) -> Any:
        return self._request("GET", f"{REST_V1}/billing/pods")

    def account(self) -> Any:
        query = {"query": "query Myself { myself { id clientBalance spendLimit } }"}
        return self._request("POST", GRAPHQL, query)


def _decode_json(raw: Any) -> Any:
    if raw is None:
        return {}
    if isinstance(raw, (bytes, bytearray)):
        text = raw.decode("utf-8")
    else:
        text = str(raw)
    if not text.strip():
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RunPodError(f"malformed RunPod response: {exc}", payload=text[:500]) from None


def normalize_pods(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    if isinstance(payload, Mapping):
        for key in ("pods", "data", "items"):
            val = payload.get(key)
            if isinstance(val, list):
                return [p for p in val if isinstance(p, dict)]
            if isinstance(val, Mapping) and isinstance(val.get("pods"), list):
                return [p for p in val["pods"] if isinstance(p, dict)]
        if "id" in payload:
            return [dict(payload)]
    raise RunPodError("malformed pod list")


def parse_gpu_catalog(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    rows: Any = payload
    if isinstance(payload, Mapping):
        data = payload.get("data")
        if isinstance(data, Mapping) and "gpuTypes" in data:
            rows = data["gpuTypes"]
        elif "gpuTypes" in payload:
            rows = payload["gpuTypes"]
        elif "gpus" in payload:
            rows = payload["gpus"]
    if not isinstance(rows, list):
        raise RunPodError("malformed GPU catalog")
    out: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, Mapping):
            continue
        lowest = item.get("lowestPrice")
        lowest_price = None
        stock = None
        if isinstance(lowest, Mapping):
            lowest_price = lowest.get("uninterruptablePrice") or lowest.get("minimumBidPrice")
            stock = lowest.get("stockStatus")
        elif isinstance(lowest, (int, float)):
            lowest_price = lowest
        out.append(
            {
                "id": item.get("id"),
                "displayName": item.get("displayName") or item.get("id"),
                "memoryInGb": item.get("memoryInGb"),
                "secureCloud": item.get("secureCloud"),
                "communityCloud": item.get("communityCloud"),
                "securePrice": _as_float(item.get("securePrice")),
                "communityPrice": _as_float(item.get("communityPrice")),
                "lowestPrice": _as_float(lowest_price),
                "stockStatus": stock,
            }
        )
    return out


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def idempotency_digest(action: str, request: Mapping[str, Any]) -> str:
    blob = json.dumps({"action": action, "request": request}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
