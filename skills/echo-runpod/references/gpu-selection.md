# GPU selection

Start from the job, not the badge.

1. Estimate VRAM from model size, quantization, context, batch, optimizer.
2. Query **live** availability and hourly rate. Never treat a remembered price as truth.
3. Pick the cheapest class that fits with headroom and is inside the approved allowlist.
4. Refuse prestige GPUs (H100/H200/B200) unless the recipe needs them and the lane allows them.

## Useful classes (not a price table)

- RTX 4090 — cheaper 24 GB class
- A40 / RTX A6000 — 48 GB workhorses
- RTX 6000 Ada — newer 48 GB
- L40S — high throughput 48 GB
- A100 / H100 / H200 / B200 — only when VRAM or interconnect actually requires them

## 27B / 32B QLoRA starting point

A 48 GB class card (A40, A6000, RTX 6000 Ada, L40S) is the usual first live query. Confirm current availability and rate before recommending spend.

```text
python -m echo_runpod.operator live runpod_list_gpu_types
python -m echo_runpod.operator cost --live-hourly <rate> --hours <h> --max-hourly <cap> --max-budget <cap> --gpu "RTX 6000 Ada" --allowed-gpu "RTX 6000 Ada,A40,L40S"
```
