import unittest

from echo_runpod.client import RunPodClient, RunPodError, parse_gpu_catalog, normalize_pods
from echo_runpod.manifests import landman_example
from echo_runpod.mcp import (
    ALL_SCOPES,
    RESOURCE_PATH,
    RESOURCE_URL,
    SCOPE_CONTROL,
    SCOPE_READ,
    SCOPE_SPEND,
    TOOLS,
    call_tool,
    chatgpt_tool_schemas,
    handle_initialize,
    handle_rpc,
    resource_catalog,
    tools_list_payload,
)
from echo_runpod.redaction import assert_no_secrets
from echo_runpod.secrets import SecretBroker


class FakeTransport:
    def __init__(self):
        self.calls = []
        self.mode = "ok"

    def __call__(self, method, url, body):
        self.calls.append((method, url, body))
        if self.mode == "timeout":
            raise RunPodError("RunPod timeout: timed out", status=None)
        if self.mode == "malformed":
            raise RunPodError("malformed RunPod response: boom", payload="<html>")
        if self.mode == "secret_leak":
            return {"pods": [{"id": "p1", "name": "x", "api_key": "RP_SUPERSECRETKEYVALUE1"}]}
        if "/gpuTypes" in url or "gpuTypes" in str(body):
            return {
                "data": {
                    "gpuTypes": [
                        {
                            "id": "NVIDIA H100 80GB HBM3",
                            "displayName": "H100",
                            "memoryInGb": 80,
                            "securePrice": 3.89,
                            "communityPrice": 2.69,
                            "lowestPrice": {
                                "uninterruptablePrice": 3.89,
                                "stockStatus": "High",
                            },
                        }
                    ]
                }
            }
        if url.endswith("/pods") and method == "GET":
            return {
                "pods": [
                    {
                        "id": "pod_landman",
                        "name": "landman-teacher",
                        "desiredStatus": "RUNNING",
                        "gpuTypeId": "NVIDIA H100 80GB HBM3",
                        "gpuCount": 1,
                        "ports": [{"privatePort": 22, "publicPort": 22123}],
                    }
                ]
            }
        if "/pods/pod_landman/logs" in url:
            return {"logs": "epoch 1 loss 1.2"}
        if "/pods/pod_landman" in url:
            return {
                "id": "pod_landman",
                "desiredStatus": "RUNNING",
                "ports": [{"privatePort": 22, "publicPort": 22123}],
                "runtime": {"uptimeInSeconds": 120},
            }
        if url.endswith("/billing/pods"):
            return {"time": "2026-08-16", "amount": 1.25}
        if "myself" in str(body).lower():
            return {"data": {"myself": {"id": "user_1", "clientBalance": 42.0}}}
        if "/networkvolumes" in url:
            return {"networkVolumes": [{"id": "vol1", "size": 200}]}
        if "/endpoints" in url:
            return {"endpoints": [{"id": "ep1", "workers": {"idle": 0, "running": 1}}]}
        return {"ok": True, "url": url, "method": method}


def _client(transport=None):
    return RunPodClient(SecretBroker(env={"RUNPOD_API_KEY": "RP_FAKEKEYFAKEKEYFAKE"}), transport=transport or FakeTransport())


