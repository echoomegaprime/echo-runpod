# Cost governance

Integrate with any existing Capacity Governor; do not replace it. This pack adds RunPod-specific checks.

Tracked: live hourly rate, runtime, accumulated, projected total, storage when available, remaining budget, idle paid resources.

Bounds: `max_hourly_rate` · `max_total_budget` · `max_runtime` · `approved_gpu_classes` · `approved_gpu_count` · `approved_storage` · `approved_workload`.

Never silently exceed a bound. Live pricing is required before spend.

Idle detector flags:

- RUNNING pods with no `workload_id`
- EXITED / stopped pods that still have volume storage
