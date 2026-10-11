"""Mocked, offline tests for allowlisted primary-source capture."""

import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
import primary_source_capture as capture_module  # noqa: E402


class PrimarySourceCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def completed(payload, *, returncode=0, stderr=b""):
        if isinstance(payload, bytes):
            stdout = payload
        else:
            stdout = json.dumps(payload).encode("utf-8")
        return type("Completed", (), {
            "returncode": returncode, "stdout": stdout, "stderr": stderr,
        })()

    def receipts(self, directory=None):
        return list((directory or self.root).glob("*/receipt.json"))

    def test_rejects_nonallowlisted_urls_credentials_options_and_path_traversal(self):
        invalid_urls = [
            "http://github.com/osac-project/repo/blob/main/README.md",
            "https://github.com.evil.test/osac-project/repo/blob/main/README.md",
            "https://user:secret@github.com/osac-project/repo/blob/main/README.md",
            "https://github.com:443/osac-project/repo/blob/main/README.md",
            "https://github.com/osac-project/repo/blob/main/README.md?download=1",
            "https://github.com/osac-project/repo/tree/main/README.md",
            "https://github.com/osac-project/repo/blob/main/%2e%2e/secret.md",
            "https://github.com/osac-project/repo/blob/main/%252e%252e/secret.md",
            "https://github.com/osac-project/repo/blob/main/dir/%2F..%2Fsecret.md",
            "https://@github.com/osac-project/repo/blob/main/README.md",
            "https://user@redhat.atlassian.net/browse/OSAC-17",
            "https://redhat.atlassian.net:443/browse/OSAC-17",
            "https://redhat.atlassian.net/browse/OSAC-17?fields=summary",
            "https://redhat.atlassian.net/browse/OSAC-0",
        ]
        with patch.object(capture_module.subprocess, "run") as run:
            for index, url in enumerate(invalid_urls):
                with self.subTest(url=url):
                    result = capture_module.capture(url, self.root)
                    self.assertEqual("unavailable", result["status"])
                    self.assertTrue(Path(result["receipt_path"]).is_file())
                    self.assertFalse(Path(result.get("capture_path", "/nonexistent")).exists())
            run.assert_not_called()
        self.assertEqual(len(invalid_urls), len(self.receipts()))

    def test_failed_receipt_does_not_persist_userinfo_credentials(self):
        rejected_urls = [
            "https://reader:top-secret@github.com/osac-project/repo/blob/main/README.md",
            "https://github.com/osac-project/repo/blob/main/README.md?access_token=query-secret",
        ]
        with patch.object(capture_module.subprocess, "run") as run:
            for index, url in enumerate(rejected_urls):
                with self.subTest(url=url):
                    result = capture_module.capture(url, self.root)
                    receipt_text = Path(result["receipt_path"]).read_text()
                    self.assertNotIn("top-secret", receipt_text)
                    self.assertNotIn("query-secret", receipt_text)
                    self.assertNotIn("reader", receipt_text)
        run.assert_not_called()

    def test_jira_uses_only_the_readonly_raw_issue_view_and_verifies_identity(self):
        issue = {
            "key": "OSAC-17",
            "fields": {"updated": "2026-10-01T12:30:00.000+0000", "summary": "A scope item"},
            "renderedFields": {"description": "Rendered description"},
        }
        url = "https://redhat.atlassian.net/browse/OSAC-17"
        with patch.object(capture_module.subprocess, "run", return_value=self.completed(issue)) as run:
            result = capture_module.capture(url, self.root)

        self.assertEqual("captured", result["status"])
        self.assertEqual(issue["fields"]["updated"], result["metadata"]["updated"])
        self.assertIn('"renderedFields"', result["text"])
        self.assertEqual(["jira", "issue", "view", "OSAC-17", "--raw", "--comments", "100"],
                         run.call_args.args[0])
        self.assertEqual({"capture_output": True, "timeout": 90, "check": False}, run.call_args.kwargs)
        stored = Path(result["capture_path"]).read_bytes()
        self.assertEqual(result["sha256"], hashlib.sha256(stored).hexdigest())

        with patch.object(capture_module.subprocess, "run", return_value=self.completed({
                **issue, "key": "OSAC-18"})) as run:
            wrong = capture_module.capture(url, self.root)
        self.assertEqual("unavailable", wrong["status"])
        self.assertIn("different issue", wrong["error"])
        self.assertFalse(Path(wrong.get("capture_path", "/nonexistent")).exists())
        self.assertTrue(Path(wrong["receipt_path"]).is_file())
        self.assertEqual(1, run.call_count)

    def test_gh_file_reads_are_get_only_and_content_is_pinned_to_resolved_commit(self):
        revision = "a" * 40
        commit = {"sha": revision, "commit": {"committer": {"date": "2026-09-30T10:00:00Z"}}}
        file_text = "# Source\nA captured primary source.\n"
        content = {
            "type": "file", "encoding": "base64",
            "content": base64.b64encode(file_text.encode()).decode(),
            "sha": "blob-sha-1",
        }
        url = "https://github.com/osac-project/ai-skills/blob/main/skills/README.md"
        with patch.object(capture_module.subprocess, "run",
                          side_effect=[self.completed(commit), self.completed(content)]) as run:
            result = capture_module.capture(url, self.root)

        self.assertEqual("captured", result["status"])
        self.assertEqual(file_text, result["text"])
        self.assertEqual(revision, result["revision"])
        self.assertEqual(
            f"https://github.com/osac-project/ai-skills/blob/{revision}/skills/README.md",
            result["resolved_url"],
        )
        self.assertEqual([
            ["gh", "api", "--method", "GET", "repos/osac-project/ai-skills/commits/main"],
            ["gh", "api", "--method", "GET",
             f"repos/osac-project/ai-skills/contents/skills/README.md?ref={revision}"],
        ], [call.args[0] for call in run.call_args_list])
        for call in run.call_args_list:
            self.assertEqual({"capture_output": True, "timeout": 90, "check": False}, call.kwargs)
        self.assertEqual(revision, result["revision"])
        self.assertEqual("main", result["metadata"]["requested_ref"])
        self.assertEqual(file_text.encode(), Path(result["capture_path"]).read_bytes())

    def test_failed_requests_keep_a_sanitized_receipt(self):
        url = "https://redhat.atlassian.net/browse/OSAC-17"
        with patch.object(capture_module.subprocess, "run",
                          return_value=self.completed(b"", returncode=1,
                                                      stderr=b"token=do-not-persist")):
            result = capture_module.capture(url, self.root)
        self.assertEqual("unavailable", result["status"])
        self.assertTrue(Path(result["receipt_path"]).is_file())
        receipt = json.loads(Path(result["receipt_path"]).read_text())
        self.assertEqual("unavailable", receipt["status"])
        self.assertIn("error", receipt)
        self.assertNotIn("do-not-persist", json.dumps(receipt))
        self.assertFalse(Path(result.get("capture_path", "/nonexistent")).exists())

    def test_nontext_or_oversized_github_files_fail_with_receipts(self):
        revision = "b" * 40
        commit = {"sha": revision, "commit": {"committer": {"date": "2026-10-01T00:00:00Z"}}}
        url = "https://github.com/osac-project/repo/blob/main/data.txt"
        binary = {
            "type": "file", "encoding": "base64",
            "content": base64.b64encode(b"\xff\x00binary").decode(),
        }
        with patch.object(capture_module.subprocess, "run",
                          side_effect=[self.completed(commit), self.completed(binary)]):
            nontext = capture_module.capture(url, self.root)
        self.assertEqual("unavailable", nontext["status"])
        self.assertIn("receipt_path", nontext)
        self.assertTrue(Path(nontext["receipt_path"]).is_file())
        self.assertFalse(Path(nontext.get("capture_path", "/nonexistent")).exists())

        oversized = {
            "type": "file", "encoding": "base64",
            "content": base64.b64encode(b"x" * (capture_module.MAX_BYTES + 1)).decode(),
        }
        with patch.object(capture_module.subprocess, "run",
                          side_effect=[self.completed(commit), self.completed(oversized)]):
            too_large = capture_module.capture(url, self.root)
        self.assertEqual("unavailable", too_large["status"])
        self.assertIn("size limit", too_large["error"])
        self.assertTrue(Path(too_large["receipt_path"]).is_file())

    def test_jira_response_shape_errors_still_leave_a_failed_receipt(self):
        url = "https://redhat.atlassian.net/browse/OSAC-17"
        with patch.object(capture_module.subprocess, "run", return_value=self.completed([])):
            result = capture_module.capture(url, self.root)
        self.assertEqual("unavailable", result["status"])
        self.assertTrue(Path(result["receipt_path"]).is_file())
        self.assertFalse(Path(result.get("capture_path", "/nonexistent")).exists())

    def test_valid_utf8_with_binary_nul_is_rejected(self):
        revision = "c" * 40
        commit = {"sha": revision, "commit": {"committer": {"date": "2026-10-01T00:00:00Z"}}}
        content = {
            "type": "file", "encoding": "base64",
            "content": base64.b64encode(b"looks like text\x00but contains a binary NUL").decode(),
        }
        url = "https://github.com/osac-project/repo/blob/main/text.txt"
        with patch.object(capture_module.subprocess, "run",
                          side_effect=[self.completed(commit), self.completed(content)]):
            result = capture_module.capture(url, self.root)
        self.assertEqual("unavailable", result["status"])
        self.assertTrue(Path(result["receipt_path"]).is_file())
        self.assertFalse(Path(result.get("capture_path", "/nonexistent")).exists())


if __name__ == "__main__":
    unittest.main()
