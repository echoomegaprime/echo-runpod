"""Prompt router — one canonical skill, multiple lanes."""

from __future__ import annotations

from dataclasses import dataclass, field


LANES = (
    "inspection",
    "gpu_selection",
    "training_prepare",
    "training_execute",
    "serverless",
    "storage",
    "networking",
    "logs",
    "cost",
    "lifecycle_mutate",
)


@dataclass(frozen=True)
class Route:
    lane: str
    mutation: bool
    requires_approval: bool
    reason: str
    references: tuple[str, ...] = field(default_factory=tuple)


_INSPECT = (
    "show my",
    "list pod",
    "list pods",
    "inspect pod",
    "get pod",
    "pod status",
    "show pods",
    "what pods",
    "fleet",
    "runpod pods",
)
_GPU = (
    "which gpu",
    "what gpu",
    "gpu should",
    "select gpu",
    "recommend gpu",
    "qlora",
    "lora",
    "vram",
    "a100",
    "h100",
    "4090",
    "l40s",
    "a40",
)
_TRAIN_PREP = (
    "prepare training",
    "training manifest",
    "train this",
    "train the",
    "fine-tune",
    "finetune",
    "adapter training",
    "sft ",
)
_TRAIN_EXEC = (
    "launch training",
    "start training",
    "run training",
    "resume training",
)
_SERVERLESS = ("endpoint", "serverless", "runsync", "worker")
_STORAGE = ("volume", "network volume", "checkpoint", "artifact")
_NET = ("ssh", "port mapping", "public ip", "proxy url")
_LOGS = ("logs", "oom", "cuda error", "nan loss", "stalled")
_COST = ("billing", "cost", "budget", "hourly rate", "spend")
_MUTATE = (
    "create pod",
    "start pod",
    "stop pod",
    "restart pod",
    "terminate",
    "delete pod",
    "resize",
    "change gpu",
)


def _has(text: str, needles: tuple[str, ...]) -> bool:
    return any(n in text for n in needles)


def route_prompt(prompt: str) -> Route:
    text = (prompt or "").strip().lower()
    if not text:
        return Route("inspection", False, False, "empty prompt defaults to inspect", ("pods.md",))

    if _has(text, _MUTATE) and not _has(text, ("prepare", "recommend", "which", "should i")):
        return Route(
            "lifecycle_mutate",
            True,
            True,
            "paid or destructive lifecycle change",
            ("pods.md", "cost-governance.md"),
        )
    if _has(text, _TRAIN_EXEC):
        return Route(
            "training_execute",
            True,
            True,
            "training launch requires approved manifest or full lane",
            ("training.md", "cost-governance.md"),
        )
    if _has(text, _TRAIN_PREP) or (
        "train" in text and not _has(text, ("which gpu", "what gpu"))
    ):
        return Route(
            "training_prepare",
            False,
            False,
            "prepare a training manifest; do not spend",
            ("training.md", "gpu-selection.md"),
        )
    if _has(text, _GPU):
        return Route(
            "gpu_selection",
            False,
            False,
            "live availability and pricing before spend",
            ("gpu-selection.md", "training.md"),
        )
    if _has(text, _COST):
        return Route("cost", False, False, "billing and cost inspection", ("cost-governance.md",))
    if _has(text, _LOGS):
        return Route("logs", False, False, "capped log and diagnostics", ("logs.md",))
    if _has(text, _SERVERLESS):
        return Route("serverless", False, False, "serverless inspection", ("serverless.md",))
    if _has(text, _STORAGE):
        return Route("storage", False, False, "storage and checkpoint inspection", ("storage.md",))
    if _has(text, _NET):
        return Route("networking", False, False, "reachability and SSH", ("networking.md",))
    if _has(text, _INSPECT) or "pod" in text:
        return Route("inspection", False, False, "read-only pod inspection", ("pods.md",))
    return Route("inspection", False, False, "default observe lane", ("architecture.md",))
