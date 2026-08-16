---
name: echo-runpod
description: >
  Echo RunPod for ChatGPT-via-Nexus. Observe RunPod pods, GPUs, billing,
  and prepare training manifests. Mutations stay approval-gated behind
  Echo Nexus confirm EXECUTE. No API keys in this file.
---

# Echo RunPod (ChatGPT source package)

Source-complete ChatGPT skill. This is **not** a native ChatGPT app registration.

Status to report honestly:

| Milestone | State |
|---|---|
| plugin source | this file + echo-runpod pack |
| MCP deployed | official RunPod MCP exists; Echo wrap is policy+REST via Nexus |
| Echo Nexus registered | capability records in nexus/capabilities.json; SDK allowlist closed |
| ChatGPT app registered | pending host UI / connector |
| ChatGPT app connected | not claimed |
| ChatGPT read tools loaded | not claimed |
| ChatGPT mutation tools loaded | not claimed |

Use Echo Nexus tools (`node_execute`, `node_file_*`) plus this pack. Never request `echo.write`. Mutations remain mutations.

Default: observe. Do not spend.
