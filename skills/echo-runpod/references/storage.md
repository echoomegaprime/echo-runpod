# Storage

| Kind | Survives stop | Survives terminate | Notes |
|---|---|---|---|
| container disk | no | no | ephemeral |
| pod volume | yes | no | host-local to the pod record |
| network volume | yes | yes (until deleted) | shareable |

Never terminate a training pod before required artifacts/checkpoints are on a network volume or exported (S3-compatible / Echo artifact dest).

Stopped pods with `volumeInGb > 0` still appear in `idle_paid_resources`.

Create-volume is approval-gated.
