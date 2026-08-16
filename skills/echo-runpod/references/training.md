# Training

Prepare first. Launch only with an approved manifest or a full lane.

## Required manifest fields

workload_id · model · model_revision · dataset · dataset_sha256 · dataset_rows · evaluation_set · trainer · trainer_sha256 · gpu_type · gpu_count · minimum_vram · maximum_hourly_price · maximum_total_budget · maximum_runtime · container_image · storage_size · volume_path · checkpoint_path · artifact_destination · termination_policy · project · owner

```text
python -m echo_runpod.operator prepare <manifest.json>
```

Status `prepared` means execution still waits for approval unless a full lane is in force.

## Methods

LoRA / QLoRA / SFT / adapter training. Checkpoints must land on the volume path, not disposable container disk. Evaluation sets stay frozen and out of the training mix.

## Launch / resume

`runpod_launch_training` and `runpod_resume_training` are approval-gated. Resume only from a checkpoint that belongs to the same workload_id + dataset SHA + model.

## Completion

1. Confirm last checkpoint and final adapter exist on the volume / artifact destination.
2. Verify hashes.
3. Write a redacted receipt.
4. Terminate the paid pod per `termination_policy`. Never leave it idle.
