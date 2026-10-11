"""Read-only Chai MCP bridge tests using a fake FastMCP and mocked upstream."""

import asyncio
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import chai_research_server as bridge  # noqa: E402


class FakeFastMCP:
    def __init__(self, name, **kwargs):
        self.name = name
        self.tools = {}

    def tool(self):
        def register(function):
            self.tools[function.__name__] = function
            return function
        return register


class ChaiResearchServerTests(unittest.TestCase):
    def make_server(self, **kwargs):
        return bridge.create_server(fastmcp_cls=FakeFastMCP, **kwargs)

    def test_exposes_only_ask_persona(self):
        app = self.make_server()
        self.assertEqual("chai-osac-research-bridge", app.name)
        self.assertEqual(["ask_persona"], list(app.tools))

    def test_forwards_question_with_900_second_timeout(self):
        app = self.make_server()
        upstream = AsyncMock(return_value={
            "isError": False,
            "content": [
                {"type": "text", "text": "Accepted decision with source [1]."},
                {"type": "image", "data": "ignored"},
            ],
        })
        headers = {"Authorization": "Bearer private-token"}
        with patch.object(bridge, "resolve_connection", return_value=("https://chai.example/mcp", headers)), \
             patch.object(bridge, "research", upstream):
            result = asyncio.run(app.tools["ask_persona"]("What is the approved scope?"))

        upstream.assert_awaited_once_with(
            "https://chai.example/mcp", headers,
            "What is the approved scope?", 900,
        )
        self.assertEqual("Accepted decision with source [1].", result["answer"])
        self.assertEqual("available", result["research_status"])
        self.assertGreaterEqual(result["elapsed_seconds"], 0)
        self.assertNotIn("https://chai.example/mcp", str(result))
        self.assertNotIn("private-token", str(result))

    def test_timeout_reports_only_safe_type_names(self):
        app = self.make_server()
        message = "request to https://private.example with token super-secret timed out"
        with patch.object(bridge, "resolve_connection", return_value=("https://private.example", {})), \
             patch.object(bridge, "research", AsyncMock(side_effect=TimeoutError(message))):
            result = asyncio.run(app.tools["ask_persona"]("Ask a question"))

        self.assertEqual("timeout", result["research_status"])
        self.assertEqual(["TimeoutError"], result["error_types"])
        self.assertEqual("Chai research timed out.", result["answer"])
        for secret in (message, "https://private.example", "super-secret"):
            self.assertNotIn(secret, str(result))

    def test_other_upstream_error_is_sanitized(self):
        app = self.make_server()
        with patch.object(bridge, "resolve_connection", return_value=("https://private.example", {})), \
             patch.object(bridge, "research", AsyncMock(side_effect=RuntimeError("private endpoint and token"))):
            result = asyncio.run(app.tools["ask_persona"]("Ask a question"))

        self.assertEqual("unavailable", result["research_status"])
        self.assertEqual(["RuntimeError"], result["error_types"])
        self.assertNotIn("private endpoint and token", str(result))

    def test_missing_environment_configuration_is_clear_and_safe(self):
        app = self.make_server()
        upstream = AsyncMock()
        with patch.dict("os.environ", {}, clear=True), patch.object(bridge, "research", upstream):
            result = asyncio.run(app.tools["ask_persona"]("Ask a question"))

        self.assertEqual("unavailable", result["research_status"])
        self.assertIn("CHAI_OSAC_PUBLIC_MCP_URL", result["answer"])
        self.assertIn("CHAI_OSAC_PUBLIC_MCP_TOKEN", result["answer"])
        self.assertEqual(["ConnectionConfigurationError"], result["error_types"])
        upstream.assert_not_awaited()

    def test_codex_config_selects_named_upstream_server(self):
        app = self.make_server(config=Path("codex.toml"), server="chai")
        upstream = AsyncMock(return_value={"content": [{"type": "text", "text": "answer"}]})
        headers = {"Authorization": "Bearer configured-secret"}
        with patch.object(bridge, "codex_connection", return_value=("https://chai.example/mcp", headers)) as config, \
             patch.object(bridge, "research", upstream):
            result = asyncio.run(app.tools["ask_persona"]("Ask a question"))

        config.assert_called_once_with(Path("codex.toml"), "chai")
        self.assertEqual("available", result["research_status"])
        self.assertNotIn("configured-secret", str(result))


if __name__ == "__main__":
    unittest.main()
