import unittest

from echo_runpod.governor import check_cost
from echo_runpod.isolation import isolate
from echo_runpod.policy import evaluate_action


FULL_LANE = {
    "workload_id": "landman-teacher-v4-exp1",
    "allowed_gpu_classes": ["RTX 6000 Ada", "A40", "L40S"],
    "max_gpu_count": 1,
    "max_hourly_rate": 1.5,
    "max_total_spend": 40.0,
    "max_runtime": "8h",
    "allowed_storage": 200,
    "allowed_pod_count": 1,
    "allowed_endpoint_count": 0,
    "dataset_identity": {
        "sha256": "3f6b93e80818e670402e75463ec2a5898104af03f4b616e1b8b6dfd8e6766a81"
    },
    "model_identity": "Qwen/Qwen2.5-32B-Instruct",
    "artifact_destination": "echo://artifacts/landman/teacher-v4-exp1",
    "termination_policy": "terminate-after-artifact-verify",
}


class GovernanceTests(unittest.TestCase):
    def test_budget_overrun_rejected(self):
        c = check_cost(
            live_hourly=2.0,
            estimated_runtime_hours=10,
            max_hourly_rate=5.0,
            max_total_budget=10.0,
        )
        self.assertFalse(c.allowed)

    def test_gpu_class_outside_allowlist(self):
        c = check_cost(
            live_hourly=1.0,
            estimated_runtime_hours=1,
            max_hourly_rate=5.0,
            max_total_budget=40.0,
            approved_gpu_classes=["A40"],
            requested_gpu="B200",
        )
        self.assertFalse(c.allowed)
        self.assertIn("allowlist", c.reason)

    def test_gpu_count_increase_rejected(self):
        c = check_cost(
            live_hourly=1.0,
            estimated_runtime_hours=1,
            max_hourly_rate=5.0,
            max_total_budget=40.0,
            approved_gpu_count=1,
            requested_gpu_count=2,
        )
        self.assertFalse(c.allowed)

    def test_wrong_workload(self):
        d = isolate(
            request_workload_id="prometheus-27b",
            request_project="prometheus",
            request_dataset_sha=None,
            request_model=None,
            target={"workload_id": "landman-teacher-v4-exp1", "project": "landman"},
        )
        self.assertFalse(d.allowed)

    def test_wrong_dataset_sha(self):
        d = isolate(
            request_workload_id="landman-teacher-v4-exp1",
            request_project="landman",
            request_dataset_sha="0" * 64,
            request_model=None,
            target={
                "workload_id": "landman-teacher-v4-exp1",
                "project": "landman",
                "dataset_sha256": "3f6b93e80818e670402e75463ec2a5898104af03f4b616e1b8b6dfd8e6766a81",
            },
        )
        self.assertFalse(d.allowed)
        self.assertIn("dataset", d.reason)

    def test_wrong_model(self):
        d = isolate(
            request_workload_id="landman-teacher-v4-exp1",
            request_project="landman",
            request_dataset_sha=None,
            request_model="other-model",
            target={
                "workload_id": "landman-teacher-v4-exp1",
                "project": "landman",
                "model": "Qwen/Qwen2.5-32B-Instruct",
            },
        )
        self.assertFalse(d.allowed)

    def test_landman_prometheus_cross_use(self):
        d = isolate(
            request_workload_id="landman-teacher-v4-exp1",
            request_project="landman",
            request_dataset_sha=None,
            request_model=None,
            target={"workload_id": "landman-teacher-v4-exp1", "project": "prometheus"},
        )
        self.assertFalse(d.allowed)
        self.assertIn("isolated", d.reason)

    def test_full_lane_permits_create(self):
        d = evaluate_action(
            "runpod_create_pod",
            confirm="EXECUTE",
            full_lane=FULL_LANE,
            request={
                "workload_id": "landman-teacher-v4-exp1",
                "gpu_class": "RTX 6000 Ada",
                "gpu_count": 1,
                "hourly_rate": 1.1,
                "projected_spend": 10,
                "dataset_sha256": "3f6b93e80818e670402e75463ec2a5898104af03f4b616e1b8b6dfd8e6766a81",
                "model": "Qwen/Qwen2.5-32B-Instruct",
            },
        )
        self.assertTrue(d.allowed)

    def test_full_lane_cannot_exceed_budget(self):
        d = evaluate_action(
            "runpod_create_pod",
            confirm="EXECUTE",
            full_lane=FULL_LANE,
            request={
                "workload_id": "landman-teacher-v4-exp1",
                "gpu_class": "RTX 6000 Ada",
                "projected_spend": 99,
            },
        )
        self.assertFalse(d.allowed)

    def test_full_lane_cannot_change_workload(self):
        d = evaluate_action(
            "runpod_create_pod",
            confirm="EXECUTE",
            full_lane=FULL_LANE,
            request={"workload_id": "prometheus-27b", "gpu_class": "A40"},
        )
        self.assertFalse(d.allowed)

    def test_full_lane_cannot_change_dataset(self):
        d = evaluate_action(
            "runpod_launch_training",
            confirm="EXECUTE",
            full_lane=FULL_LANE,
            request={
                "workload_id": "landman-teacher-v4-exp1",
                "dataset_sha256": "b" * 64,
            },
        )
        self.assertFalse(d.allowed)

    def test_full_lane_cannot_change_model(self):
        d = evaluate_action(
            "runpod_launch_training",
            confirm="EXECUTE",
            full_lane=FULL_LANE,
            request={
                "workload_id": "landman-teacher-v4-exp1",
                "model": "meta-llama/something",
            },
        )
        self.assertFalse(d.allowed)

    def test_full_lane_cannot_expand_gpu_count(self):
        d = evaluate_action(
            "runpod_create_pod",
            confirm="EXECUTE",
            full_lane=FULL_LANE,
            request={"workload_id": "landman-teacher-v4-exp1", "gpu_count": 8},
        )
        self.assertFalse(d.allowed)

    def test_full_lane_cannot_pick_expensive_outside_bounds(self):
        d = evaluate_action(
            "runpod_create_pod",
            confirm="EXECUTE",
            full_lane=FULL_LANE,
            request={
                "workload_id": "landman-teacher-v4-exp1",
                "gpu_class": "H200",
                "hourly_rate": 8.0,
            },
        )
        self.assertFalse(d.allowed)


if __name__ == "__main__":
    unittest.main()
