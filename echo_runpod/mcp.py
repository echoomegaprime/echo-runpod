"""Echo RunPod MCP surface.

Canonical tool/policy source for ChatGPT, Grok, Codex, and Echo agents.
Thin runtime entry: Echo Nexus registers /oauth-mcp-runpod-v1 against this catalog.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from echo_runpod.client import RunPodClient, RunPodError, idempotency_digest, normalize_pods, parse_gpu_catalog
from echo_runpod.governor import check_cost, idle_paid_resources
from echo_runpod.manifests import ManifestError, validate_manifest
from echo_runpod.policy import (
    APPROVAL_ACTIONS,
    DESTRUCTIVE_ACTIONS,
    READ_ACTIONS,
    annotations_for,
    evaluate_action,
)
from echo_runpod.redaction import assert_no_secrets, redact
from echo_runpod.secrets import SecretBroker, SecretError

RESOURCE_ID = "oauth-mcp-runpod-v1"
RESOURCE_PATH = "/oauth-mcp-runpod-v1"
RESOURCE_URL = "https://mcp.echo-op.com/oauth-mcp-runpod-v1"
SERVICE_NAME = "echo-oauth-mcp-runpod-v1"
PROTOCOL_VERSION = "2025-03-26"

SCOPE_READ = "echo.runpod.read"
SCOPE_PREPARE = "echo.runpod.prepare"
SCOPE_CONTROL = "echo.runpod.control"
SCOPE_SPEND = "echo.runpod.spend"
ALL_SCOPES = (SCOPE_READ, SCOPE_PREPARE, SCOPE_CONTROL, SCOPE_SPEND)

# Never request echo.write.

PREPARE_ACTIONS = frozenset({"runpod_prepare_training", "runpod_validate_manifest"})
CONTROL_ACTIONS = frozenset(
    {
        "runpod_start_pod",
        "runpod_stop_pod",
        "runpod_restart_pod",
        "runpod_terminate_pod",
        "runpod_cancel_job",
    }
)
SPEND_ACTIONS = frozenset(
    {
        "runpod_create_pod",
        "runpod_resize_pod",
        "runpod_change_gpu",
        "runpod_attach_volume",
        "runpod_launch_training",
        "runpod_resume_training",
    }
)


def _prop(typ: str, description: str, **extra: Any) -> dict[str, Any]:
    out = {"type": typ, "description": description}
    out.update(extra)
    return out


def _tool(
    name: str,
    description: str,
    scopes: tuple[str, ...],
    props: dict[str, Any] | None = None,
    required: list[str] | None = None,
    mutating: bool = False,
) -> dict[str, Any]:
    properties = dict(props or {})
    req = list(required or [])
    if mutating and "confirm" not in properties:
        properties["confirm"] = _prop("string", "Must be EXECUTE for consequential mutations")
        if "confirm" not in req:
            req.append("confirm")
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if req:
        schema["required"] = req
    return {
        "name": name,
        "description": description,
        "scopes": list(scopes),
        "mutating": mutating,
        "inputSchema": schema,
        "annotations": annotations_for(name),
    }


TOOLS: list[dict[str, Any]] = [
    _tool("runpod_status", "Account + fleet snapshot (read-only)", (SCOPE_READ,)),
    _tool("runpod_account", "RunPod account/balance if the API exposes it", (SCOPE_READ,)),
    _tool("runpod_list_pods", "List pods in the Commander RunPod account", (SCOPE_READ,)),
    _tool(
        "runpod_get_pod",
        "Pod details",
        (SCOPE_READ,),
        {"pod_id": _prop("string", "RunPod pod id")},
        ["pod_id"],
    ),
    _tool(
        "runpod_pod_status",
        "Normalized pod desired/current status",
        (SCOPE_READ,),
        {"pod_id": _prop("string", "RunPod pod id")},
        ["pod_id"],
    ),
    _tool(
        "runpod_stream_pod_logs",
        "Fetch available pod logs (capped; official stream when REST exposes it)",
        (SCOPE_READ,),
        {"pod_id": _prop("string", "RunPod pod id"), "lines": _prop("integer", "Max lines")},
        ["pod_id"],
    ),
    _tool("runpod_list_gpu_types", "GPU catalog", (SCOPE_READ,)),
    _tool("runpod_gpu_availability", "GPU stock / cloud availability", (SCOPE_READ,)),
    _tool("runpod_gpu_pricing", "Live GPU pricing (never hard-coded as truth)", (SCOPE_READ,)),
    _tool("runpod_list_endpoints", "Serverless endpoints", (SCOPE_READ,)),
    _tool(
        "runpod_get_endpoint",
        "Serverless endpoint details",
        (SCOPE_READ,),
        {"endpoint_id": _prop("string", "Endpoint id")},
        ["endpoint_id"],
    ),
    _tool(
        "runpod_endpoint_health",
        "Serverless endpoint health",
        (SCOPE_READ,),
        {"endpoint_id": _prop("string", "Endpoint id")},
        ["endpoint_id"],
    ),
    _tool(
        "runpod_list_jobs",
        "Jobs for an endpoint when the official API supports it",
        (SCOPE_READ,),
        {"endpoint_id": _prop("string", "Endpoint id")},
    ),
    _tool(
        "runpod_get_job",
        "Job status",
        (SCOPE_READ,),
        {"endpoint_id": _prop("string", "Endpoint id"), "job_id": _prop("string", "Job id")},
        ["job_id"],
    ),
    _tool(
        "runpod_stream_job",
        "Job output if the official API supports it",
        (SCOPE_READ,),
        {"endpoint_id": _prop("string", "Endpoint id"), "job_id": _prop("string", "Job id")},
        ["job_id"],
    ),
    _tool("runpod_list_volumes", "Network volumes / storage", (SCOPE_READ,)),
    _tool(
        "runpod_get_volume",
        "Volume details",
        (SCOPE_READ,),
        {"volume_id": _prop("string", "Network volume id")},
        ["volume_id"],
    ),
    _tool(
        "runpod_network_info",
        "Ports / proxy / SSH fields from a pod",
        (SCOPE_READ,),
        {"pod_id": _prop("string", "RunPod pod id")},
        ["pod_id"],
    ),
    _tool("runpod_billing", "Billing / accrued spend when available", (SCOPE_READ,)),
    _tool(
        "runpod_cost_estimate",
        "Estimate cost from live GPU pricing",
        (SCOPE_READ, SCOPE_PREPARE),
        {
            "gpu_type": _prop("string", "GPU display name or id"),
            "hours": _prop("number", "Hours to estimate"),
            "gpu_count": _prop("integer", "GPU count"),
            "max_hourly_rate": _prop("number", "Ceiling"),
            "max_total_budget": _prop("number", "Budget ceiling"),
        },
        ["gpu_type", "hours"],
    ),
    _tool("runpod_burn_rate", "Current burn from running pods + live prices", (SCOPE_READ,)),
    _tool(
        "runpod_training_status",
        "Training workload status (pod + checkpoints)",
        (SCOPE_READ,),
        {"pod_id": _prop("string", "Trainer pod id")},
    ),
    _tool(
        "runpod_training_checkpoints",
        "Checkpoint / artifact paths if exposed",
        (SCOPE_READ,),
        {"pod_id": _prop("string", "Trainer pod id"), "volume_id": _prop("string", "Volume id")},
    ),
    _tool("runpod_live_verify", "Read-only live verification receipt", (SCOPE_READ,)),
    _tool(
        "runpod_prepare_training",
        "Validate a training manifest. Does not spend.",
        (SCOPE_PREPARE, SCOPE_READ),
        {"manifest": _prop("object", "Training manifest object")},
        ["manifest"],
    ),
    _tool(
        "runpod_validate_manifest",
        "Alias of prepare — validate only",
        (SCOPE_PREPARE, SCOPE_READ),
        {"manifest": _prop("object", "Training manifest object")},
        ["manifest"],
    ),
    _tool(
        "runpod_create_pod",
        "Create a pod (approval-gated, confirm=EXECUTE)",
        (SCOPE_SPEND,),
        {
            "name": _prop("string", "Pod name"),
            "gpu_type": _prop("string", "GPU type id"),
            "gpu_count": _prop("integer", "GPU count"),
            "image": _prop("string", "Container image"),
            "workload_id": _prop("string", "Isolation workload id"),
        },
        ["gpu_type"],
        True,
    ),
    _tool(
        "runpod_start_pod",
        "Start an existing pod (confirm=EXECUTE)",
        (SCOPE_CONTROL,),
        {"pod_id": _prop("string", "Pod id")},
        ["pod_id"],
        True,
    ),
    _tool(
        "runpod_stop_pod",
        "Stop a pod (confirm=EXECUTE)",
        (SCOPE_CONTROL,),
        {"pod_id": _prop("string", "Pod id")},
        ["pod_id"],
        True,
    ),
    _tool(
        "runpod_restart_pod",
        "Restart / reset a pod (confirm=EXECUTE)",
        (SCOPE_CONTROL,),
        {"pod_id": _prop("string", "Pod id")},
        ["pod_id"],
        True,
    ),
    _tool(
        "runpod_terminate_pod",
        "Delete/terminate a pod (destructive, confirm=EXECUTE)",
        (SCOPE_CONTROL,),
        {"pod_id": _prop("string", "Pod id")},
        ["pod_id"],
        True,
    ),
    _tool(
        "runpod_resize_pod",
        "Resize / update a pod if RunPod permits (confirm=EXECUTE)",
        (SCOPE_SPEND,),
        {"pod_id": _prop("string", "Pod id"), "gpu_type": _prop("string", "New GPU type")},
        ["pod_id"],
        True,
    ),
    _tool(
        "runpod_change_gpu",
        "Change GPU class (confirm=EXECUTE)",
        (SCOPE_SPEND,),
        {"pod_id": _prop("string", "Pod id"), "gpu_type": _prop("string", "New GPU type")},
        ["pod_id", "gpu_type"],
        True,
    ),
    _tool(
        "runpod_attach_volume",
        "Attach or change storage where supported (confirm=EXECUTE)",
        (SCOPE_SPEND,),
        {"pod_id": _prop("string", "Pod id"), "volume_id": _prop("string", "Volume id")},
        ["pod_id", "volume_id"],
        True,
    ),
    _tool(
        "runpod_launch_training",
        "Execute a prepared training manifest (confirm=EXECUTE)",
        (SCOPE_SPEND,),
        {
            "manifest": _prop("object", "Approved training manifest"),
            "approved_manifest": _prop("object", "Same manifest after Commander approval"),
        },
        ["manifest"],
        True,
    ),
    _tool(
        "runpod_resume_training",
        "Resume a training pod (confirm=EXECUTE)",
        (SCOPE_SPEND,),
        {"pod_id": _prop("string", "Pod id")},
        ["pod_id"],
        True,
    ),
    _tool(
        "runpod_cancel_job",
        "Cancel a serverless job if the official API supports it (confirm=EXECUTE)",
        (SCOPE_CONTROL,),
        {"endpoint_id": _prop("string", "Endpoint id"), "job_id": _prop("string", "Job id")},
        ["job_id"],
        True,
    ),
]

TOOL_INDEX = {t["name"]: t for t in TOOLS}


def resource_catalog() -> dict[str, Any]:
    return {
        "id": RESOURCE_ID,
        "path": RESOURCE_PATH,
        "name": "Echo RunPod MCP v1",
        "canonical": RESOURCE_URL,
        "service": SERVICE_NAME,
        "purpose": "Governed RunPod control plane for Echo Omega Prime",
        "scopes": list(ALL_SCOPES),
        "default_scopes": list(ALL_SCOPES),
        "scope_descriptions": {
            SCOPE_READ: "Inspect pods, GPUs, pricing, billing, storage, logs, jobs",
            SCOPE_PREPARE: "Validate training manifests and cost estimates (no spend)",
            SCOPE_CONTROL: "Start/stop/restart/terminate/cancel with confirm=EXECUTE",
            SCOPE_SPEND: "Create/resize/launch paid resources with confirm=EXECUTE",
        },
        "tools": [t["name"] for t in TOOLS],
        "oauth_never": ["echo.write"],
        "secret_ref": "vault://runpod/api-key",
        "secret_env_fallback": "RUNPOD_API_KEY",
        "cloudflare_route": RESOURCE_PATH,
        "chatgpt_description": (
            "Governed RunPod control plane for Echo Omega Prime. Inspect pods, GPUs, "
            "pricing, billing, storage, logs, and training jobs; prepare and execute "
            "approval-gated RunPod operations through Echo Nexus."
        ),
    }


def tools_list_payload(scopes: list[str] | None) -> list[dict[str, Any]]:
    granted = set(scopes or ALL_SCOPES)
    grant_all = not granted or granted.intersection(ALL_SCOPES)
    out = []
    for tool in TOOLS:
        if grant_all or set(tool["scopes"]).intersection(granted):
            out.append(
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "inputSchema": tool["inputSchema"],
                    "annotations": tool["annotations"],
                }
            )
    return out


def chatgpt_tool_schemas() -> list[dict[str, Any]]:
    """Schemas ChatGPT MCP discovery expects."""
    return tools_list_payload(list(ALL_SCOPES))


def required_scopes_for(name: str) -> list[str]:
    tool = TOOL_INDEX.get(name)
    return list(tool["scopes"]) if tool else []


def scope_allows(name: str, scopes: list[str] | None) -> bool:
    need = required_scopes_for(name)
    if not need:
        return False
    granted = set(scopes or [])
    return bool(granted.intersection(need))


def _error(code: str, message: str, status: int = 400) -> dict[str, Any]:
    return {
        "ok": False,
        "error": code,
        "error_type": code,
        "message": message,
        "status": status,
    }


def handle_initialize() -> dict[str, Any]:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": SERVICE_NAME, "version": "1.1.0"},
    }


def handle_rpc(
    message: Mapping[str, Any],
    *,
    authenticated: bool,
    scopes: list[str] | None = None,
    client: RunPodClient | None = None,
    transport: Callable[[str, str, Mapping[str, Any] | None], Any] | None = None,
) -> dict[str, Any]:
    """JSON-RPC MCP handler. Never includes secrets in the returned payload."""
    rpc_id = message.get("id")
    method = str(message.get("method") or "")
    params = message.get("params") if isinstance(message.get("params"), Mapping) else {}

    def ok(result: Any) -> dict[str, Any]:
        payload = {"jsonrpc": "2.0", "id": rpc_id, "result": redact(result)}
        assert_no_secrets(payload)
        return payload

    def fail(err: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "isError": True,
                "content": [{"type": "text", "text": err["error"]}],
                "structuredContent": redact(err),
            },
        }
        assert_no_secrets(payload)
        return payload

    if not authenticated:
        return fail(_error("unauthenticated", "OAuth bearer required", 401))

    if method == "initialize":
        return ok(handle_initialize())
    if method in {"tools/list", "tools.list"}:
        return ok({"tools": tools_list_payload(scopes), "scopes_granted": list(scopes or ALL_SCOPES)})
    if method == "ping":
        return ok({})
    if method not in {"tools/call", "tools.call"}:
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    name = str(params.get("name") or "")
    args = params.get("arguments") if isinstance(params.get("arguments"), Mapping) else {}
    out = call_tool(name, dict(args), scopes=scopes, client=client, transport=transport)
    if not out.get("ok"):
        return fail(out)
    return ok(out)


def call_tool(
    name: str,
    args: dict[str, Any],
    *,
    scopes: list[str] | None,
    client: RunPodClient | None = None,
    transport: Callable[[str, str, Mapping[str, Any] | None], Any] | None = None,
) -> dict[str, Any]:
    if name not in TOOL_INDEX:
        return _error("unknown_tool", f"unknown_tool:{name}", 404)
    if not scope_allows(name, scopes):
        return _error("insufficient_scope", f"{name} requires {required_scopes_for(name)}", 403)

    confirm = args.get("confirm")
    decision = evaluate_action(
        name if name != "runpod_validate_manifest" else "runpod_prepare_training",
        confirm=str(confirm) if confirm is not None else None,
        approved_manifest=args.get("approved_manifest") if isinstance(args.get("approved_manifest"), Mapping) else None,
        full_lane=args.get("full_lane") if isinstance(args.get("full_lane"), Mapping) else None,
        request=args,
    )
    if name in APPROVAL_ACTIONS or name in DESTRUCTIVE_ACTIONS or TOOL_INDEX[name]["mutating"]:
        if str(confirm or "") != "EXECUTE":
            return _error(
                "mutating_ops_require_confirm_EXECUTE",
                "Spend/destructive operations require confirm: EXECUTE",
                400,
            )
        if not decision.allowed:
            return {
                **_error("policy_denied", decision.reason, 403),
                "policy": decision.to_dict(),
            }

    try:
        data = _dispatch(name, args, client=client, transport=transport)
        payload = {
            "ok": True,
            "tool": name,
            "data": redact(data),
            "policy": decision.to_dict(),
            "secret_ref": "vault://runpod/api-key",
        }
        assert_no_secrets(payload)
        return payload
    except SecretError as exc:
        return _error("vault_unavailable", str(exc), 503)
    except RunPodError as exc:
        code = "runpod_http"
        if exc.status is None and "timeout" in str(exc).lower():
            code = "runpod_timeout"
        elif exc.status is None and "malformed" in str(exc).lower():
            code = "runpod_malformed"
        return redact(
            {
                **_error(code, str(exc), exc.status or 502),
                "runpod_status": exc.status,
                "payload": exc.payload,
            }
        )
    except ManifestError as exc:
        return _error("validation_error", str(exc), 400)
    except ValueError as exc:
        return _error("validation_error", str(exc), 400)


def _client(client: RunPodClient | None, transport: Callable | None) -> RunPodClient:
    if client:
        return client
    return RunPodClient(SecretBroker(), opener=None, transport=transport)


def _dispatch(
    name: str,
    args: dict[str, Any],
    *,
    client: RunPodClient | None,
    transport: Callable | None,
) -> Any:
    rp = _client(client, transport)
    if name == "runpod_status":
        pods_raw = rp.list_pods()
        pods = normalize_pods(pods_raw)
        auth = rp.broker.status()
        return {
            "auth": {"source": auth.source, "reference": auth.reference, "present": auth.present},
            "pod_count": len(pods),
            "idle_paid_resources": idle_paid_resources(pods),
        }
    if name == "runpod_account":
        return rp.account()
    if name == "runpod_list_pods":
        return {"pods": normalize_pods(rp.list_pods())}
    if name in {"runpod_get_pod", "runpod_pod_status"}:
        pod = rp.get_pod(str(args["pod_id"]))
        if name == "runpod_pod_status":
            return {
                "id": pod.get("id") if isinstance(pod, Mapping) else None,
                "desiredStatus": (pod or {}).get("desiredStatus") if isinstance(pod, Mapping) else None,
                "status": parse_pod_state(pod),
            }
        return pod
    if name == "runpod_stream_pod_logs":
        return rp.pod_logs(str(args["pod_id"]), int(args.get("lines") or 200))
    if name == "runpod_list_gpu_types":
        return parse_gpu_catalog(rp.list_gpu_types())
    if name == "runpod_gpu_availability":
        return {"gpus": parse_gpu_catalog(rp.list_gpu_types())}
    if name == "runpod_gpu_pricing":
        return {"gpus": parse_gpu_catalog(rp.list_gpu_types())}
    if name == "runpod_list_endpoints":
        return rp.list_endpoints()
    if name == "runpod_get_endpoint":
        return rp.get_endpoint(str(args["endpoint_id"]))
    if name == "runpod_endpoint_health":
        data = rp.get_endpoint(str(args["endpoint_id"]))
        return {"endpoint": data, "health": (data or {}).get("workers") if isinstance(data, Mapping) else data}
    if name == "runpod_list_jobs":
        return rp.list_jobs(args.get("endpoint_id"))
    if name in {"runpod_get_job", "runpod_stream_job"}:
        return rp.get_job(str(args.get("endpoint_id") or ""), str(args["job_id"]))
    if name == "runpod_list_volumes":
        return rp.list_volumes()
    if name == "runpod_get_volume":
        return rp.get_volume(str(args["volume_id"]))
    if name == "runpod_network_info":
        pod = rp.get_pod(str(args["pod_id"]))
        if not isinstance(pod, Mapping):
            raise RunPodError("malformed pod payload")
        return {
            "id": pod.get("id"),
            "ports": pod.get("ports") or pod.get("portMappings"),
            "runtime": pod.get("runtime"),
            "publicIp": pod.get("publicIp") or (pod.get("runtime") or {}).get("ports")
            if isinstance(pod.get("runtime"), Mapping)
            else pod.get("publicIp"),
        }
    if name == "runpod_billing":
        return rp.billing()
    if name == "runpod_cost_estimate":
        catalog = parse_gpu_catalog(rp.list_gpu_types())
        gpu = str(args["gpu_type"])
        match = next(
            (
                g
                for g in catalog
                if gpu.lower() in str(g.get("id") or "").lower()
                or gpu.lower() in str(g.get("displayName") or "").lower()
            ),
            None,
        )
        hourly = None
        if match:
            hourly = match.get("securePrice") or match.get("communityPrice") or match.get("lowestPrice")
        count = int(args.get("gpu_count") or 1)
        if hourly is not None:
            hourly = float(hourly) * count
        hours = float(args["hours"])
        check = check_cost(
            live_hourly=hourly,
            estimated_runtime_hours=hours,
            max_hourly_rate=args.get("max_hourly_rate"),
            max_total_budget=args.get("max_total_budget"),
            requested_gpu=gpu,
            requested_gpu_count=count,
        )
        return {
            "allowed": check.allowed,
            "reason": check.reason,
            "gpu": gpu,
            "hourly": check.estimated_hourly,
            "hours": hours,
            "estimated_total": check.estimated_total,
            "remaining_budget": check.remaining_budget,
        }
    if name == "runpod_burn_rate":
        pods = normalize_pods(rp.list_pods())
        catalog = parse_gpu_catalog(rp.list_gpu_types())
        prices = {str(g.get("id")): g for g in catalog}
        running = [p for p in pods if parse_pod_state(p) in {"RUNNING", "EXITED"} or str(p.get("desiredStatus") or "").upper() == "RUNNING"]
        hourly = 0.0
        priced = 0
        for pod in running:
            if str(pod.get("desiredStatus") or pod.get("status") or "").upper() != "RUNNING":
                continue
            gpu_id = str(pod.get("gpuTypeId") or pod.get("machine") or "")
            info = prices.get(gpu_id)
            if not info:
                continue
            rate = info.get("securePrice") or info.get("communityPrice") or info.get("lowestPrice")
            if rate is None:
                continue
            hourly += float(rate) * int(pod.get("gpuCount") or 1)
            priced += 1
        return {"running_priced": priced, "estimated_hourly_burn": hourly, "idle_paid_resources": idle_paid_resources(pods)}
    if name in {"runpod_prepare_training", "runpod_validate_manifest"}:
        man = validate_manifest(args["manifest"] if isinstance(args.get("manifest"), Mapping) else {})
        return {"ok": True, "status": "prepared", "execution": "waits_for_approval_unless_full_lane", "manifest": man.to_dict()}
    if name == "runpod_training_status":
        if args.get("pod_id"):
            return rp.get_pod(str(args["pod_id"]))
        return {"pods": normalize_pods(rp.list_pods())}
    if name == "runpod_training_checkpoints":
        if args.get("volume_id"):
            return rp.get_volume(str(args["volume_id"]))
        return rp.list_volumes()
    if name == "runpod_live_verify":
        pods = normalize_pods(rp.list_pods())
        gpus = parse_gpu_catalog(rp.list_gpu_types())
        billing = None
        try:
            billing = rp.billing()
        except RunPodError:
            billing = {"available": False}
        auth = rp.broker.status()
        return {
            "auth": {"source": auth.source, "reference": auth.reference, "present": auth.present},
            "pod_count": len(pods),
            "gpu_count": len(gpus),
            "billing": billing,
            "resource": RESOURCE_URL,
        }
    if name == "runpod_create_pod":
        body = {
            "name": args.get("name") or args.get("workload_id") or "echo-runpod",
            "gpuTypeIds": [args["gpu_type"]],
            "gpuCount": int(args.get("gpu_count") or 1),
            "imageName": args.get("image") or args.get("container_image"),
        }
        digest = idempotency_digest(name, body)
        return {"result": rp.create_pod(body), "idempotency": digest}
    if name == "runpod_start_pod":
        return rp.start_pod(str(args["pod_id"]))
    if name == "runpod_stop_pod":
        return rp.stop_pod(str(args["pod_id"]))
    if name == "runpod_restart_pod":
        return rp.restart_pod(str(args["pod_id"]))
    if name == "runpod_terminate_pod":
        return rp.terminate_pod(str(args["pod_id"]))
    if name in {"runpod_resize_pod", "runpod_change_gpu"}:
        return rp.update_pod(str(args["pod_id"]), {"gpuTypeIds": [args.get("gpu_type")]} if args.get("gpu_type") else {})
    if name == "runpod_attach_volume":
        return rp.update_pod(str(args["pod_id"]), {"networkVolumeId": args["volume_id"]})
    if name == "runpod_launch_training":
        man = validate_manifest(args["manifest"] if isinstance(args.get("manifest"), Mapping) else {})
        body = {
            "name": man.workload_id,
            "gpuTypeIds": [man.gpu_type],
            "gpuCount": man.gpu_count,
            "imageName": man.container_image,
            "volumeInGb": man.storage_size,
        }
        return {"manifest": man.to_dict(), "result": rp.create_pod(body)}
    if name == "runpod_resume_training":
        return rp.start_pod(str(args["pod_id"]))
    if name == "runpod_cancel_job":
        return rp.cancel_job(str(args.get("endpoint_id") or ""), str(args["job_id"]))
    raise RunPodError(f"dispatch not implemented: {name}")


def parse_pod_state(pod: Any) -> str:
    if not isinstance(pod, Mapping):
        return "UNKNOWN"
    raw = pod.get("desiredStatus") or pod.get("status") or pod.get("currentStatus") or ""
    if isinstance(raw, Mapping):
        raw = raw.get("state") or raw.get("status") or ""
    text = str(raw).upper()
    if text in {"RUNNING", "EXITED", "DEAD", "CREATED", "RESTARTING", "PAUSED", "TERMINATED"}:
        return text
    if "run" in text.lower():
        return "RUNNING"
    return text or "UNKNOWN"
