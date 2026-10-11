import importlib.util
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    "registry", Path(__file__).parents[1] / "scripts/reset-matlab-proxy-registry.py"
)
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)


class ProxyRegistryTest(unittest.TestCase):
    def test_reused_context_cleared_and_license_cache_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            mwi = home / ".matlab/MWI/hosts/notebook"
            session = mwi / "proxy_manager/75_default"
            session.mkdir(parents=True)
            for name in ("75_jsp.info", "75_kernel.info"):
                (session / name).write_text('{"75_default":{"pid":"495"}}')
            cache = mwi / "proxy_app_config.json"
            cache.write_text("preserve licensing cache")
            user_file = home / "research.info"
            user_file.write_text("preserve notebook files")
            other = home / ".matlab/MWI/hosts/other/proxy_manager/75_default"
            other.mkdir(parents=True)
            (other / "75_jsp.info").write_text("other host")

            self.assertEqual(registry.reset_registry(home, "notebook"), 2)
            self.assertFalse(session.exists())
            self.assertEqual(cache.read_text(), "preserve licensing cache")
            self.assertEqual(user_file.read_text(), "preserve notebook files")
            self.assertTrue((other / "75_jsp.info").exists())
            self.assertEqual(registry.reset_registry(home, "notebook"), 0)

    def test_fresh_home_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.assertEqual(registry.reset_registry(home, "notebook"), 0)
            self.assertEqual(list(home.iterdir()), [])

    def test_unrelated_files_and_symlinked_sessions_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            root = home / ".matlab/MWI/hosts/notebook/proxy_manager"
            root.mkdir(parents=True)
            outside = home / "project"
            outside.mkdir()
            (outside / "research.info").write_text("keep")
            (root / "external").symlink_to(outside, target_is_directory=True)
            (root / "notes.txt").write_text("keep")
            self.assertEqual(registry.reset_registry(home, "notebook"), 0)
            self.assertTrue((outside / "research.info").exists())
            self.assertTrue((root / "notes.txt").exists())

    def test_symlinked_registry_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            mwi = home / ".matlab/MWI/hosts/notebook"
            mwi.mkdir(parents=True)
            outside = home / "project"
            outside.mkdir()
            (outside / "research.info").write_text("keep")
            (mwi / "proxy_manager").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(RuntimeError):
                registry.reset_registry(home, "notebook")
            self.assertTrue((outside / "research.info").exists())
