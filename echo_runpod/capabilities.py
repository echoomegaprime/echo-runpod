"""Canonical Echo-facing capability map.

Capability names remain echo.runpod.* (internal registry ids).
OAuth scopes on each record are the live-accepted set for that tool only.
"""

from __future__ import annotations

from echo_runpod.mcp import RESOURCE_URL, TOOLS
from echo_runpod.oauth import ALL_SCOPES, OAUTH_NEVER, PACKAGE_VERSION
from echo_runpod.policy import APPROVAL_ACTIONS, DESTRUCTIVE_ACTIONS, READ_ACTIONS, annotations_for

NEXUS_CAPABILITIES = [
    "echo.runpod.status",
    "echo.runpod.account",
    "echo.runpod.list_pods",
    "echo.runpod.get_pod",
    "echo.runpod.pod_status",
    "echo.runpod.stream_pod_logs",
    "echo.runpod.list_gpu_types",
    "echo.runpod.gpu_availability",
    "echo.runpod.gpu_pricing",
    "echo.runpod.list_endpoints",
    "echo.runpod.get_endpoint",
    "echo.runpod.endpoint_health",
    "echo.runpod.list_jobs",
    "echo.runpod.get_job",
    "echo.runpod.stream_job",
    "echo.runpod.list_volumes",
    "echo.runpod.get_volume",
    "echo.runpod.network_info",
    "echo.runpod.billing",
    "echo.runpod.cost_estimate",
    "echo.runpod.burn_rate",
    "echo.runpod.prepare_training",
    "echo.runpod.training_status",
    "echo.runpod.training_checkpoints",
    "echo.runpod.live_verify",
    "echo.runpod.create_pod",
    "echo.runpod.start_pod",
    "echo.runpod.stop_pod",
    "echo.runpod.restart_pod",
    "echo.runpod.terminate_pod",
    "echo.runpod.resize_pod",
    "echo.runpod.change_gpu",
    "echo.runpod.attach_volume",
    "echo.runpod.launch_training",
    "echo.runpod.resume_training",
    "echo.runpod.cancel_job",
]

TOOL_TO_CAPABILITY = {name: name.replace("runpod_", "echo.runpod.", 1) for name in (
    *[t["name"] for t in TOOLS],
)}

OFFICIAL_MCP_TOOLS = {
    "list-pods": "runpod_list_pods",
    "get-pod": "runpod_get_pod",
    "create-pod": "runpod_create_pod",
    "update-pod": "runpod_resize_pod",
    "start-pod": "runpod_start_pod",
    "stop-pod": "runpod_stop_pod",
    "restart-pod": "runpod_restart_pod",
    "stream-pod-logs": "runpod_stream_pod_logs",
    "delete-pod": "runpod_terminate_pod",
}


def capability_records() -> list[dict]:
    records = []
    for tool, cap in TOOL_TO_CAPABILITY.items():
        hints = annotations_for(tool)
        tool_meta = next((t for t in TOOLS if t["name"] == tool), None)
        scopes = list(tool_meta["scopes"]) if tool_meta else list(ALL_SCOPES)
        records.append(
            {
                "capability": cap,
                "tool": tool,
                "read_only": tool in READ_ACTIONS and tool not in APPROVAL_ACTIONS,
                "approval_required": tool in APPROVAL_ACTIONS or tool in DESTRUCTIVE_ACTIONS,
                "annotations": hints,
                "confirm": "EXECUTE" if tool in APPROVAL_ACTIONS or tool in DESTRUCTIVE_ACTIONS else None,
                "mcp_resource": RESOURCE_URL,
                "oauth_scopes": scopes,
            }
        )
    return records


def nexus_manifest() -> dict:
    return {
        "pack": "echo-runpod",
        "version": PACKAGE_VERSION,
        "control_plane": "echo-nexus",
        "mcp_resource": RESOURCE_URL,
        "mcp_path": "/oauth-mcp-runpod-v1",
        "sdk_allowlist": "closed — do not register via sdk_invoke_allowed",
        "execution_path": "governed policy + official RunPod MCP/REST via Echo Nexus pack edge",
        "confirm": "EXECUTE",
        "oauth_scopes_used": list(ALL_SCOPES),
        "oauth_never": list(OAUTH_NEVER),
        "secret_ref": "vault://runpod/api-key",
        "secret_env_fallback": "RUNPOD_API_KEY",
        "upstream": {
            "runpod_plugins_official_commit": "b669407688056642d09d2049df5432cb78ae33f0",
            "runpod_plugins_official_version": "1.1.2",
            "runpod_mcp_commit": "51d6fd9a0ff16a4eeb7d508972aeb5502f514939",
        },
        "capabilities": capability_records(),
    }
