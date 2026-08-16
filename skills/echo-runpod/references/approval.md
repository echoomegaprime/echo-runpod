# Approval and full lane

## Classes

- **READ** — allowed without extra approval. `readOnlyHint: true`.
- **APPROVAL** — needs an approved execution manifest or a bounded full lane, plus `confirm: EXECUTE`.
- **DESTRUCTIVE** — terminate/delete. Never labeled read-only.

Mutations are never annotated `readOnlyHint: true`.

## Approval-gated actions

create / start / stop / restart / terminate pod · resize · change GPU · create volume · launch / resume training · create / scale endpoint

## Full lane required fields

`workload_id` · `allowed_gpu_classes` · `max_gpu_count` · `max_hourly_rate` · `max_total_spend` · `max_runtime` · `allowed_storage` · `allowed_pod_count` · `allowed_endpoint_count` · `dataset_identity` · `model_identity` · `artifact_destination` · `termination_policy`

Inside those bounds the operator may select an allowed GPU, create the pod, verify startup/SSH, upload data/trainer, launch, monitor, recover transients, resume an approved checkpoint, upload and verify the adapter, write receipts, and terminate the paid pod.

It may not increase budget, pick an unapproved or more expensive GPU class, raise GPU count, change workload/dataset/model, create unrelated infra, or leave an idle paid pod running.

## Confirm token

Echo Nexus mutating ops require `confirm: "EXECUTE"`. Preserve it even when a full lane exists.
