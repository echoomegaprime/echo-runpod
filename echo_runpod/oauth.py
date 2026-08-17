"""Live-approved Echo OAuth scopes for Echo RunPod.

Inspected 2026-08-17 against the live authorization server:

- resource metadata: https://mcp.echo-op.com/.well-known/oauth-protected-resource
- AS metadata: https://mcp.echo-op.com/.well-known/oauth-authorization-server
- path-specific: https://mcp.echo-op.com/.well-known/oauth-protected-resource/oauth-mcp-runpod-v1 (404)

Protected-resource scopes_supported (oauth-mcp-v3):
    echo.search, echo.fetch, echo.invoke.read, echo.sdk.invoke

The authorization server does NOT advertise:
    echo.read, echo.write, echo.runpod.read, echo.runpod.prepare,
    echo.runpod.control, echo.runpod.spend

echo.read was a candidate repair target. Live metadata rejected it.
Do not request echo.write. Mutations stay mutating and use echo.sdk.invoke.
"""

from __future__ import annotations

PACKAGE_VERSION = "1.1.1"

# Live-accepted ChatGPT / MCP resource scopes.
SCOPE_SEARCH = "echo.search"
SCOPE_FETCH = "echo.fetch"
SCOPE_READ = "echo.invoke.read"
SCOPE_INVOKE = "echo.sdk.invoke"

ALL_SCOPES = (SCOPE_SEARCH, SCOPE_FETCH, SCOPE_READ, SCOPE_INVOKE)
LIVE_SCOPES = ALL_SCOPES

READ_SCOPES = frozenset({SCOPE_FETCH, SCOPE_READ})
SEARCH_SCOPES = frozenset({SCOPE_SEARCH})
INVOKE_SCOPES = frozenset({SCOPE_INVOKE})

# Names that must never be requested or advertised.
FORBIDDEN_SCOPES = frozenset(
    {
        "echo.write",
        "echo.read",
        "echo.runpod.read",
        "echo.runpod.prepare",
        "echo.runpod.control",
        "echo.runpod.spend",
    }
)

OAUTH_NEVER = ("echo.write",)

SCOPE_DESCRIPTIONS = {
    SCOPE_SEARCH: "Discovery / registry / live-verify catalog queries",
    SCOPE_FETCH: "Fetch a specific RunPod resource by id",
    SCOPE_READ: "Read-only RunPod capability invocation",
    SCOPE_INVOKE: "Governed preparation and mutation capability invocation",
}

ISSUER = "https://mcp.echo-op.com"
AUTHORIZATION_ENDPOINT = "https://mcp.echo-op.com/oauth/authorize"
TOKEN_ENDPOINT = "https://mcp.echo-op.com/oauth/token"
JWKS_URI = "https://mcp.echo-op.com/.well-known/jwks.json"
RESOURCE_URL = "https://mcp.echo-op.com/oauth-mcp-runpod-v1"


def recognized_scopes(scopes: list[str] | tuple[str, ...] | None) -> set[str]:
    """Return only live-accepted scopes. Unknown / invented names grant nothing."""
    return set(scopes or ()) & set(ALL_SCOPES)


def scopes_for_read_tool(*, discovery: bool = False) -> tuple[str, ...]:
    if discovery:
        return (SCOPE_SEARCH, SCOPE_READ, SCOPE_FETCH)
    return (SCOPE_READ, SCOPE_FETCH)


def scopes_for_prepare_tool() -> tuple[str, ...]:
    return (SCOPE_READ, SCOPE_FETCH, SCOPE_INVOKE)


def scopes_for_mutation_tool() -> tuple[str, ...]:
    return (SCOPE_INVOKE,)


def primary_required_scope(scopes: list[str] | tuple[str, ...], *, mutating: bool) -> str:
    """Single scope the live pack middleware can enforce."""
    if mutating:
        return SCOPE_INVOKE
    if SCOPE_READ in scopes:
        return SCOPE_READ
    if SCOPE_FETCH in scopes:
        return SCOPE_FETCH
    return SCOPE_SEARCH
