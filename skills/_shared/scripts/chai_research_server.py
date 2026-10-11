#!/usr/bin/env python3
"""Read-only stdio MCP bridge to the configured Chai ask_persona tool."""

import argparse
import logging
import os
import time
from pathlib import Path

from ask_persona import connection as codex_connection
from ask_persona import failure_types, research


UPSTREAM_TIMEOUT_SECONDS = 900
DEFAULT_SERVER = "chai_osac_public"


class ConnectionConfigurationError(Exception):
    """A connection setup error with no endpoint, credential, or raw details."""


def resolve_connection(config=None, server=DEFAULT_SERVER):
    if config is not None:
        try:
            return codex_connection(config, server)
        except Exception:
            raise ConnectionConfigurationError from None

    url = os.environ.get("CHAI_OSAC_PUBLIC_MCP_URL")
    token = os.environ.get("CHAI_OSAC_PUBLIC_MCP_TOKEN")
    if not url or not token:
        raise ConnectionConfigurationError
    return url, {"Authorization": f"Bearer {token}"}


def answer_text(result):
    blocks = result.get("content", []) if isinstance(result, dict) else []
    return "\n\n".join(
        block["text"] for block in blocks
        if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)
    ).strip()


def create_server(*, config=None, server=DEFAULT_SERVER, fastmcp_cls=None):
    if fastmcp_cls is None:
        try:
            from mcp.server.fastmcp import FastMCP
        except ImportError as exc:
            raise RuntimeError("Install the optional 'mcp' package to run the Chai research bridge.") from exc
        fastmcp_cls = FastMCP

    app = fastmcp_cls("chai-osac-research-bridge", log_level="WARNING")
    # Stdio stderr is often surfaced by clients; omit endpoint/session logging.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("mcp.client.streamable_http").setLevel(logging.WARNING)

    @app.tool()
    async def ask_persona(question: str) -> dict:
        """Ask one read-only Chai organizational research question."""
        started = time.monotonic()
        try:
            if not question.strip():
                return {
                    "answer": "A non-empty research question is required.",
                    "research_status": "unavailable",
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "error_types": ["ValueError"],
                }
            url, headers = resolve_connection(config, server)
            result = await research(url, headers, question, UPSTREAM_TIMEOUT_SECONDS)
            if not isinstance(result, dict) or result.get("isError"):
                return {
                    "answer": "Chai research returned an unavailable response.",
                    "research_status": "unavailable",
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "error_types": ["ToolError"],
                }
            return {
                "answer": answer_text(result),
                "research_status": "available",
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
        except ConnectionConfigurationError as exc:
            message = (
                "Chai research is not configured. Set CHAI_OSAC_PUBLIC_MCP_URL and "
                "CHAI_OSAC_PUBLIC_MCP_TOKEN, or pass --config and --server."
                if config is None else
                "Chai research configuration is unavailable; check the selected Codex MCP server."
            )
            return {
                "answer": message,
                "research_status": "unavailable",
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "error_types": failure_types(exc),
            }
        except Exception as exc:
            types = failure_types(exc)
            timed_out = any("Timeout" in name for name in types)
            return {
                "answer": "Chai research timed out." if timed_out else "Chai research is unavailable.",
                "research_status": "timeout" if timed_out else "unavailable",
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "error_types": types,
            }

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="Optional Codex TOML MCP configuration.")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="MCP server name in --config.")
    args = parser.parse_args()
    create_server(config=args.config, server=args.server).run(transport="stdio")


if __name__ == "__main__":
    main()
