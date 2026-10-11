"""Client configuration and safe error checks; no live MCP calls."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("ask_persona", Path(__file__).resolve().parents[1] / "ask_persona.py")
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class ClientChecks(unittest.TestCase):
    def test_env_credentials_used_without_artifact_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text('[mcp_servers.chai_osac_public]\nurl="https://example.org/mcp"\nbearer_token_env_var="PILOT_TEST_TOKEN"\n')
            with patch.dict(os.environ, {"PILOT_TEST_TOKEN": "test-only"}):
                url, headers = client.connection(path, "chai_osac_public")
                self.assertEqual("https://example.org/mcp", url)
                self.assertEqual("Bearer test-only", headers["Authorization"])

    def test_missing_credentials_report_no_secret_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text('[mcp_servers.chai_osac_public]\nurl="https://example.org/mcp"\nbearer_token_env_var="MISSING_PILOT_TOKEN"\n')
            with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
                client.connection(path, "chai_osac_public")

    def test_errors_never_include_exception_text(self):
        error = TimeoutError("sensitive endpoint details")
        self.assertEqual(["TimeoutError"], client.failure_types(error))


if __name__ == "__main__": unittest.main()
