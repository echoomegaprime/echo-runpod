"""Echo RunPod edge adapter for the live Echo OAuth MCP pack.

Registers /oauth-mcp-runpod-v1 (and a small Nexus subset) then delegates
execution to the canonical echo_runpod pack. Advertises only live-accepted
OAuth scopes. Never advertises echo.write or invented echo.runpod.* scopes.
Secrets stay at vault://runpod/api-key then RUNPOD_API_KEY.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

RESOURCE_PATH = "/oauth-mcp-runpod-v1"
RESOURCE_ID = "oauth-mcp-runpod-v1"
NEXUS_PATH = "/oauth-mcp-nexus-v1"

# Live-accepted scopes. Must match echo_runpod.oauth / authorization server.
SCOPE_SEARCH = "echo.search"
SCOPE_FETCH = "echo.fetch"
SCOPE_READ = "echo.invoke.read"
SCOPE_INVOKE = "echo.sdk.invoke"
ALL_SCOPES = (SCOPE_SEARCH, SCOPE_FETCH, SCOPE_READ, SCOPE_INVOKE)

NEXUS_SUBSET_TOOLS = (
    "runpod_status",
    "runpod_list_pods",
    "runpod_get_pod",
    "runpod_list_gpu_types",
    "runpod_gpu_pricing",
    "runpod_billing",
    "runpod_prepare_training",
    "runpod_live_verify",
    "runpod_stop_pod",
    "runpod_create_pod",
)

PREPARE_TOOLS = frozenset({"runpod_prepare_training", "runpod_validate_manifest", "runpod_cost_estimate"})
CONTROL_TOOLS = frozenset(
    {
        "runpod_start_pod",
        "runpod_stop_pod",
        "runpod_restart_pod",
        "runpod_terminate_pod",
        "runpod_cancel_job",
    }
)
SPEND_TOOLS = frozenset(
    {
        "runpod_create_pod",
        "runpod_resize_pod",
        "runpod_change_gpu",
        "runpod_attach_volume",
        "runpod_launch_training",
        "runpod_resume_training",
    }
)
MUTATING_TOOLS = CONTROL_TOOLS | SPEND_TOOLS

# Fallback catalog if C:\\ECHO_OMEGA_PRIME\\RUNPOD is not importable yet.
FALLBACK_TOOLS = (
    "runpod_status",
    "runpod_account",
    "runpod_list_pods",
    "runpod_get_pod",
    "runpod_pod_status",
    "runpod_stream_pod_logs",
    "runpod_list_gpu_types",
    "runpod_gpu_availability",
    "runpod_gpu_pricing",
    "runpod_list_endpoints",
    "runpod_get_endpoint",
    "runpod_endpoint_health",
    "runpod_list_jobs",
    "runpod_get_job",
    "runpod_stream_job",
    "runpod_list_volumes",
    "runpod_get_volume",
    "runpod_network_info",
    "runpod_billing",
    "runpod_cost_estimate",
    "runpod_burn_rate",
    "runpod_training_status",
    "runpod_training_checkpoints",
    "runpod_live_verify",
    "runpod_prepare_training",
    "runpod_validate_manifest",
    "runpod_create_pod",
    "runpod_start_pod",
    "runpod_stop_pod",
    "runpod_restart_pod",
    "runpod_terminate_pod",
    "runpod_resize_pod",
    "runpod_change_gpu",
    "runpod_attach_volume",
    "runpod_launch_training",
    "runpod_resume_training",
    "runpod_cancel_job",
)

_RUNPOD_ROOTS = (
    Path(r"C:\ECHO_OMEGA_PRIME\RUNPOD"),
    Path(r"C:\ECHO_OMEGA_PRIME\repos\echo-runpod"),
    Path("/workspace/echo-runpod"),
)

_mcp = None
_import_error: str | None = None


def _ensure_path() -> None:
    for root in _RUNPOD_ROOTS:
        if (root / "echo_runpod").is_dir():
            text = str(root)
            if text not in sys.path:
                sys.path.insert(0, text)
            return


def _load_mcp():
    global _mcp, _import_error
    if _mcp is not None:
        return _mcp
    _ensure_path()
    try:
        from echo_runpod import mcp as module  # type: ignore

        _mcp = module
        _import_error = None
        return _mcp
    except Exception as exc:  # noqa: BLE001 — edge must stay up
        _import_error = f"{type(exc).__name__}: {exc}"
        return None


def tool_names() -> list[str]:
    module = _load_mcp()
    if module is not None:
        return [t["name"] for t in module.TOOLS]
    return list(FALLBACK_TOOLS)


def is_runpod_tool(name: str) -> bool:
    return str(name or "").startswith("runpod_")


def required_scope(name: str) -> str:
    if name in MUTATING_TOOLS:
        return SCOPE_INVOKE
    return SCOPE_READ


def required_scopes_map() -> dict[str, str]:
    return {name: required_scope(name) for name in tool_names()}


def configure_pack(
    pack: dict[str, dict[str, Any]],
    required_scopes: dict[str, str],
    mutating_tools: set[str],
    pack_paths: set[str] | None = None,
) -> None:
    """Idempotently register the dedicated RunPod resource + Nexus subset."""
    names = tool_names()
    pack[RESOURCE_PATH] = {
        "id": RESOURCE_ID,
        "name": "Echo RunPod MCP v1",
        "scopes": list(ALL_SCOPES),
        "tools": list(names),
    }
    if pack_paths is not None:
        pack_paths.add(RESOURCE_PATH)

    nexus = pack.get(NEXUS_PATH)
    if isinstance(nexus, dict):
        tools = nexus.setdefault("tools", [])
        scopes = nexus.setdefault("scopes", [])
        for name in NEXUS_SUBSET_TOOLS:
            if name not in tools:
                tools.append(name)
        # Only attach live-accepted scopes. Never echo.runpod.* or echo.write.
        for scope in (SCOPE_READ, SCOPE_INVOKE, SCOPE_FETCH, SCOPE_SEARCH):
            if scope not in scopes:
                scopes.append(scope)

    required_scopes.update(required_scopes_map())
    mutating_tools.update(MUTATING_TOOLS)


def tool_definition(name: str) -> dict[str, Any] | None:
    if not is_runpod_tool(name):
        return None
    module = _load_mcp()
    if module is not None and name in module.TOOL_INDEX:
        tool = module.TOOL_INDEX[name]
        return {
            "name": tool["name"],
            "description": tool["description"],
            "inputSchema": tool["inputSchema"],
            "annotations": tool["annotations"],
        }
    if name not in FALLBACK_TOOLS:
        return None
    properties: dict[str, Any] = {}
    required: list[str] = []
    mutating = name in MUTATING_TOOLS
    if mutating:
        properties["confirm"] = {"type": "string", "description": "Must be EXECUTE for consequential mutations"}
        properties["approved_manifest"] = {"type": "object", "description": "Commander-approved execution manifest"}
        properties["full_lane"] = {"type": "object", "description": "Bounded full-lane authorization object"}
        properties["idempotency_key"] = {"type": "string", "description": "Client idempotency key"}
        required.append("confirm")
    schema: dict[str, Any] = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        schema["required"] = required
    return {
        "name": name,
        "description": f"{name} (governed Echo RunPod tool)",
        "inputSchema": schema,
        "annotations": {
            "readOnlyHint": not mutating,
            "destructiveHint": name == "runpod_terminate_pod",
            "idempotentHint": name in {"runpod_start_pod", "runpod_stop_pod", "runpod_terminate_pod"},
            "openWorldHint": True,
        },
    }


def execute(name: str, args: dict[str, Any], scopes: list[str] | None = None) -> dict[str, Any]:
    module = _load_mcp()
    if module is None:
        return {
            "error": "runpod_pack_unavailable",
            "detail": _import_error or "echo_runpod not importable",
            "secret_ref": "vault://runpod/api-key",
        }
    granted = list(scopes) if scopes is not None else list(ALL_SCOPES)
    payload = module.call_tool(name, dict(args or {}), scopes=granted)
    if not payload.get("ok"):
        out = {"error": payload.get("error_type") or payload.get("error") or "runpod_error"}
        for key, value in payload.items():
            if key != "ok":
                out[key] = value
        return out
    return payload


__all__ = [
    "ALL_SCOPES",
    "MUTATING_TOOLS",
    "NEXUS_SUBSET_TOOLS",
    "RESOURCE_ID",
    "RESOURCE_PATH",
    "SCOPE_INVOKE",
    "SCOPE_READ",
    "configure_pack",
    "execute",
    "is_runpod_tool",
    "required_scope",
    "required_scopes_map",
    "tool_definition",
    "tool_names",
]
