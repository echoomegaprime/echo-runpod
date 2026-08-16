# Authentication

## Resolution order

1. Vault Broker `vault://runpod/api-key` (server-env only)
2. Process environment `RUNPOD_API_KEY`

Never persist the raw key. `SecretBroker.status()` reports `{source, reference, present}` only.

## Wire format

```
Authorization: Bearer <key>
```

Official REST: `https://rest.runpod.io/v1`
Official GraphQL (GPU catalog): `https://api.runpod.io/graphql`
Official MCP: `https://mcp.getrunpod.io/`

## RunPod CLI

`runpodctl` reads the same account key from its own config. Echo operators must not copy that file into skills or receipts.

## Redaction

`echo_runpod.redaction` strips:

- `Authorization: Bearer …`
- `RUNPOD_API_KEY=…` and JSON `api_key` / `token` / `password` / `secret`
- `RP_…`, `sk-…`, `hf_…`, `ghp_…`, `xai-…`

Apply redaction to logs, exceptions, receipts, tool responses, and Git diffs before they leave process memory.

## Fail closed

If neither Vault nor env can supply a key that looks like a key (≥16 chars), refuse the live call. Do not invent a demo key.
