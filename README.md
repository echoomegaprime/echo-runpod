# Echo RunPod

Governed RunPod control plane for ECHO OMEGA PRIME. Version **1.1.1**.

One canonical policy source. Thin entry points for Grok, Codex, Echo agents, and ChatGPT-via-Nexus.

## Default

Observe and prepare. Do not spend unless the Commander approved a manifest or a bounded full lane is in force. Echo Nexus mutations require `confirm: EXECUTE`.

## ChatGPT / MCP

Dedicated resource (do **not** request `echo.write`):

- https://mcp.echo-op.com/oauth-mcp-runpod-v1
- live scopes: `echo.search` `echo.fetch` `echo.invoke.read` `echo.sdk.invoke`
- never: `echo.write`, `echo.read`, `echo.runpod.*`
- secret: `vault://runpod/api-key` then `RUNPOD_API_KEY`

`echo.sdk.invoke` keeps mutation tools mutating (`readOnlyHint: false`). They still require `confirm: EXECUTE` plus an approved manifest or bounded full lane.

## Install

See `skills/echo-runpod/references/install-verify.md`.

## Test

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```

## Upstream

- runpod/runpod-plugins-official v1.1.2 `b669407688056642d09d2049df5432cb78ae33f0`
- runpod/runpod-mcp `51d6fd9a0ff16a4eeb7d508972aeb5502f514939`

## Secrets

`vault://runpod/api-key` then `RUNPOD_API_KEY`. Never commit keys.
