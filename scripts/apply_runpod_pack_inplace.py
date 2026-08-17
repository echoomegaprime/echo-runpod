#!/usr/bin/env python3
"""In-place CAS patcher: register /oauth-mcp-runpod-v1 on the live OAuth MCP pack.

Safe to run on HAMMER next to echo_oauth_mcp_pack.py. Verifies sha256, applies
one unique replacement per block, refuses to continue if a block is missing or
matches more than once. Does not advertise echo.write. Does not touch 8787/8798.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# On HAMMER this script lives next to the pack; in the repo it lives under scripts/.
CANDIDATES = [
    HERE,
    HERE.parent,
    Path(r"C:\ECHO_OMEGA_PRIME\GROK_BRIDGE"),
]
PACK_NAME = "echo_oauth_mcp_pack.py"
PACK_SHA = "ec4b6b0aa03350c8be315f723697a3d39070d8dd1df2df66e99c55414dd1d953"

PACK_BLOCKS = [
    (
        "pack-import",
        "from sg_subject_proxy import SG_PREFIX, SubjectShadowGlassProxy\n",
        "from sg_subject_proxy import SG_PREFIX, SubjectShadowGlassProxy\n"
        "from echo_runpod_edge import (\n"
        "    configure_pack as configure_runpod_pack,\n"
        "    execute as execute_runpod,\n"
        "    tool_definition as runpod_tool_definition,\n"
        ")\n",
    ),
    (
        "pack-configure",
        "configure_node_filesystem_pack(PACK, TOOL_REQUIRED_SCOPES, MUTATING_TOOLS)\n"
        "ALL_PACK_SCOPES[:] = sorted({scope for metadata in PACK.values() for scope in metadata[\"scopes\"]})\n",
        "configure_node_filesystem_pack(PACK, TOOL_REQUIRED_SCOPES, MUTATING_TOOLS)\n"
        "configure_runpod_pack(PACK, TOOL_REQUIRED_SCOPES, MUTATING_TOOLS, PACK_PATHS)\n"
        "ALL_PACK_SCOPES[:] = sorted({scope for metadata in PACK.values() for scope in metadata[\"scopes\"]})\n",
    ),
    (
        "pack-tool-def",
        "    node_filesystem_definition = node_filesystem_tool_definition(name)\n"
        "    if node_filesystem_definition is not None:\n"
        "        return node_filesystem_definition\n",
        "    node_filesystem_definition = node_filesystem_tool_definition(name)\n"
        "    if node_filesystem_definition is not None:\n"
        "        return node_filesystem_definition\n"
        "    runpod_definition = runpod_tool_definition(name)\n"
        "    if runpod_definition is not None:\n"
        "        return runpod_definition\n",
    ),
    (
        "pack-execute",
        "    if mutating and confirm != \"EXECUTE\":\n"
        "        return {\"error\": \"mutating_ops_require_confirm_EXECUTE\"}\n\n"
        "    if name == \"nexus_dashboard\":\n",
        "    if mutating and confirm != \"EXECUTE\":\n"
        "        return {\"error\": \"mutating_ops_require_confirm_EXECUTE\"}\n\n"
        "    if name.startswith(\"runpod_\"):\n"
        "        return execute_runpod(name, args)\n\n"
        "    if name == \"nexus_dashboard\":\n",
    ),
    (
        "pack-modules",
        "\"modules\": [\"registry\", \"jobs\", \"autonomy\", \"grok-build\", \"qcoder\", \"fleet\", \"memory\", \"arcanum\", \"kf\", \"github\", \"security\", \"shadowglass\"],\n",
        "\"modules\": [\"registry\", \"jobs\", \"autonomy\", \"grok-build\", \"qcoder\", \"fleet\", \"memory\", \"arcanum\", \"kf\", \"github\", \"security\", \"shadowglass\", \"runpod\"],\n",
    ),
]


def _find_pack() -> Path:
    for root in CANDIDATES:
        candidate = root / PACK_NAME
        if candidate.is_file():
            return candidate
    raise SystemExit(f"missing {PACK_NAME} in {CANDIDATES}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _replace(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path.name}: block {label} matched {count} times")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("patched", path.name, label)


def main() -> None:
    pack = _find_pack()
    digest = _sha256(pack)
    if digest != PACK_SHA:
        raise SystemExit(f"pack sha256 mismatch: {digest}")
    sidecar = pack.parent / "echo_runpod_edge.py"
    if not sidecar.is_file():
        raise SystemExit(f"missing sidecar {sidecar}")
    for label, old, new in PACK_BLOCKS:
        _replace(pack, old, new, label)
    print("ok", "pack", _sha256(pack), "sidecar", _sha256(sidecar))


if __name__ == "__main__":
    sys.exit(main())
