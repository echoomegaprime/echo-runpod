# MCP tool annotations

Truthful hints. Never mislabel a mutation as read-only.

| Class | readOnlyHint | destructiveHint | idempotentHint | openWorldHint |
|---|---|---|---|---|
| READ | true | false | false | true |
| start/stop/terminate | false | terminate=true | true (same target) | true |
| create/launch/scale | false | false | false | true |

`openWorldHint: true` because RunPod is an external account.

Nexus mutations still require `confirm: EXECUTE`.
