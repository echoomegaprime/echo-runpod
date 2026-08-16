"""Workload isolation — never reuse another project's pod."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


FORBIDDEN_CROSS = {
    ("landman", "prometheus"),
    ("prometheus", "landman"),
}


@dataclass(frozen=True)
class IsolationDecision:
    allowed: bool
    reason: str


def isolate(
    *,
    request_workload_id: str,
    request_project: str,
    request_dataset_sha: str | None,
    request_model: str | None,
    target: Mapping[str, Any] | None,
) -> IsolationDecision:
    if not request_workload_id:
        return IsolationDecision(False, "workload_id is required")
    if not request_project:
        return IsolationDecision(False, "project is required")
    if target is None:
        return IsolationDecision(True, "no existing resource to bind")
    t_wl = str(target.get("workload_id") or "")
    t_proj = str(target.get("project") or "")
    t_ds = str(target.get("dataset_sha256") or target.get("dataset_sha") or "")
    t_model = str(target.get("model") or "")
    if t_wl and t_wl != request_workload_id:
        return IsolationDecision(False, "wrong workload ID is rejected")
    if t_proj and t_proj != request_project:
        pair = (t_proj.lower(), request_project.lower())
        if pair in FORBIDDEN_CROSS:
            return IsolationDecision(False, "Landman and Prometheus workloads must stay isolated")
        return IsolationDecision(False, "project mismatch")
    if request_dataset_sha and t_ds and t_ds.lower() != request_dataset_sha.lower():
        return IsolationDecision(False, "wrong dataset SHA is rejected")
    if request_model and t_model and t_model != request_model:
        return IsolationDecision(False, "wrong model identity is rejected")
    return IsolationDecision(True, "workload identity matches")
