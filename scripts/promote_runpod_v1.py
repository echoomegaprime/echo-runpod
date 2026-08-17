#!/usr/bin/env python3
"""Promote /oauth-mcp-runpod-v1 on the live GROK_BRIDGE edge.

Idempotent. Safe re-run:
  1. copies echo_runpod_edge.py next to echo_oauth_mcp_pack.py
  2. CAS-patches the pack (same blocks as apply_runpod_pack_inplace.py)
  3. adds `runpod` to the cloudflared oauth-mcp-*-v1 regex
  4. compiles the pack
  5. restarts EchoOAuthMCP + GrokMCP-Cloudflared
  6. probes local 8796 and public HTTPS

Does not invent echo.write. Does not touch 8787/8798. Does not start paid pods.
"""

from __future__ import annotations

import hashlib
import json
import py_compile
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from apply_runpod_pack_inplace import PACK_BLOCKS, PACK_NAME, _replace, _sha256

HERE = Path(__file__).resolve().parent
PACK_CANDIDATES = [
    Path(r"C:\ECHO_OMEGA_PRIME\GROK_BRIDGE") / PACK_NAME,
    HERE.parent / PACK_NAME,
]
SIDECAR_SRC = HERE / "echo_runpod_edge.py"
CFG = Path(r"C:\Users\bobmc\.cloudflared\config.yml")
OLD_REGEX = (
    r"path: ^/oauth-mcp-(nexus|grok|fleet|arcanum|kf|github|shadowglass|qcoder|ops|pentest|certforge)-v1(/.*)?$"
)
NEW_REGEX = (
    r"path: ^/oauth-mcp-(nexus|grok|fleet|arcanum|kf|github|shadowglass|qcoder|ops|pentest|certforge|runpod)-v1(/.*)?$"
)


def _find_pack() -> Path:
    for candidate in PACK_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise SystemExit(f"missing {PACK_NAME} in {PACK_CANDIDATES}")


def _patch_tunnel(cfg: Path) -> str:
    if not cfg.is_file():
        return "cloudflared config missing — skipped"
    text = cfg.read_text(encoding="utf-8")
    if "runpod" in text and "oauth-mcp-" in text and "|runpod)" in text.replace(" ", ""):
        return "tunnel regex already includes runpod"
    if OLD_REGEX not in text:
        if "|runpod)-v1" in text or "|runpod|" in text:
            return "tunnel regex already includes runpod"
        raise SystemExit("cloudflared regex block not found — refuse to patch")
    bak = cfg.with_suffix(cfg.suffix + f".bak_runpod_{int(time.time())}")
    shutil.copy2(cfg, bak)
    cfg.write_text(text.replace(OLD_REGEX, NEW_REGEX, 1), encoding="ascii", newline="\n")
    return f"tunnel regex updated (backup {bak.name})"


def _restart(name: str) -> str:
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"Restart-Service {name} -Force"],
        check=False,
        capture_output=True,
        text=True,
    )
    return f"{name} exit={completed.returncode}"


def _probe(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "echo-runpod-promote/1.1"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return {"url": url, "status": resp.status, "ok": 200 <= resp.status < 300}
    except Exception as exc:  # noqa: BLE001 — probe must not crash promote
        status = getattr(exc, "code", None)
        return {"url": url, "status": status, "ok": False, "error": str(exc)}


def main() -> int:
    pack = _find_pack()
    if not SIDECAR_SRC.is_file():
        raise SystemExit(f"missing sidecar source {SIDECAR_SRC}")
    sidecar = pack.parent / "echo_runpod_edge.py"
    shutil.copy2(SIDECAR_SRC, sidecar)
    print("sidecar", sidecar, _sha256(sidecar))

    before = _sha256(pack)
    src = pack.read_text(encoding="utf-8")
    already = "from echo_runpod_edge import" in src and "configure_runpod_pack" in src
    if already:
        print("pack already wired")
    else:
        bak = pack.with_suffix(pack.suffix + f".bak_runpod_{int(time.time())}")
        shutil.copy2(pack, bak)
        print("pack backup", bak)
        for label, old, new in PACK_BLOCKS:
            _replace(pack, old, new, label)
    py_compile.compile(str(pack), doraise=True)
    print("pack syntax ok", "sha", _sha256(pack), "was", before)

    print(_patch_tunnel(CFG))
    print(_restart("EchoOAuthMCP"))
    time.sleep(2)
    print(_restart("GrokMCP-Cloudflared"))
    time.sleep(4)

    probes = [
        _probe("http://127.0.0.1:8796/oauth-mcp-runpod-v1"),
        _probe("https://mcp.echo-op.com/oauth-mcp-runpod-v1"),
        _probe("https://mcp.echo-op.com/.well-known/oauth-protected-resource/oauth-mcp-runpod-v1"),
    ]
    print(json.dumps({"probes": probes}, indent=2))
    public = next(p for p in probes if p["url"].startswith("https://mcp.echo-op.com/oauth-mcp-runpod-v1"))
    return 0 if public.get("status") in {200, 401} else 4


if __name__ == "__main__":
    raise SystemExit(main())
