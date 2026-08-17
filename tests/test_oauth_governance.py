"""Regression pack for the Nexus OAuth / governed mutation repair."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from echo_runpod.capabilities import capability_records, nexus_manifest
from echo_runpod.client import RunPodClient
from echo_runpod.idempotency import IdempotencyStore, set_store
from echo_runpod.mcp import (
    ALL_SCOPES,
    TOOLS,
    call_tool,
    handle_initialize,
    handle_rpc,
    resource_catalog,
    tools_list_payload,
)
from echo_runpod.oauth import (
    FORBIDDEN_SCOPES,
    PACKAGE_VERSION,
    SCOPE_FETCH,
    SCOPE_INVOKE,
    SCOPE_READ,
    SCOPE_SEARCH,
)
from echo_runpod.policy import DESTRUCTIVE_ACTIONS, evaluate_action
from echo_runpod.redaction import assert_no_secrets
from echo_runpod.secrets import SecretBroker

from tests.test_governance import FULL_LANE
from tests.test_mcp import FakeTransport, _client


ROOT = Path(__file__).resolve().parents[1]


class OauthScopeContractTests(unittest.TestCase):
    def test_01_live_approved_oauth_scope_constants(self):
        self.assertEqual(ALL_SCOPES, (SCOPE_SEARCH, SCOPE_FETCH, SCOPE_READ, SCOPE_INVOKE))
        self.assertEqual(SCOPE_SEARCH, "echo.search")
        self.assertEqual(SCOPE_FETCH, "echo.fetch")
        self.assertEqual(SCOPE_READ, "echo.invoke.read")
        self.assertEqual(SCOPE_INVOKE, "echo.sdk.invoke")
        cat = resource_catalog()
        self.assertEqual(set(cat["scopes"]), set(ALL_SCOPES))

    def test_02_echo_write_absent(self):
        self.assertNotIn("echo.write", ALL_SCOPES)
        self.assertIn("echo.write", resource_catalog()["oauth_never"])
        manifest = nexus_manifest()
        self.assertNotIn("echo.write", manifest["oauth_scopes_used"])
        self.assertIn("echo.write", manifest["oauth_never"])
        for rec in manifest["capabilities"]:
            self.assertNotIn("echo.write", rec["oauth_scopes"])

    def test_03_invented_runpod_scopes_absent(self):
        invented = {
            "echo.runpod.read",
            "echo.runpod.prepare",
            "echo.runpod.control",
            "echo.runpod.spend",
            "echo.read",
        }
        self.assertTrue(invented <= FORBIDDEN_SCOPES)
        for name in invented:
            self.assertNotIn(name, ALL_SCOPES)
            self.assertNotIn(name, resource_catalog()["scopes"])


class ToolFilterTests(unittest.TestCase):
    def test_04_read_scope_sees_only_read_tools(self):
        names = {t["name"] for t in tools_list_payload([SCOPE_READ])}
        self.assertIn("runpod_list_pods", names)
        self.assertIn("runpod_status", names)
        self.assertNotIn("runpod_create_pod", names)
        self.assertNotIn("runpod_stop_pod", names)
        self.assertNotIn("runpod_terminate_pod", names)
        for tool in TOOLS:
            if tool["name"] in names:
                self.assertFalse(tool["mutating"], tool["name"])

    def test_05_sdk_invoke_sees_governed_mutation_tools(self):
        names = {t["name"] for t in tools_list_payload([SCOPE_INVOKE])}
        self.assertIn("runpod_create_pod", names)
        self.assertIn("runpod_stop_pod", names)
        self.assertIn("runpod_launch_training", names)
        self.assertIn("runpod_prepare_training", names)
        self.assertNotIn("runpod_list_pods", names)
        self.assertNotIn("runpod_billing", names)

    def test_06_unknown_scope_does_not_expose_everything(self):
        self.assertEqual(tools_list_payload([]), [])
        self.assertEqual(tools_list_payload(None), [])
        self.assertEqual(tools_list_payload(["echo.runpod.read"]), [])
        self.assertEqual(tools_list_payload(["echo.write"]), [])
        self.assertEqual(tools_list_payload(["not.a.scope"]), [])
        mixed = {t["name"] for t in tools_list_payload(["echo.runpod.spend", SCOPE_READ])}
        self.assertTrue(mixed)
        self.assertNotIn("runpod_create_pod", mixed)


class AnnotationAndSchemaTests(unittest.TestCase):
    def test_07_mutation_annotations_readonly_false(self):
        for tool in TOOLS:
            if tool["mutating"]:
                self.assertFalse(tool["annotations"]["readOnlyHint"], tool["name"])

    def test_08_destructive_tools_marked_destructive(self):
        for name in DESTRUCTIVE_ACTIONS:
            tool = next((t for t in TOOLS if t["name"] == name), None)
            if tool is None:
                continue
            self.assertTrue(tool["annotations"]["destructiveHint"], name)
            self.assertFalse(tool["annotations"]["readOnlyHint"], name)

    def test_09_every_mutation_schema_contains_confirm(self):
        for tool in TOOLS:
            if tool["mutating"]:
                props = tool["inputSchema"]["properties"]
                self.assertIn("confirm", props, tool["name"])
                self.assertIn("confirm", tool["inputSchema"].get("required", []), tool["name"])

    def test_10_mutations_contain_approved_manifest(self):
        for tool in TOOLS:
            if tool["mutating"]:
                self.assertIn("approved_manifest", tool["inputSchema"]["properties"], tool["name"])

    def test_11_mutations_contain_full_lane(self):
        for tool in TOOLS:
            if tool["mutating"]:
                self.assertIn("full_lane", tool["inputSchema"]["properties"], tool["name"])

    def test_12_mutations_contain_idempotency_key(self):
        for tool in TOOLS:
            if tool["mutating"]:
                self.assertIn("idempotency_key", tool["inputSchema"]["properties"], tool["name"])
            else:
                self.assertNotIn("idempotency_key", tool["inputSchema"]["properties"], tool["name"])
                self.assertNotIn("confirm", tool["inputSchema"]["properties"], tool["name"])


class IdempotencyEnforcementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = IdempotencyStore()
        set_store(self.store)

    def tearDown(self) -> None:
        set_store(None)

    def _lane_create(self, gpu="RTX 6000 Ada", extra=None):
        args = {
            "gpu_type": gpu,
            "gpu_count": 1,
            "workload_id": "landman-teacher-v4-exp1",
            "confirm": "EXECUTE",
            "full_lane": FULL_LANE,
            "idempotency_key": "create-landman-001",
        }
        if extra:
            args.update(extra)
        return args

    def test_13_same_key_same_request_does_not_duplicate_spend(self):
        transport = FakeTransport()
        client = _client(transport)
        args = self._lane_create()
        first = call_tool("runpod_create_pod", args, scopes=[SCOPE_INVOKE], client=client)
        self.assertTrue(first["ok"], first)
        posts = [c for c in transport.calls if c[0] == "POST" and str(c[1]).endswith("/pods")]
        self.assertEqual(len(posts), 1)
        second = call_tool("runpod_create_pod", dict(args), scopes=[SCOPE_INVOKE], client=client)
        self.assertTrue(second["ok"], second)
        self.assertTrue(second.get("idempotent_replay"))
        posts = [c for c in transport.calls if c[0] == "POST" and str(c[1]).endswith("/pods")]
        self.assertEqual(len(posts), 1)

    def test_14_same_key_changed_request_conflicts(self):
        transport = FakeTransport()
        client = _client(transport)
        first = call_tool("runpod_create_pod", self._lane_create(), scopes=[SCOPE_INVOKE], client=client)
        self.assertTrue(first["ok"], first)
        changed = self._lane_create(gpu="A40")
        conflict = call_tool("runpod_create_pod", changed, scopes=[SCOPE_INVOKE], client=client)
        self.assertFalse(conflict["ok"])
        self.assertEqual(conflict["error_type"], "idempotency_conflict")
        posts = [c for c in transport.calls if c[0] == "POST" and str(c[1]).endswith("/pods")]
        self.assertEqual(len(posts), 1)


class FullLaneIsolationTests(unittest.TestCase):
    def test_15_full_lane_workload_mismatch_rejected(self):
        d = evaluate_action(
            "runpod_create_pod",
            confirm="EXECUTE",
            full_lane=FULL_LANE,
            request={"workload_id": "prometheus-27b", "gpu_class": "A40"},
        )
        self.assertFalse(d.allowed)
        self.assertIn("workload", d.reason)

    def test_16_full_lane_dataset_mismatch_rejected(self):
        d = evaluate_action(
            "runpod_launch_training",
            confirm="EXECUTE",
            full_lane=FULL_LANE,
            request={"workload_id": "landman-teacher-v4-exp1", "dataset_sha256": "b" * 64},
        )
        self.assertFalse(d.allowed)
        self.assertIn("dataset", d.reason)

    def test_17_full_lane_model_mismatch_rejected(self):
        d = evaluate_action(
            "runpod_launch_training",
            confirm="EXECUTE",
            full_lane=FULL_LANE,
            request={"workload_id": "landman-teacher-v4-exp1", "model": "meta-llama/something"},
        )
        self.assertFalse(d.allowed)
        self.assertIn("model", d.reason)

    def test_18_gpu_class_outside_allowlist_rejected(self):
        d = evaluate_action(
            "runpod_create_pod",
            confirm="EXECUTE",
            full_lane=FULL_LANE,
            request={"workload_id": "landman-teacher-v4-exp1", "gpu_class": "H200"},
        )
        self.assertFalse(d.allowed)

    def test_19_gpu_count_above_limit_rejected(self):
        d = evaluate_action(
            "runpod_create_pod",
            confirm="EXECUTE",
            full_lane=FULL_LANE,
            request={"workload_id": "landman-teacher-v4-exp1", "gpu_count": 8},
        )
        self.assertFalse(d.allowed)

    def test_20_hourly_cost_ceiling_enforced(self):
        d = evaluate_action(
            "runpod_create_pod",
            confirm="EXECUTE",
            full_lane=FULL_LANE,
            request={"workload_id": "landman-teacher-v4-exp1", "gpu_class": "A40", "hourly_rate": 9.0},
        )
        self.assertFalse(d.allowed)

    def test_21_total_budget_enforced(self):
        d = evaluate_action(
            "runpod_create_pod",
            confirm="EXECUTE",
            full_lane=FULL_LANE,
            request={"workload_id": "landman-teacher-v4-exp1", "gpu_class": "A40", "projected_spend": 99},
        )
        self.assertFalse(d.allowed)


class RedactionAndCapabilityTests(unittest.TestCase):
    def test_22_runpod_api_key_never_appears_in_tool_output(self):
        transport = FakeTransport()
        transport.mode = "secret_leak"
        out = call_tool("runpod_list_pods", {}, scopes=[SCOPE_READ], client=_client(transport))
        blob = repr(out)
        self.assertNotIn("RP_SUPERSECRETKEYVALUE1", blob)
        self.assertNotIn("RP_FAKEKEYFAKEKEYFAKE", blob)
        assert_no_secrets(out)

    def test_23_tokens_and_authorization_headers_redacted(self):
        from echo_runpod.redaction import redact, redact_text

        header = redact({"Authorization": "Bearer tok_secret_value_123456"})
        self.assertEqual(header["Authorization"], "[REDACTED]")
        text = redact_text("Authorization: Bearer tok_secret_value_123456")
        self.assertNotIn("tok_secret_value_123456", text)

    def test_24_capability_records_use_per_tool_scopes(self):
        records = {r["tool"]: r for r in capability_records()}
        self.assertNotEqual(set(records["runpod_list_pods"]["oauth_scopes"]), set(ALL_SCOPES))
        self.assertEqual(set(records["runpod_list_pods"]["oauth_scopes"]), {SCOPE_READ, SCOPE_FETCH})
        self.assertEqual(set(records["runpod_create_pod"]["oauth_scopes"]), {SCOPE_INVOKE})
        self.assertIn(SCOPE_INVOKE, records["runpod_prepare_training"]["oauth_scopes"])
        for rec in records.values():
            self.assertTrue(set(rec["oauth_scopes"]) <= set(ALL_SCOPES), rec["tool"])
            self.assertNotIn("echo.write", rec["oauth_scopes"])
            self.assertNotIn("echo.runpod.read", rec["oauth_scopes"])

    def test_25_chatgpt_skill_contains_current_scope_guidance(self):
        skill = (ROOT / "chatgpt" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("echo.search", skill)
        self.assertIn("echo.invoke.read", skill)
        self.assertIn("echo.sdk.invoke", skill)
        self.assertIn("echo.write", skill)
        self.assertIn("EXECUTE", skill)
        self.assertIn("vault://runpod/api-key", skill)
        self.assertIn("never request echo.write", skill.lower())
        self.assertIn("Do **not** request", skill)
        self.assertIn("invalid_scope", skill)
        self.assertIn("1.1.1", handle_initialize()["serverInfo"]["version"])
        self.assertEqual(PACKAGE_VERSION, "1.1.1")
        self.assertEqual(nexus_manifest()["version"], "1.1.1")


class UnauthenticatedSurfaceTests(unittest.TestCase):
    def test_unauthenticated_lists_no_tools(self):
        out = handle_rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, authenticated=False)
        self.assertTrue(out["result"]["isError"])
        self.assertEqual(out["result"]["structuredContent"]["error_type"], "unauthenticated")


if __name__ == "__main__":
    unittest.main()
