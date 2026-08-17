# Echo RunPod bundle — 2026-08-17

Governed RunPod pack + operator console + receipts. No secrets.

## Contents

| Path | What |
| --- | --- |
| `echo-runpod/` | Canonical pack (policy, MCP, tests, skills, promote scripts) |
| `operator-console/` | TanStack operator UI source (no `node_modules`) |
| `receipts/` | Test + live MCP evidence (no API keys) |
| `screenshots/` | Fleet / receipts QA shots |

## Repo

- GitHub: https://github.com/echoomegaprime/echo-runpod
- Branch: `main`
- Start: `9fe155fc87407771aea681251a69430a4f1911d4`
- Head: `64253d95c809e5fe5aeb947cce74a81875959766`

## Live MCP (do not request `echo.write`)

- Resource: https://mcp.echo-op.com/oauth-mcp-runpod-v1
- Well-known: https://mcp.echo-op.com/.well-known/oauth-protected-resource/oauth-mcp-runpod-v1
- Scopes: `echo.search` `echo.fetch` `echo.invoke.read` `echo.sdk.invoke`
- Secret: `vault://runpod/api-key` then `RUNPOD_API_KEY`

## Tests

```bash
cd echo-runpod
PYTHONPATH=. python -m unittest discover -s tests -v
```

Expected: 83 passed, 0 failed, 0 skipped.

## Install loaders (Windows / Hammer)

See `echo-runpod/skills/echo-runpod/references/install-verify.md`.

Canonical pack: `C:\ECHO_OMEGA_PRIME\RUNPOD\`
