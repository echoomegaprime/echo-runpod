import unittest

from echo_runpod.router import route_prompt


class RouterTests(unittest.TestCase):
    def test_gpu_qlora_27b(self):
        route = route_prompt("Which GPU should I use to QLoRA a 27B model on RunPod?")
        self.assertEqual(route.lane, "gpu_selection")
        self.assertFalse(route.mutation)
        self.assertIn("gpu-selection.md", route.references)

    def test_show_pods(self):
        route = route_prompt("Show my RunPod pods.")
        self.assertEqual(route.lane, "inspection")
        self.assertFalse(route.mutation)
        self.assertFalse(route.requires_approval)

    def test_train_adapter(self):
        route = route_prompt("Train this adapter.")
        self.assertEqual(route.lane, "training_prepare")
        self.assertFalse(route.mutation)


if __name__ == "__main__":
    unittest.main()
