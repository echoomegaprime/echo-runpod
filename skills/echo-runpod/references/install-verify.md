# Install and verify

Canonical root: `C:\ECHO_OMEGA_PRIME\RUNPOD\`

Loader copies:

- `C:\Users\bobmc\.codex\skills\echo-runpod\`
- `C:\Users\bobmc\.grok\skills\echo-runpod\`
- `C:\ECHO_OMEGA_PRIME\.agents\skills\echo-runpod\`
- `C:\ECHO_OMEGA_PRIME\CHATGPT_SKILLS\ECHO_CORE_V1\echo-runpod\`
- Grok agent: `C:\Users\bobmc\.grok\agents\echo-runpod-operator.md`
- Thin routers replace `runpod-pods` and `runpod-training` under Codex skills

Verify each installed `SKILL.md`:

1. Read back via Nexus `node_file_read`
2. SHA-256
3. YAML frontmatter present
4. references exist
5. no secrets
6. loader directory lists the skill

Tests:

```text
cd <pack> && PYTHONPATH=. python -m unittest discover -s tests -v
```
