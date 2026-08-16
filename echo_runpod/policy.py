"""Approval gates, full-lane bounds, and action classification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

READ_ACTIONS = frozenset(
    {
        "runpod_status",
        "runpod_list_pods",
        "runpod_get_pod",
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
        "runpod_billing",
        "runpod_prepare_training",
        "runpod_training_status",
        "runpod_training_checkpoints",
    }
)

APPROVAL_ACTIONS = frozenset(
    {
        "runpod_create_pod",
        "runpod_start_pod",
        "runpod_stop_pod",
        "runpod_restart_pod",
        "runpod_terminate_pod",
        "runpod_resize_pod",
        "runpod_change_gpu",
        "runpod_create_volume",
        "runpod_launch_training",
        "runpod_resume_training",
        "runpod_create_endpoint",
        "runpod_scale_endpoint",
    }
)

DESTRUCTIVE_ACTIONS = frozenset(
    {
        "runpod_terminate_pod",
        "runpod_delete_volume",
        "runpod_delete_endpoint",
    }
)

FULL_LANE_ALLOWED = frozenset(
    {
        "runpod_list_pods",
        "runpod_get_pod",
        "runpod_stream_pod_logs",
        "runpod_list_gpu_types",
        "runpod_gpu_availability",
        "runpod_gpu_pricing",
        "runpod_list_volumes",
        "runpod_get_volume",
        "runpod_billing",
        "runpod_prepare_training",
        "runpod_training_status",
        "runpod_training_checkpoints",
        "runpod_create_pod",
        "runpod_start_pod",
        "runpod_stop_pod",
        "runpod_restart_pod",
        "runpod_terminate_pod",
        "runpod_launch_training",
        "runpod_resume_training",
    }
)

REQUIRED_FULL_LANE_FIELDS = (
    "workload_id",
    "allowed_gpu_classes",
    "max_gpu_count",
    "max_hourly_rate",
    "max_total_spend",
    "max_runtime",
    "allowed_storage",
    "allowed_pod_count",
    "allowed_endpoint_count",
    "dataset_identity",
    "model_identity",
    "artifact_destination",
    "termination_policy",
)


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    action: str
    reason: str
    mutation: bool
    requires_confirm: bool
    confirm_token: str | None
    lane: str
    annotations: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "reason": self.reason,
            "mutation": self.mutation,
            "requires_confirm": self.requires_confirm,
            "confirm_token": self.confirm_token,
            "lane": self.lane,
            "annotations": self.annotations,
        }


def annotations_for(action: str) -> dict[str, Any]:
    read = action in READ_ACTIONS
    destructive = action in DESTRUCTIVE_ACTIONS
    mutation = action in APPROVAL_ACTIONS or destructive
    idempotent = action in {
        "runpod_start_pod",
        "runpod_stop_pod",
        "runpod_terminate_pod",
    }
    return {
        "readOnlyHint": read and not mutation,
        "destructiveHint": destructive,
        "idempotentHint": idempotent,
        "openWorldHint": True,
    }


def _identity_values(value: Any) -> set[str]:
    """Accept a string identity or a dict with name/id/sha256/model keys."""
    if value is None:
        return set()
    if isinstance(value, str):
        return {value} if value else set()
    if isinstance(value, Mapping):
        out: set[str] = set()
        for key in ("name", "id", "model", "sha256", "hash", "identity"):
            item = value.get(key)
            if item:
                out.add(str(item))
        return out
    return {str(value)}


def _lane_ok(lane: Mapping[str, Any] | None, request: Mapping[str, Any]) -> tuple[bool, str]:
    if not lane:
        return False, "no full lane"
    missing = [f for f in REQUIRED_FULL_LANE_FIELDS if f not in lane]
    if missing:
        return False, f"full lane missing fields: {', '.join(missing)}"
    req_wl = request.get("workload_id")
    if req_wl and req_wl != lane["workload_id"]:
        return False, "full lane cannot change workload"
    ds_vals = _identity_values(lane.get("dataset_identity"))
    if request.get("dataset_sha256") and str(request["dataset_sha256"]) not in ds_vals:
        return False, "full lane cannot change dataset"
    model_vals = _identity_values(lane.get("model_identity"))
    if request.get("model") and str(request["model"]) not in model_vals:
        return False, "full lane cannot change model"
    gpu = request.get("gpu_class") or request.get("gpu_type")
    allowed = {str(x).lower() for x in lane["allowed_gpu_classes"]}
    if gpu and str(gpu).lower() not in allowed:
        return False, "gpu class outside allowlist"
    count = request.get("gpu_count")
    if count is not None and int(count) > int(lane["max_gpu_count"]):
        return False, "gpu count increase rejected"
    hourly = request.get("hourly_rate")
    if hourly is not None and float(hourly) > float(lane["max_hourly_rate"]):
        return False, "hourly rate exceeds full-lane bound"
    spend = request.get("projected_spend")
    if spend is not None and float(spend) > float(lane["max_total_spend"]):
        return False, "budget overrun rejected"
    return True, "within full-lane bounds"


def evaluate_action(
    action: str,
    *,
    confirm: str | None = None,
    approved_manifest: Mapping[str, Any] | None = None,
    full_lane: Mapping[str, Any] | None = None,
    request: Mapping[str, Any] | None = None,
) -> PolicyDecision:
    request = dict(request or {})
    hints = annotations_for(action)
    mutation = action in APPROVAL_ACTIONS or action in DESTRUCTIVE_ACTIONS
    if action in READ_ACTIONS and not mutation:
        return PolicyDecision(
            True,
            action,
            "read action allowed without execution approval",
            False,
            False,
            None,
            "observe",
            hints,
        )
    if action not in APPROVAL_ACTIONS and action not in DESTRUCTIVE_ACTIONS:
        return PolicyDecision(
            False, action, "unknown action", False, False, None, "unknown", hints
        )

    if full_lane:
        ok, why = _lane_ok(full_lane, request)
        if not ok:
            return PolicyDecision(False, action, why, True, True, "EXECUTE", "full_lane", hints)
        if action not in FULL_LANE_ALLOWED:
            return PolicyDecision(
                False,
                action,
                "action not permitted in full lane",
                True,
                True,
                "EXECUTE",
                "full_lane",
                hints,
            )
        if confirm != "EXECUTE":
            return PolicyDecision(
                False,
                action,
                "Echo Nexus mutations require confirm: EXECUTE",
                True,
                True,
                "EXECUTE",
                "full_lane",
                hints,
            )
        return PolicyDecision(True, action, why, True, True, "EXECUTE", "full_lane", hints)

    if approved_manifest:
        mid = approved_manifest.get("workload_id")
        if request.get("workload_id") and mid and request["workload_id"] != mid:
            return PolicyDecision(
                False,
                action,
                "wrong workload ID is rejected",
                True,
                True,
                "EXECUTE",
                "approved",
                hints,
            )
        if confirm != "EXECUTE":
            return PolicyDecision(
                False,
                action,
                "approved manifest present but confirm: EXECUTE is required",
                True,
                True,
                "EXECUTE",
                "approved",
                hints,
            )
        return PolicyDecision(
            True, action, "approved execution manifest", True, True, "EXECUTE", "approved", hints
        )

    return PolicyDecision(
        False,
        action,
        "approval-gated action requires an approved execution manifest or a bounded full lane",
        True,
        True,
        "EXECUTE",
        "gated",
        hints,
    )
