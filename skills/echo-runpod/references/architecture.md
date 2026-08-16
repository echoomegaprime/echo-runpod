# Architecture

```
ChatGPT / Grok / Codex / Echo agents
        |
        v
Echo RunPod Skill  (this pack — one policy source)
        |
        v
Echo Nexus  (https://mcp.echo-op.com/oauth-mcp-nexus-v1)
        |
        +-- Vault Broker     vault://runpod/api-key
        +-- RunPod policy    READ / APPROVAL / DESTRUCTIVE / FULL LANE
        +-- Official RunPod  MCP https://mcp.getrunpod.io/  REST https://rest.runpod.io/v1
        +-- Cost governor    live hourly + budget + idle paid resources
        +-- Isolation        workload_id + project + dataset sha + model
        +-- Audit receipts   hashed, redacted
```

## Why not Unified RW SDK

The live SDK allowlist is closed. `sdk_invoke_allowed` for `echo.runpod.*` returns `sdk_capability_not_allowlisted`. Do not fight it. Capability records live in `nexus/capabilities.json` for a later pack load. Runtime path is Nexus `node_execute` + this package.

## Official vs Echo

| Layer | Owner | Role |
|---|---|---|
| Official MCP / REST / runpodctl | RunPod | pods, endpoints, jobs, templates, volumes, billing, logs, Hub |
| Echo policy | Echo | approval, full-lane bounds, isolation, redaction |
| Echo Vault | ShadowGlass / broker | runtime key only |
| Echo receipts | this pack | hashed evidence |

## Upstream pins

- runpod/runpod-plugins-official v1.1.2 commit `b669407688056642d09d2049df5432cb78ae33f0`
- runpod/runpod-mcp commit `51d6fd9a0ff16a4eeb7d508972aeb5502f514939`
- Default official image: `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404`

## OAuth / scopes

Nexus umbrella scopes in force include `echo.nexus.read`, `echo.nexus.control`, `echo.nexus.fs.read`, `echo.nexus.fs.write`, `echo.grok.sdk.invoke`. Do not add a fabricated `echo.write`. Mutations stay mutations and still require `confirm: EXECUTE`.
