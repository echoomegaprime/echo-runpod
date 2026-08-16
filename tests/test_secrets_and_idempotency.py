import unittest

from echo_runpod.client import idempotency_digest
from echo_runpod.redaction import assert_no_secrets, redact, redact_text
from echo_runpod.secrets import SecretBroker, SecretError


class SecretTests(unittest.TestCase):
    def test_redacts_runpod_key(self):
        text = "Authorization: Bearer RP_abcdefghijklmnopqrstuvwxyz123456"
        out = redact_text(text)
        self.assertNotIn("RP_abcdefghijklmnopqrstuvwxyz123456", out)
        self.assertIn("[REDACTED]", out)
        assert_no_secrets(out)

    def test_redacts_env_assignment(self):
        out = redact_text("RUNPOD_API_KEY=supersecretvalue123456")
        self.assertNotIn("supersecretvalue123456", out)

    def test_redacts_nested(self):
        payload = redact({"api_key": "abc", "nested": {"token": "xyz", "ok": 1}})
        self.assertEqual(payload["api_key"], "[REDACTED]")
        self.assertEqual(payload["nested"]["token"], "[REDACTED]")
        self.assertEqual(payload["nested"]["ok"], 1)

    def test_broker_never_logs_key(self):
        broker = SecretBroker(env={"RUNPOD_API_KEY": "RP_this_must_not_leak_1234567890"})
        status = broker.status()
        self.assertTrue(status.present)
        self.assertNotIn("RP_this", repr(status))
        header = broker.authorization_header()
        redacted = redact(header)
        self.assertEqual(redacted["Authorization"], "[REDACTED]")

    def test_missing_secret(self):
        broker = SecretBroker(env={})
        with self.assertRaises(SecretError):
            broker.resolve()


class IdempotencyTests(unittest.TestCase):
    def test_same_key_same_request(self):
        req = {"workload_id": "w1", "gpu_count": 1}
        a = idempotency_digest("runpod_create_pod", req)
        b = idempotency_digest("runpod_create_pod", req)
        self.assertEqual(a, b)

    def test_different_request_different_digest(self):
        a = idempotency_digest("runpod_create_pod", {"gpu_count": 1})
        b = idempotency_digest("runpod_create_pod", {"gpu_count": 2})
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
