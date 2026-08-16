# Pods

## Inspect first

```text
python -m echo_runpod.operator live runpod_list_pods
python -m echo_runpod.operator live runpod_get_pod --pod-id <id>
```

Official MCP: `list-pods`, `get-pod`. REST: `GET /v1/pods`, `GET /v1/pods/{id}`.

Fields to record: id, name, desiredStatus, GPU, data center, runtime, ports, volumeInGb, image, workload_id if tagged.

## Lifecycle

| Action | Spend | Storage | Reversible |
|---|---|---|---|
| list / get | no | n/a | n/a |
| start | yes (compute) | kept | stop |
| stop | compute off | **may still bill** | start |
| restart | yes | kept | yes |
| terminate / delete | compute off | **destroyed** | no |

Stop is the safe default when work might resume. Terminate only after artifacts/checkpoints are off host-local disk.

## Mutations

Require policy allow + `confirm: EXECUTE`. Official MCP: `create-pod`, `start-pod`, `stop-pod`, `restart-pod`, `update-pod`, `delete-pod`.

Default image when unspecified: `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404`.

## Isolation

Refuse to attach a pod whose `workload_id`, `project`, dataset SHA, or model does not match the request. Landman ≠ Prometheus.
