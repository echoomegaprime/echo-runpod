# Networking

A pod `desiredStatus=RUNNING` does not prove the service is reachable.

Verify:

- SSH host/port and key
- public IP if requested
- port mappings
- HTTP proxy URL (`*.proxy.runpod.net`)
- TCP access
- process bind address — services must listen on `0.0.0.0`, not `127.0.0.1`

Firewall / auth failures are diagnostics, not a reason to recreate a paid pod without approval.
