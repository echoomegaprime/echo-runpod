"""Canonical Echo-facing capability map. Names follow echo.runpod.*."""

from __future__ import annotations

from echo_runpod.mcp import ALL_SCOPES, RESOURCE_URL, TOOLS
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
        records.append(
            {
                "capability": cap,
                "tool": tool,
                "read_only": tool in READ_ACTIONS and tool not in APPROVAL_ACTIONS,
                "approval_required": tool in APPROVAL_ACTIONS or tool in DESTRUCTIVE_ACTIONS,
                "annotations": hints,
                "confirm": "EXECUTE" if tool in APPROVAL_ACTIONS or tool in DESTRUCTIVE_ACTIONS else None,
                "mcp_resource": RESOURCE_URL,
                "oauth_scopes": list(ALL_SCOPES),
            }
        )
    return records
