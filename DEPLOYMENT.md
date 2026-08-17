# Echo RunPod deployment

Head: `64253d95c809e5fe5aeb947cce74a81875959766` on `main`.
Started from: `9fe155fc87407771aea681251a69430a4f1911d4`.

## ChatGPT / MCP

- Resource: https://mcp.echo-op.com/oauth-mcp-runpod-v1
- Well-known: https://mcp.echo-op.com/.well-known/oauth-protected-resource/oauth-mcp-runpod-v1
- Transport: OAuth 2.1 PKCE + DCR, JSON-RPC `/mcp`
- Scopes: `echo.search` `echo.fetch` `echo.invoke.read` `echo.sdk.invoke`
- Never: `echo.write`, invented `echo.runpod.*`
- Secret: `vault://runpod/api-key` then `RUNPOD_API_KEY`

Unauthenticated `initialize` / `tools/list` must be HTTP 401.

## Tests

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```

83 passed, 0 failed, 0 skipped (2026-08-17).

## Promote (Hammer)

`scripts/promote_runpod_v1.py` copies `echo_runpod_edge.py` next to `echo_oauth_mcp_pack.py`, CAS-patches the pack, and requires `runpod` in the Cloudflared `oauth-mcp-*-v1` regex. Reload `GrokMCP-Cloudflared` if the public resource 502s while well-known is 200.
