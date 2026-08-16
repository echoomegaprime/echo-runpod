# Official RunPod foundation

Authoritative upstream, not a fork.

## Sources reviewed

- https://docs.runpod.io/
- https://github.com/runpod/runpod-plugins-official  v1.1.2  `b669407688056642d09d2049df5432cb78ae33f0`
- https://github.com/runpod/runpod-mcp  `51d6fd9a0ff16a4eeb7d508972aeb5502f514939`

## Official plugin areas (reference only)

`runpod` · `runpod-mcp` · `runpodctl` · `runpod-usage` · `flash` · `companion-clis`

Echo does not clone those implementations. Echo wraps official behavior with Vault, approval, cost ceilings, isolation, receipts.

## Official MCP pod tools

| Official tool | Echo tool | Class |
|---|---|---|
| list-pods | runpod_list_pods | read |
| get-pod | runpod_get_pod | read |
| stream-pod-logs | runpod_stream_pod_logs | read |
| create-pod | runpod_create_pod | approval |
| update-pod | runpod_resize_pod | approval |
| start-pod | runpod_start_pod | approval |
| stop-pod | runpod_stop_pod | approval |
| restart-pod | runpod_restart_pod | approval (v2) |
| delete-pod | runpod_terminate_pod | destructive |

Official MCP also covers endpoints, jobs, templates, network volumes, registries, catalog, billing, logs, Hub, public endpoints. Prefer those tools over custom REST when they exist.

## REST used when MCP is not in-process

- `GET https://rest.runpod.io/v1/pods`
- `GET https://rest.runpod.io/v1/pods/{id}`
- `GET https://rest.runpod.io/v1/billing/pods`
- GraphQL `gpuTypes { id displayName memoryInGb secureCloud communityCloud }`
