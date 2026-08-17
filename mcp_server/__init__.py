"""Thin MCP entry that re-exports the canonical Echo RunPod pack."""

from echo_runpod.mcp import (
    ALL_SCOPES,
    RESOURCE_ID,
    RESOURCE_PATH,
    RESOURCE_URL,
    TOOLS,
    call_tool,
    chatgpt_tool_schemas,
    handle_initialize,
    handle_rpc,
    resource_catalog,
    tools_list_payload,
)

__all__ = [
    "ALL_SCOPES",
    "RESOURCE_ID",
    "RESOURCE_PATH",
    "RESOURCE_URL",
    "TOOLS",
    "call_tool",
    "chatgpt_tool_schemas",
    "handle_initialize",
    "handle_rpc",
    "resource_catalog",
    "tools_list_payload",
]
