# Troubleshooting

| Symptom | First check |
|---|---|
| 401 / 403 | Vault/env present? Account match? Do not print the key. |
| pod not found | list pods; wrong account or already terminated |
| RUNNING but dead | networking.md — bind, proxy, SSH |
| CUDA OOM | smaller batch / 48 GB+ class / confirm live VRAM |
| NaN loss | LR, bad batch, mixed precision; do not keep burning hours |
| stalled step | disk, data loader, NCCL, preemption |
| unexpected bill | idle_paid_resources; stopped ≠ free |
| SDK allowlist miss | expected — use this pack + official MCP/REST |
