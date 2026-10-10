import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("runtime_versions", Path(__file__).parents[1] / "scripts/runtime_versions.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RuntimeVersionTest(unittest.TestCase):
    def test_ignores_code_server_initialization_timestamp(self):
        output = "[2026-10-09T14:20:30.305Z] info Wrote default config\n4.114.0 abc123 with Code 1.114.0\n"
        self.assertEqual(module.parse_tool_version(output), "4.114.0")

    def test_other_tools_and_missing_version(self):
        self.assertEqual(module.parse_tool_version("conda 26.9.1\n"), "26.9.1")
        self.assertEqual(module.parse_tool_version("2.8.1\n"), "2.8.1")
        self.assertEqual(module.parse_tool_version("\x1b[1mbtop version: \x1b[0m1.4.6\n"), "1.4.6")
        with self.assertRaises(ValueError):
            module.parse_tool_version("[2026-10-09] initializing\n")
