"""Regression tests: an unapproved update must never proceed."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "check_release.py"
spec = importlib.util.spec_from_file_location("check_release", MODULE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class GateTests(unittest.TestCase):
    def test_missing_config_fails(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "No approved"):
                gate.check(Path(td) / "release.json")

    def test_empty_and_pretend_approval_fail(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "release.json"
            for payload in ({}, {"status": "approved"}, {"status": "approved", **{
                name: True for name in gate.REQUIRED}}):
                path.write_text(json.dumps(payload))
                with self.assertRaises(ValueError):
                    gate.check(path)

    def test_private_paths_and_sensitive_files_are_ignored(self):
        patterns = (Path(__file__).resolve().parents[1] / ".gitignore").read_text()
        for marker in (".env", "snapshots/", "private/", "*.token"):
            self.assertIn(marker, patterns)

    def test_schedule_is_opt_in_and_does_not_publish(self):
        path = Path(__file__).resolve().parents[1] / ".github/workflows/daily-refresh.yml"
        text = path.read_text()
        self.assertIn("vars.PUBLIC_CATALOG_UPDATES_ENABLED == 'true'", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("wrangler deploy", text)
        self.assertNotIn("CLOUDFLARE_API_TOKEN", text)


if __name__ == "__main__":
    unittest.main()