class McpTests(unittest.TestCase):
    def test_01_mcp_initialization(self):
        result = handle_initialize()
        self.assertEqual(result["protocolVersion"], "2025-03-26")
        self.assertEqual(result["serverInfo"]["name"], "echo-oauth-mcp-runpod-v1")
        self.assertIn("tools", result["capabilities"])

    def test_02_tool_discovery(self):
        tools = tools_list_payload(list(ALL_SCOPES))
        names = {t["name"] for t in tools}
        self.assertIn("runpod_list_pods", names)
        self.assertIn("runpod_create_pod", names)
        self.assertGreaterEqual(len(tools), 20)

    def test_03_oauth_unauthenticated_rejection(self):
        out = handle_rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, authenticated=False)
        self.assertTrue(out["result"]["isError"])
        self.assertEqual(out["result"]["structuredContent"]["error_type"], "unauthenticated")

    def test_04_valid_read_scope(self):
        out = call_tool(
            "runpod_list_pods",
            {},
            scopes=[SCOPE_READ],
            client=_client(),
        )
        self.assertTrue(out["ok"])
        self.assertEqual(out["data"]["pods"][0]["id"], "pod_landman")

    def test_05_mutation_blocked_without_scope(self):
        out = call_tool("runpod_stop_pod", {"pod_id": "x", "confirm": "EXECUTE"}, scopes=[SCOPE_READ])
        self.assertFalse(out["ok"])
        self.assertEqual(out["error_type"], "insufficient_scope")

    def test_06_mutation_blocked_without_approval(self):
        out = call_tool("runpod_stop_pod", {"pod_id": "x"}, scopes=[SCOPE_CONTROL])
        self.assertEqual(out["error_type"], "mutating_ops_require_confirm_EXECUTE")
        out2 = call_tool(
            "runpod_stop_pod",
            {"pod_id": "x", "confirm": "EXECUTE"},
            scopes=[SCOPE_CONTROL],
        )
        self.assertEqual(out2["error_type"], "policy_denied")

    def test_07_api_key_never_appears_in_mcp_output(self):
        transport = FakeTransport()
        transport.mode = "secret_leak"
        out = call_tool("runpod_list_pods", {}, scopes=[SCOPE_READ], client=_client(transport))
        blob = repr(out)
        self.assertNotIn("RP_SUPERSECRETKEYVALUE1", blob)
        self.assertNotIn("RP_FAKEKEYFAKEKEYFAKE", blob)
        assert_no_secrets(out)

    def test_08_malformed_runpod_responses(self):
        transport = FakeTransport()
        transport.mode = "malformed"
        out = call_tool("runpod_list_pods", {}, scopes=[SCOPE_READ], client=_client(transport))
        self.assertEqual(out["error_type"], "runpod_malformed")

    def test_09_runpod_api_timeout(self):
        transport = FakeTransport()
        transport.mode = "timeout"
        out = call_tool("runpod_list_pods", {}, scopes=[SCOPE_READ], client=_client(transport))
        self.assertEqual(out["error_type"], "runpod_timeout")

    def test_10_price_parsing(self):
        catalog = parse_gpu_catalog(
            {
                "data": {
                    "gpuTypes": [
                        {
                            "id": "H100",
                            "displayName": "H100",
                            "securePrice": "3.89",
                            "lowestPrice": {"uninterruptablePrice": 3.89, "stockStatus": "High"},
                        }
                    ]
                }
            }
        )
        self.assertEqual(catalog[0]["securePrice"], 3.89)
        self.assertEqual(catalog[0]["lowestPrice"], 3.89)
        with self.assertRaises(RunPodError):
            parse_gpu_catalog({"nope": True})

    def test_11_pod_enumeration(self):
        pods = normalize_pods({"pods": [{"id": "a"}, {"id": "b"}]})
        self.assertEqual([p["id"] for p in pods], ["a", "b"])
        self.assertEqual(normalize_pods([{"id": "c"}])[0]["id"], "c")

    def test_12_pod_state_parsing(self):
        from echo_runpod.mcp import parse_pod_state

        self.assertEqual(parse_pod_state({"desiredStatus": "RUNNING"}), "RUNNING")
        self.assertEqual(parse_pod_state({"status": {"state": "EXITED"}}), "EXITED")
        self.assertEqual(parse_pod_state("bad"), "UNKNOWN")

    def test_13_gpu_availability(self):
        out = call_tool("runpod_gpu_availability", {}, scopes=[SCOPE_READ], client=_client())
        self.assertTrue(out["ok"])
        self.assertEqual(out["data"]["gpus"][0]["stockStatus"], "High")

    def test_14_training_manifest_validation(self):
        good = call_tool(
            "runpod_prepare_training",
            {"manifest": landman_example()},
            scopes=["echo.runpod.prepare"],
            client=_client(),
        )
        self.assertTrue(good["ok"])
        bad = call_tool(
            "runpod_validate_manifest",
            {"manifest": {"workload_id": "x"}},
            scopes=["echo.runpod.prepare"],
            client=_client(),
        )
        self.assertEqual(bad["error_type"], "validation_error")

    def test_15_spending_ceiling_enforcement(self):
        out = call_tool(
            "runpod_cost_estimate",
            {"gpu_type": "H100", "hours": 6, "max_hourly_rate": 1.0, "max_total_budget": 5},
            scopes=[SCOPE_READ],
            client=_client(),
        )
        self.assertTrue(out["ok"])
        self.assertFalse(out["data"]["allowed"])
        over = call_tool(
            "runpod_create_pod",
            {
                "gpu_type": "H100",
                "confirm": "EXECUTE",
                "full_lane": {
                    "workload_id": "w1",
                    "allowed_gpu_classes": ["rtx 4090"],
                    "max_gpu_count": 1,
                    "max_hourly_rate": 1.0,
                    "max_total_spend": 5,
                    "max_runtime": "1h",
                    "allowed_storage": 20,
                    "allowed_pod_count": 1,
                    "allowed_endpoint_count": 0,
                    "dataset_identity": "d",
                    "model_identity": "m",
                    "artifact_destination": "a",
                    "termination_policy": "stop",
                },
            },
            scopes=[SCOPE_SPEND],
            client=_client(),
        )
        self.assertEqual(over["error_type"], "policy_denied")

    def test_16_tool_error_typing(self):
        out = call_tool("not_a_tool", {}, scopes=[SCOPE_READ])
        self.assertEqual(out["error_type"], "unknown_tool")
        unauth = handle_rpc({"id": 1, "method": "tools/call", "params": {"name": "runpod_list_pods"}}, authenticated=False)
        self.assertEqual(unauth["result"]["structuredContent"]["error_type"], "unauthenticated")

    def test_17_nexus_resource_registration(self):
        cat = resource_catalog()
        self.assertEqual(cat["path"], "/oauth-mcp-runpod-v1")
        self.assertEqual(cat["canonical"], "https://mcp.echo-op.com/oauth-mcp-runpod-v1")
        self.assertEqual(cat["id"], "oauth-mcp-runpod-v1")
        self.assertIn("echo.runpod.read", cat["scopes"])
        self.assertNotIn("echo.write", cat["scopes"])
        self.assertEqual(cat["oauth_never"], ["echo.write"])

    def test_18_cloudflare_route_health(self):
        cat = resource_catalog()
        self.assertEqual(cat["cloudflare_route"], RESOURCE_PATH)
        self.assertTrue(cat["canonical"].startswith("https://mcp.echo-op.com/"))
        self.assertTrue(RESOURCE_PATH.startswith("/oauth-mcp-"))
        # Handler path matching used by Echo Nexus pack middleware
        path = RESOURCE_PATH
        self.assertTrue(path == cat["path"] or path.startswith(cat["path"] + "/"))

    def test_19_live_mcp_endpoint_discovery(self):
        cat = resource_catalog()
        self.assertEqual(cat["canonical"], RESOURCE_URL)
        self.assertIn("runpod_live_verify", cat["tools"])
        listed = {t["name"] for t in tools_list_payload(list(ALL_SCOPES))}
        self.assertEqual(listed, set(cat["tools"]))

    def test_20_chatgpt_compatible_tool_schema(self):
        schemas = chatgpt_tool_schemas()
        self.assertGreaterEqual(len(schemas), 20)
        for tool in schemas:
            schema = tool["inputSchema"]
            self.assertEqual(schema["type"], "object")
            self.assertIn("properties", schema)
            self.assertFalse(schema.get("additionalProperties", True))
            self.assertTrue(tool["name"].startswith("runpod_"))
            self.assertTrue(tool["description"])
        mutating = [t for t in TOOLS if t["mutating"]]
        for tool in mutating:
            self.assertIn("confirm", tool["inputSchema"]["properties"])


if __name__ == "__main__":
    unittest.main()
