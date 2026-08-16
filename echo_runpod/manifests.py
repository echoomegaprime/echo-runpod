"""Training manifest schema and validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

REQUIRED_FIELDS = (
    "workload_id",
    "model",
    "model_revision",
    "dataset",
    "dataset_sha256",
    "dataset_rows",
    "evaluation_set",
    "trainer",
    "trainer_sha256",
    "gpu_type",
    "gpu_count",
    "minimum_vram",
    "maximum_hourly_price",
    "maximum_total_budget",
    "maximum_runtime",
    "container_image",
    "storage_size",
    "volume_path",
    "checkpoint_path",
    "artifact_destination",
    "termination_policy",
    "project",
    "owner",
)

SHA256_LEN = 64


@dataclass
class TrainingManifest:
    workload_id: str
    model: str
    model_revision: str
    dataset: str
    dataset_sha256: str
    dataset_rows: int
    evaluation_set: str
    trainer: str
    trainer_sha256: str
    gpu_type: str
    gpu_count: int
    minimum_vram: int
    maximum_hourly_price: float
    maximum_total_budget: float
    maximum_runtime: str
    container_image: str
    storage_size: int
    volume_path: str
    checkpoint_path: str
    artifact_destination: str
    termination_policy: str
    project: str
    owner: str
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        extras = data.pop("extras", {})
        data.update(extras)
        return data


class ManifestError(ValueError):
    pass


def _hex64(name: str, value: Any) -> str:
    text = str(value or "").strip().lower()
    if len(text) != SHA256_LEN or any(c not in "0123456789abcdef" for c in text):
        raise ManifestError(f"{name} must be a 64-char lowercase sha256")
    return text


def validate_manifest(raw: Mapping[str, Any]) -> TrainingManifest:
    missing = [f for f in REQUIRED_FIELDS if f not in raw or raw[f] in (None, "")]
    if missing:
        raise ManifestError(f"training manifest missing fields: {', '.join(missing)}")
    if int(raw["gpu_count"]) < 1:
        raise ManifestError("gpu_count must be >= 1")
    if int(raw["dataset_rows"]) < 1:
        raise ManifestError("dataset_rows must be >= 1")
    if float(raw["maximum_hourly_price"]) <= 0 or float(raw["maximum_total_budget"]) <= 0:
        raise ManifestError("budget fields must be positive")
    extras = {k: v for k, v in raw.items() if k not in REQUIRED_FIELDS}
    return TrainingManifest(
        workload_id=str(raw["workload_id"]),
        model=str(raw["model"]),
        model_revision=str(raw["model_revision"]),
        dataset=str(raw["dataset"]),
        dataset_sha256=_hex64("dataset_sha256", raw["dataset_sha256"]),
        dataset_rows=int(raw["dataset_rows"]),
        evaluation_set=str(raw["evaluation_set"]),
        trainer=str(raw["trainer"]),
        trainer_sha256=_hex64("trainer_sha256", raw["trainer_sha256"]),
        gpu_type=str(raw["gpu_type"]),
        gpu_count=int(raw["gpu_count"]),
        minimum_vram=int(raw["minimum_vram"]),
        maximum_hourly_price=float(raw["maximum_hourly_price"]),
        maximum_total_budget=float(raw["maximum_total_budget"]),
        maximum_runtime=str(raw["maximum_runtime"]),
        container_image=str(raw["container_image"]),
        storage_size=int(raw["storage_size"]),
        volume_path=str(raw["volume_path"]),
        checkpoint_path=str(raw["checkpoint_path"]),
        artifact_destination=str(raw["artifact_destination"]),
        termination_policy=str(raw["termination_policy"]),
        project=str(raw["project"]),
        owner=str(raw["owner"]),
        extras=extras,
    )


def landman_example() -> dict[str, Any]:
    """Isolation test fixture. Not a generic default."""
    return {
        "workload_id": "landman-teacher-v4-exp1",
        "project": "landman",
        "owner": "commander",
        "model": "Qwen/Qwen2.5-32B-Instruct",
        "model_revision": "main",
        "dataset": r"E:\tmp\echo-landman-teacher-v4\forge_exp1_corpus_20260816T180000Z\experimental_corpus.jsonl",
        "dataset_sha256": "3f6b93e80818e670402e75463ec2a5898104af03f4b616e1b8b6dfd8e6766a81",
        "dataset_rows": 5800,
        "evaluation_set": "frozen-eval-not-mixed-into-training",
        "trainer": "echo-landman-qlora",
        "trainer_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "gpu_type": "RTX 6000 Ada",
        "gpu_count": 1,
        "minimum_vram": 48,
        "maximum_hourly_price": 1.50,
        "maximum_total_budget": 40.00,
        "maximum_runtime": "8h",
        "container_image": "runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404",
        "storage_size": 200,
        "volume_path": "/workspace",
        "checkpoint_path": "/workspace/checkpoints/landman",
        "artifact_destination": "echo://artifacts/landman/teacher-v4-exp1",
        "termination_policy": "terminate-after-artifact-verify",
        "notes": "4000 Landman teacher + 1800 title-math; do not mix Prometheus",
    }
