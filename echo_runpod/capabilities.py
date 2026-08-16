"""Canonical Echo-facing capability map. Names follow echo.runpod.*."""

from __future__ import annotations

from echo_runpod.policy import APPROVAL_ACTIONS, DESTRUCTIVE_ACTIONS, READ_ACTIONS, annotations_for

NEXUS_CAPABILITIES = [
    "echo.runpod.status",
    "echo.runpod.list_pods",
    "echo.runpod.get_pod",
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
    "echo.runpod.billing",
    "echo.runpod.prepare_training",
    "echo.runpod.training_status",
    "echo.runpod.training_checkpoints",
    "echo.runpod.create_pod",
    "echo.runpod.start_pod",
    "echo.runpod.stop_pod",
    "echo.runpod.restart_pod",
    "echo.runpod.terminate_pod",
    "echo.runpod.launch_training",
    "echo.runpod.resume_training",
]

TOOL_TO_CAPABILITY = {
    "runpod_status": "echo.runpod.status",
    "runpod_list_pods": "echo.runpod.list_pods",
    "runpod_get_pod": "echo.runpod.get_pod",
    "runpod_stream_pod_logs": "echo.runpod.stream_pod_logs",
    "runpod_list_gpu_types": "echo.runpod.list_gpu_types",
    "runpod_gpu_availability": "echo.runpod.gpu_availability",
    "runpod_gpu_pricing": "echo.runpod.gpu_pricing",
    "runpod_list_endpoints": "echo.runpod.list_endpoints",
    "runpod_get_endpoint": "echo.runpod.get_endpoint",
    "runpod_endpoint_health": "echo.runpod.endpoint_health",
    "runpod_list_jobs": "echo.runpod.list_jobs",
    "runpod_get_job": "echo.runpod.get_job",
    "runpod_stream_job": "echo.runpod.stream_job",
    "runpod_list_volumes": "echo.runpod.list_volumes",
    "runpod_get_volume": "echo.runpod.get_volume",
    "runpod_billing": "echo.runpod.billing",
    "runpod_prepare_training": "echo.runpod.prepare_training",
    "runpod_training_status": "echo.runpod.training_status",
    "runpod_training_checkpoints": "echo.runpod.training_checkpoints",
    "runpod_create_pod": "echo.runpod.create_pod",
    "runpod_start_pod": "echo.runpod.start_pod",
    "runpod_stop_pod": "echo.runpod.stop_pod",
    "runpod_restart_pod": "echo.runpod.restart_pod",
    "runpod_terminate_pod": "echo.runpod.terminate_pod",
    "runpod_launch_training": "echo.runpod.launch_training",
    "runpod_resume_training": "echo.runpod.resume_training",
}

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
            }
        )
    return records
