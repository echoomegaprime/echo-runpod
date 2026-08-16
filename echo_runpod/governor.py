"""Cost governance. Query live prices; never hard-code them as truth."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class CostCheck:
    allowed: bool
    reason: str
    estimated_hourly: float | None
    estimated_total: float | None
    remaining_budget: float | None


def check_cost(
    *,
    live_hourly: float | None,
    estimated_runtime_hours: float | None,
    max_hourly_rate: float | None,
    max_total_budget: float | None,
    accumulated: float = 0.0,
    approved_gpu_classes: list[str] | None = None,
    requested_gpu: str | None = None,
    approved_gpu_count: int | None = None,
    requested_gpu_count: int | None = None,
) -> CostCheck:
    if requested_gpu and approved_gpu_classes:
        allowed = {c.lower() for c in approved_gpu_classes}
        if requested_gpu.lower() not in allowed:
            return CostCheck(False, "GPU class outside allowlist is rejected", live_hourly, None, None)
    if (
        requested_gpu_count is not None
        and approved_gpu_count is not None
        and int(requested_gpu_count) > int(approved_gpu_count)
    ):
        return CostCheck(False, "GPU count increase is rejected", live_hourly, None, None)
    if live_hourly is None:
        return CostCheck(False, "live pricing required before spend", None, None, None)
    if max_hourly_rate is not None and float(live_hourly) > float(max_hourly_rate):
        return CostCheck(
            False,
            "hourly rate exceeds max_hourly_rate",
            live_hourly,
            None,
            None,
        )
    estimated_total = None
    remaining = None
    if estimated_runtime_hours is not None:
        estimated_total = float(live_hourly) * float(estimated_runtime_hours) + float(accumulated)
    if max_total_budget is not None:
        remaining = float(max_total_budget) - float(accumulated)
        if remaining < 0:
            return CostCheck(False, "budget overrun is rejected", live_hourly, estimated_total, remaining)
        if estimated_total is not None and estimated_total > float(max_total_budget):
            return CostCheck(False, "projected total exceeds remaining approved budget", live_hourly, estimated_total, remaining)
    return CostCheck(True, "within cost bounds", live_hourly, estimated_total, remaining)


def idle_paid_resources(pods: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    idle = []
    for pod in pods:
        status = str(pod.get("desiredStatus") or pod.get("status") or "").upper()
        name = pod.get("name") or pod.get("id")
        if status == "RUNNING" and not pod.get("workload_id"):
            idle.append({"id": pod.get("id"), "name": name, "reason": "running without workload_id"})
        if status == "EXITED" and float(pod.get("volumeInGb") or 0) > 0:
            idle.append(
                {
                    "id": pod.get("id"),
                    "name": name,
                    "reason": "stopped pod may still incur storage charges",
                }
            )
    return idle
