# Logs and diagnostics

Cap and summarize. Never dump unbounded logs into model context.

Cover: pod logs, worker logs, training logs, CUDA / OOM / NCCL, disk full, SSH/connect, container start, checkpoint fail, dependency fail, stalled epoch/step, NaN loss, crash/restart, API rate limits.

Official MCP: `stream-pod-logs` (v2). Echo tool: `runpod_stream_pod_logs` (read-only).
