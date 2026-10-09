import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("image_tags", Path(__file__).parents[1] / "scripts/image-tags.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TagsTest(unittest.TestCase):
    def test_actual_versions_and_jll_build_suffix(self):
        metadata = {
            "image": {"source_revision": "a" * 40, "created": "2026-10-09T00:00:00Z",
                      "base_image": "quay.io/jupyter/julia-notebook:julia-1.13.1@sha256:" + "b" * 64},
            "julia": {"version": "1.13.1", "cuda_runtime": "12.9",
                      "direct_packages": {"QuantumToolbox": "0.51.2", "CUDA_Runtime_jll": "0.25.0+2"}},
            "python": {"version": "3.13.15", "packages": {"jupyterhub": "6.0.1", "jupyterlab": "4.6.4", "notebook": "7.6.3"}},
            "os": {"version_id": "26.04"}, "tools": {"mamba": "2.8.1"}, "manifest_sha256": "c" * 64,
        }
        tags, labels = module.derive(metadata, "123-1")
        for tag in ("julia-1.13.1", "hub-6.0.1", "python-3.13.15", "python-3.13",
                    "quantumtoolbox-0.51.2", "cuda-runtime-jll-0.25.0_2", "build-123-1"):
            self.assertIn(tag, tags)
        self.assertEqual(labels["org.opencontainers.image.base.digest"], "sha256:" + "b" * 64)
        self.assertIn('"QuantumToolbox": "0.51.2"', labels["org.ltpn.hydra-jupyterhub.julia.direct-versions"])
        metadata["matlab"] = {"release": "R2026b", "version": "26.2.0.1234567",
                              "source_image": "ghcr.io/ltpn/matlab:R2026b"}
        tags, labels = module.derive(metadata, "123-1")
        self.assertIn("matlab-R2026b", tags)
        self.assertIn("matlab-26.2.0.1234567", tags)
        self.assertEqual(labels["org.ltpn.hydra-jupyterhub.matlab.release"], "R2026b")

    def test_rejects_overlong_tags(self):
        with self.assertRaises(ValueError):
            module.safe_tag("a" * 129)


if __name__ == "__main__":
    unittest.main()
