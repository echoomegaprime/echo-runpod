import unittest

from echo_runpod.mcp import ALL_SCOPES, TOOLS

from scripts import echo_runpod_edge as edge


class EdgeAdapterTests(unittest.TestCase):
    def test_configure_registers_dedicated_resource(self):
        pack: dict = {
            "/oauth-mcp-nexus-v1": {
                "id": "oauth-mcp-nexus-v1",
                "name": "Echo Nexus",
                "scopes": ["echo.nexus.read"],
                "tools": ["nexus_status"],
            }
        }
        required: dict[str, str] = {}
        mutating: set[str] = set()
        paths: set[str] = set(pack)
        edge.configure_pack(pack, required, mutating, paths)
        self.assertIn("/oauth-mcp-runpod-v1", pack)
        self.assertIn("/oauth-mcp-runpod-v1", paths)
        meta = pack["/oauth-mcp-runpod-v1"]
        self.assertEqual(meta["id"], "oauth-mcp-runpod-v1")
        self.assertEqual(set(meta["scopes"]), set(ALL_SCOPES))
        self.assertNotIn("echo.write", meta["scopes"])
        self.assertGreaterEqual(len(meta["tools"]), 20)
        self.assertIn("runpod_list_pods", pack["/oauth-mcp-nexus-v1"]["tools"])
        self.assertIn("echo.invoke.read", pack["/oauth-mcp-nexus-v1"]["scopes"])
        self.assertIn("echo.sdk.invoke", pack["/oauth-mcp-nexus-v1"]["scopes"])
        self.assertNotIn("echo.runpod.read", pack["/oauth-mcp-nexus-v1"]["scopes"])
        self.assertEqual(required["runpod_list_pods"], "echo.invoke.read")
        self.assertEqual(required["runpod_stop_pod"], "echo.sdk.invoke")
        self.assertEqual(required["runpod_create_pod"], "echo.sdk.invoke")
        self.assertIn("runpod_stop_pod", mutating)
        self.assertNotIn("runpod_list_pods", mutating)

    def test_tool_definition_is_chatgpt_compatible(self):
        schema = edge.tool_definition("runpod_stop_pod")
        assert schema is not None
        self.assertEqual(schema["inputSchema"]["type"], "object")
        self.assertFalse(schema["inputSchema"].get("additionalProperties", True))
        self.assertIn("confirm", schema["inputSchema"]["properties"])
        self.assertFalse(schema["annotations"]["readOnlyHint"])
        listed = {t["name"] for t in TOOLS}
        self.assertTrue(listed.issubset(set(edge.tool_names())))

    def test_unknown_tool_is_none(self):
        self.assertIsNone(edge.tool_definition("nexus_status"))


if __name__ == "__main__":
    unittest.main()
