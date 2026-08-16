import unittest

from echo_runpod.manifests import ManifestError, landman_example, validate_manifest


class ManifestTests(unittest.TestCase):
    def test_landman_example_validates(self):
        man = validate_manifest(landman_example())
        self.assertEqual(man.dataset_rows, 5800)
        self.assertEqual(man.project, "landman")

    def test_missing_field(self):
        raw = landman_example()
        del raw["gpu_type"]
        with self.assertRaises(ManifestError):
            validate_manifest(raw)

    def test_bad_sha(self):
        raw = landman_example()
        raw["dataset_sha256"] = "nope"
        with self.assertRaises(ManifestError):
            validate_manifest(raw)


if __name__ == "__main__":
    unittest.main()
