import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).parents[1]


def run_cli(*args, data=None):
    return subprocess.run([sys.executable, "-m", "logshare", *args], input=data,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ROOT)


class CliTests(unittest.TestCase):
    def test_stdin_json_and_utf8(self):
        result = run_cli("-", "--format", "json", data="中文 password=example-secret".encode())
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertIn("中文", output["sanitized_log"])
        self.assertNotIn(b"example-secret", result.stdout)

    def test_existing_output_and_input_protection(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "input.log"
            target = Path(folder) / "report.md"
            source.write_text("hello", encoding="utf-8")
            target.write_text("keep", encoding="utf-8")
            self.assertEqual(run_cli(str(source), "-o", str(target)).returncode, 2)
            self.assertEqual(target.read_text(), "keep")
            self.assertEqual(run_cli(str(source), "-o", str(source), "--force").returncode, 2)
            self.assertEqual(source.read_text(), "hello")
            self.assertEqual(run_cli(str(source), "-o", str(target), "--force").returncode, 0)

    def test_hardlink_cannot_overwrite_input(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "input.log"
            alias = Path(folder) / "alias.log"
            source.write_text("keep", encoding="utf-8")
            try:
                os.link(source, alias)
            except OSError:
                self.skipTest("hardlinks not available")
            self.assertEqual(run_cli(str(source), "-o", str(alias), "--force").returncode, 2)
            self.assertEqual(source.read_text(), "keep")

    def test_literals_file_and_custom_key(self):
        with tempfile.TemporaryDirectory() as folder:
            values = Path(folder) / "local.secrets"
            values.write_text("private-project\n", encoding="utf-8")
            args = ["-", "--redact-file", str(values), "--redact-key", "tenant", "--format", "text"]
            result = run_cli(*args, data=b"private-project tenant=example-value")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(b"private-project", result.stdout)
            self.assertNotIn(b"example-value", result.stdout)
            self.assertEqual(run_cli(*args, "-o", str(values), "--force", data=b"hello").returncode, 2)

    def test_legacy_encoding_and_invalid_bytes(self):
        source = "中文日志 password=example-secret".encode("gb18030")
        failed = run_cli("-", data=source)
        self.assertEqual(failed.returncode, 2)
        self.assertNotIn(b"example-secret", failed.stderr)
        result = run_cli("-", "--encoding", "gb18030", "--format", "text", data=source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("中文日志", result.stdout.decode())

    def test_missing_file_error_does_not_echo_private_path(self):
        result = run_cli("/missing/private-project/application.log")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(b"private-project", result.stderr)

    def test_input_size_limit(self):
        result = run_cli("-", data=b"a" * (20 * 1024 * 1024 + 1))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")

    def test_version_and_help(self):
        self.assertEqual(run_cli("--version").returncode, 0)
        self.assertEqual(run_cli("--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()
