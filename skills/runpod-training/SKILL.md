---
name: runpod-training
description: >
  Thin router into Echo RunPod for GPU selection and training preparation.
  Use for RunPod training, QLoRA, LoRA, adapter, 27B GPU pick.
  Does not launch paid jobs without an approved manifest or full lane.
---

# RunPod Training (router)

Thin router. Canonical training manifests, isolation, and cost gates live in `echo-runpod`.

Preserved selection policy:

1. Estimate VRAM from model, sequence, batch, optimizer.
2. Pick the smallest GPU that fits with headroom.
3. Prefer a 48 GB class card when the job would otherwise be memory-bound.
4. Query **live** availability and price before spending. Do not treat remembered rates as truth.

Preserved useful classes: A40, RTX A6000, RTX 6000 Ada, L40S. Cheaper cards only after the recipe still fits.

## Workflow

1. Confirm dataset size, SHA, and adapter recipe.
2. `python -m echo_runpod.operator route "Which GPU should I use to QLoRA a 27B model on RunPod?"`
3. Prepare a full training manifest. Execution waits for approval unless a full lane exists.
4. Never mix Landman and Prometheus pods or datasets.

Read `../echo-runpod/SKILL.md` and `../echo-runpod/references/training.md`.
