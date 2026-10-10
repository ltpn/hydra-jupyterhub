import importlib.util
import tempfile
import sys
import types
from unittest.mock import patch
import unittest
import urllib.error
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "vscode_launcher", Path(__file__).parents[1] / "scripts/configure-vscode-launcher.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>'
LICENSE = b"MIT License\nCopyright Microsoft Corporation\nPermission notice\n"


class IconFallbackTest(unittest.TestCase):
    def test_head_preferred_and_license_retained(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return LICENSE if url.endswith("LICENSE.txt") else SVG
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            icon = launcher.download_icon(root, fetch)
            self.assertEqual(icon.read_bytes(), SVG)
            self.assertEqual((root / "VSCODE-ICON-LICENSE.txt").read_bytes(), LICENSE)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all("/HEAD/" in url for url in calls))

    def test_missing_head_uses_pinned_commit(self):
        calls = []
        def fetch(url):
            calls.append(url)
            if "/HEAD/" in url:
                raise urllib.error.HTTPError(url, 404, "Not found", {}, None)
            return LICENSE if url.endswith("LICENSE.txt") else SVG
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIsNotNone(launcher.download_icon(root, fetch))
            self.assertIn(launcher.REFS[1], (root / "vscode-icon-source.txt").read_text())
        self.assertIn("/HEAD/", calls[0])
        self.assertTrue(all(launcher.REFS[1] in url for url in calls[1:]))

    def test_failed_or_invalid_downloads_keep_default(self):
        def missing(url):
            raise urllib.error.URLError("Unavailable")
        for fetch in (missing, lambda url: b"<html>Not an SVG</html>"):
            with self.subTest(fetch=fetch), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                # A previous preview must not leave a stale override behind.
                (root / "vscode-icon.svg").write_bytes(SVG)
                self.assertIsNone(launcher.download_icon(root, fetch))
                self.assertFalse((root / "vscode-icon.svg").exists())
                config = root / "jupyter_server_config.py"
                launcher.configure(config, None)
                self.assertIn("VS Code", config.read_text())
                self.assertNotIn("['icon_path']", config.read_text())

    def test_customizes_existing_entrypoint_without_recursion(self):
        command = object()
        plugin = types.ModuleType("jupyter_vscode_proxy")
        plugin.setup_vscode = lambda: {"command": command, "launcher_entry": {"title": "VS Code", "icon_path": "plugin-default.svg"}}
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "jupyter_server_config.py"
            launcher.configure(config, None)
            with patch.dict(sys.modules, {"jupyter_vscode_proxy": plugin}):
                namespace = {}
                exec(config.read_text(), namespace)
                exec(config.read_text(), namespace)
                result = plugin.setup_vscode()
        self.assertIs(result["command"], command)
        self.assertEqual(result["launcher_entry"], {"title": "VS Code", "icon_path": "plugin-default.svg"})
