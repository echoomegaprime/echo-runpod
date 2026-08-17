---
name: echo-runpod
description: >-
  Echo RunPod for ChatGPT. Inspect pods, GPUs, pricing, billing, storage,
  logs, and training jobs through the governed MCP resource
  https://mcp.echo-op.com/oauth-mcp-runpod-v1. Mutations stay approval-gated
  behind confirm EXECUTE. Never request echo.write. No API keys in this file.
---

# Echo RunPod (ChatGPT)

Install the custom MCP connector:

`https://mcp.echo-op.com/oauth-mcp-runpod-v1`

Description to paste:

Governed RunPod control plane for Echo Omega Prime. Inspect pods, GPUs, pricing, billing, storage, logs, and training jobs; prepare and execute approval-gated RunPod operations through Echo Nexus.

Live OAuth contract (authorization-server `scopes_supported`, 2026-08-17). Request **only** these:

- `echo.search` — discovery / live-verify
- `echo.fetch` — fetch a specific resource
- `echo.invoke.read` — read-only RunPod tools
- `echo.sdk.invoke` — governed prepare + mutation invocation

Do **not** request:

- `echo.write` — not issued by the live authorization server
- `echo.read` — not issued (use `echo.invoke.read`)
- `echo.runpod.read` / `echo.runpod.prepare` / `echo.runpod.control` / `echo.runpod.spend` — invented names; they cause `invalid_scope`

Default: observe. Read tools run when the token has `echo.invoke.read` or `echo.fetch`. Spend/destructive tools require `echo.sdk.invoke` **and** `confirm: EXECUTE` **and** an approved manifest or bounded full lane. Mutation tools stay mutating (`readOnlyHint: false`). Do not claim mutation tools are loaded until ChatGPT `tools/list` actually shows them.

| Milestone | State |
|---|---|
| plugin source | this file + echo-runpod pack |
| MCP deployed | `/oauth-mcp-runpod-v1` on Echo Nexus pack edge |
| Echo Nexus registered | catalog + capabilities |
| ChatGPT app registered | host UI — Commander connects the URL above |
| ChatGPT app connected | not claimed by this pack alone |
| ChatGPT read tools loaded | after OAuth; verify `tools/list` |
| ChatGPT mutation tools loaded | only if the host allows custom MCP mutations |

Secrets stay at `vault://runpod/api-key` (env fallback `RUNPOD_API_KEY`) on the MCP host. Never paste keys into ChatGPT.
