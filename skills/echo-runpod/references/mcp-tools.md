# MCP tool annotations

Truthful hints. Never mislabel a mutation as read-only.

| Class | readOnlyHint | destructiveHint | idempotentHint | openWorldHint |
|---|---|---|---|---|
| READ | true | false | false | true |
| start/stop/terminate | false | terminate=true | true (same target) | true |
| create/launch/scale | false | false | false | true |

`openWorldHint: true` because RunPod is an external account.

Nexus mutations still require `confirm: EXECUTE`.

## ChatGPT resource

- path: `/oauth-mcp-runpod-v1`
- url: `https://mcp.echo-op.com/oauth-mcp-runpod-v1`
- scopes: `echo.runpod.read` `echo.runpod.prepare` `echo.runpod.control` `echo.runpod.spend`
- never: `echo.write`

Python catalog: `echo_runpod.mcp.resource_catalog()`.
Echo Nexus registers the same id in `src/lib/oauth-mcp-pack/catalog.ts`.
