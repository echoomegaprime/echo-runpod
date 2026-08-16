import unittest

from echo_runpod.policy import evaluate_action


class PolicyTests(unittest.TestCase):
    def test_read_without_approval(self):
        d = evaluate_action("runpod_list_pods")
        self.assertTrue(d.allowed)
        self.assertFalse(d.mutation)
        self.assertTrue(d.annotations["readOnlyHint"])

    def test_create_requires_approval(self):
        d = evaluate_action("runpod_create_pod")
        self.assertFalse(d.allowed)
        self.assertTrue(d.mutation)
        self.assertFalse(d.annotations["readOnlyHint"])

    def test_start_requires_approval(self):
        self.assertFalse(evaluate_action("runpod_start_pod").allowed)

    def test_resize_requires_approval(self):
        self.assertFalse(evaluate_action("runpod_resize_pod").allowed)

    def test_launch_training_requires_approval(self):
        self.assertFalse(evaluate_action("runpod_launch_training").allowed)

    def test_mutations_not_labeled_readonly(self):
        for action in (
            "runpod_create_pod",
            "runpod_start_pod",
            "runpod_terminate_pod",
            "runpod_launch_training",
        ):
            d = evaluate_action(action)
            self.assertFalse(d.annotations["readOnlyHint"], action)

    def test_approved_manifest_still_needs_execute(self):
        d = evaluate_action(
            "runpod_create_pod",
            approved_manifest={"workload_id": "w1"},
            request={"workload_id": "w1"},
        )
        self.assertFalse(d.allowed)
        d2 = evaluate_action(
            "runpod_create_pod",
            confirm="EXECUTE",
            approved_manifest={"workload_id": "w1"},
            request={"workload_id": "w1"},
        )
        self.assertTrue(d2.allowed)


if __name__ == "__main__":
    unittest.main()
