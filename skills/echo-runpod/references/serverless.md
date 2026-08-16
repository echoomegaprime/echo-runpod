# Serverless

Distinct from pods. Endpoints bill by worker time and min workers.

## Inspect (read)

list / get endpoint · health · list / get job · stream job (capped)

## Mutations (gated)

create endpoint · scale (especially raising min workers) · cancel job

## Concepts

- `run` vs `runsync`
- worker min/max and GPU pools
- model cache
- public endpoints
- Hub deployments
- retry / cancel / health / autoscaling

Do not raise `workersMin` without approval. Idle min workers are paid resources.
