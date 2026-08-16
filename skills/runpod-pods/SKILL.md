---
name: runpod-pods
description: >
  Thin router into Echo RunPod for pod list/stop/start/terminate.
  Use for RunPod pods, pod list, stop pod, start pod, delete pod.
  Mutations stay approval-gated. Prefer /echo-runpod for the full suite.
---

# RunPod Pods (router)

This skill is a **thin router**. Canonical policy, Vault, cost, and isolation live in `echo-runpod`.

Preserved from the previous Codex skill:

- Treat the API key as `Authorization: Bearer <key>` (resolved at runtime, never stored here).
- List/find before any destructive action.
- **Stop is not delete.** A stopped pod can still incur storage charges.
- Terminate only when the pod and its host-local storage are no longer needed.

## Workflow

1. Route through Echo RunPod inspection lane.
2. `python -m echo_runpod.operator live runpod_list_pods`
3. Confirm pod id and account.
4. Stop first if you only need to halt compute (approval + `confirm: EXECUTE`).
5. Terminate only after artifacts are off host-local storage.

Do not create a second client. Read `../echo-runpod/SKILL.md` and `references/runpod-pods.md`.
