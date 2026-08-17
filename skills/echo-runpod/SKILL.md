---
name: echo-runpod
description: >
  Governed Echo RunPod control plane for pods, GPU selection, training
  preparation, serverless, storage, networking, logs, billing, and
  approval-gated lifecycle. Use for RunPod, runpod, pods, GPU catalog,
  QLoRA, LoRA, adapter training, endpoints, volumes, billing, checkpoints,
  Landman vs Prometheus isolation, or /echo-runpod. Default is observe.
  Mutations require confirm: EXECUTE or a bounded full lane.
---

# Echo RunPod

Canonical RunPod skill for Grok, Codex, Echo agents, and ChatGPT-via-Nexus.

Control plane: **ChatGPT / Grok / Codex → this skill → Echo Nexus → Vault + policy + official RunPod MCP/REST + cost governor + receipts.**

Do not invent a second RunPod control plane. Do not route through Echo Unified RW SDK.

ChatGPT-installable MCP resource (never request `echo.write`):

- `https://mcp.echo-op.com/oauth-mcp-runpod-v1`
- live scopes: `echo.search` `echo.fetch` `echo.invoke.read` `echo.sdk.invoke`
- never: `echo.write`, `echo.read`, invented `echo.runpod.*` names


## Default mode — observe + prepare

Allowed without extra approval:

- list/get pods, endpoints, jobs, volumes
- GPU types, availability, live pricing
- billing / cost inspect
- capped logs
- prepare training manifests
- recommend GPUs
- checkpoint / artifact inspect

Not allowed without an approved execution manifest or a bounded full lane:

- create / start / stop / restart / terminate pod
- resize / change GPU
- create volume
- launch / resume training
- create or scale paid serverless

Echo Nexus mutations still require `confirm: "EXECUTE"`.

## Route first

| Prompt shape | Lane | Spend? |
|---|---|---|
| Show my RunPod pods | inspection | no |
| Which GPU should I use to QLoRA a 27B? | gpu_selection | no — live price first |
| Train this adapter | training_prepare | no — manifest only |
| Launch / start training | training_execute | yes — gated |
| Create / start / terminate pod | lifecycle_mutate | yes — gated |

```text
python -m echo_runpod.operator route "Show my RunPod pods."
python -m echo_runpod.operator live runpod_list_pods
python -m echo_runpod.operator prepare <manifest.json>
```

## Hard rules

1. Secrets resolve at runtime via `vault://runpod/api-key` then `RUNPOD_API_KEY`. Never write keys into skills, logs, receipts, git, or prompts.
2. Official backends only: RunPod MCP `https://mcp.getrunpod.io/` and REST `https://rest.runpod.io/v1`. Upstream pins: plugins official `b669407688056642d09d2049df5432cb78ae33f0` (v1.1.2), MCP `51d6fd9a0ff16a4eeb7d508972aeb5502f514939`.
3. STOP ≠ DELETE. Stopped pods can still bill storage.
4. RUNNING ≠ reachable. Verify SSH / proxy / service bind.
5. Never reuse another project's pod. Landman and Prometheus stay isolated.
6. Never hard-code prices. Query live before spend.
7. Never terminate a training pod before checkpoints/artifacts are off host-local disk.
8. Do not add `echo.runpod.*` through the closed SDK allowlist. Execution path is Nexus `node_execute` + this policy.

## References

- [architecture.md](references/architecture.md)
- [auth.md](references/auth.md)
- [official-runpod.md](references/official-runpod.md)
- [approval.md](references/approval.md)
- [pods.md](references/pods.md)
- [gpu-selection.md](references/gpu-selection.md)
- [training.md](references/training.md)
- [serverless.md](references/serverless.md)
- [storage.md](references/storage.md)
- [networking.md](references/networking.md)
- [jobs.md](references/jobs.md)
- [logs.md](references/logs.md)
- [cost-governance.md](references/cost-governance.md)
- [troubleshooting.md](references/troubleshooting.md)
- [grok-operator.md](references/grok-operator.md)
- [api-map.md](references/api-map.md)
- [mcp-tools.md](references/mcp-tools.md)
- [runpodctl.md](references/runpodctl.md)
- [official-docs-index.md](references/official-docs-index.md)
- [landman-teacher.md](references/landman-teacher.md)
- [install-verify.md](references/install-verify.md)
