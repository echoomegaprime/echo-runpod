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

Scopes (never `echo.write`):

- `echo.runpod.read`
- `echo.runpod.prepare`
- `echo.runpod.control`
- `echo.runpod.spend`

Default: observe. Read tools run when policy allows. Spend/destructive tools require `confirm: EXECUTE`.

| Milestone | State |
|---|---|
| plugin source | this file + echo-runpod pack |
| MCP deployed | `/oauth-mcp-runpod-v1` on Echo Nexus pack edge |
| Echo Nexus registered | catalog + capabilities |
| ChatGPT app registered | host UI — Commander connects the URL above |
| ChatGPT app connected | not claimed by this pack alone |
| ChatGPT read tools loaded | after OAuth to the resource |
| ChatGPT mutation tools loaded | after OAuth; still approval-gated |

Secrets stay at `vault://runpod/api-key` (env fallback `RUNPOD_API_KEY`) on the MCP host. Never paste keys into ChatGPT.
