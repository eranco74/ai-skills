#!/usr/bin/env python3
"""Call the configured Chai research tool with a configurable long timeout.

Requires the optional `mcp` Python package. Credentials remain in environment
variables referenced by Codex's TOML config; request/response artifacts omit them.
"""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import ssl
import time
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10; `mcp` requires 3.10 or later.
    import tomli as tomllib


def connection(config_path, server):
    config = tomllib.loads(Path(config_path).read_text())
    settings = config.get("mcp_servers", {}).get(server)
    if not settings or "url" not in settings:
        raise ValueError("Select a configured streamable HTTP MCP server")
    headers = dict(settings.get("http_headers", {}))
    for name, variable in settings.get("env_http_headers", {}).items():
        if variable not in os.environ:
            raise ValueError("A configured header environment variable is missing")
        headers[name] = os.environ[variable]
    variable = settings.get("bearer_token_env_var")
    if variable:
        if not os.environ.get(variable):
            raise ValueError("The configured bearer-token environment variable is missing")
        headers["Authorization"] = "Bearer " + os.environ[variable]
    return settings["url"], headers


async def research(url, headers, question, timeout):
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    # HTTP stream and JSON-RPC tool timeouts both need to cover a slow persona.
    limits = httpx.Timeout(timeout, connect=30.0)
    async with httpx.AsyncClient(headers=headers, timeout=limits, verify=ssl.create_default_context()) as client:
        async with streamable_http_client(url, http_client=client) as (read, write, _):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=timeout)) as session:
                await session.initialize()
                result = await session.call_tool(
                    "ask_persona", {"question": question},
                    read_timeout_seconds=timedelta(seconds=timeout),
                )
                return result.model_dump(mode="json", by_alias=True, exclude_none=True)


def failure_types(exc):
    """Safe diagnostics for nested transport errors without endpoint/token text."""
    children = getattr(exc, "exceptions", ())
    return sorted(set([type(exc).__name__] + [name for child in children for name in failure_types(child)]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path.home() / ".codex/config.toml")
    parser.add_argument("--server", default="chai_osac_public")
    parser.add_argument("--timeout", type=float, default=900)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    question = args.question_file.read_text().strip()
    if not question:
        parser.error("The question file is empty")
    args.output.mkdir(parents=True, exist_ok=True)
    # Never overwrite a completed retrieval fixture accidentally.
    if (args.output / "response.json").exists() or (args.output / "request.json").exists():
        parser.error("The output already contains a request or response; use a new run directory")
    request = {
        "server": args.server, "tool": "ask_persona", "question": question,
        "question_sha256": hashlib.sha256(question.encode()).hexdigest(),
        "timeout_seconds": args.timeout,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with (args.output / "request.json").open("x") as request_file:
            request_file.write(json.dumps(request, indent=2) + "\n")
    except FileExistsError:
        parser.error("Another request already uses this output directory")
    started = time.monotonic()
    print(f"Waiting for {args.server}/ask_persona (up to {args.timeout:g}s)", flush=True)
    try:
        url, headers = connection(args.config, args.server)
        result = asyncio.run(research(url, headers, question, args.timeout))
        status = "error" if result.get("isError") else "available"
        response = {"status": status, "result": result}
        text = "\n\n".join(item.get("text", "") for item in result.get("content", []) if item.get("type") == "text")
        (args.output / "response.txt").write_text(text + "\n")
    except Exception as exc:
        # Exception text can include endpoint details; only record the type.
        names = failure_types(exc)
        response = {"status": "timeout" if any("Timeout" in name for name in names) else "unavailable",
                    "error_types": names}
    response.update({
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    })
    try:
        response["mcp_sdk_version"] = importlib.metadata.version("mcp")
    except importlib.metadata.PackageNotFoundError:
        response["mcp_sdk_version"] = None
    (args.output / "response.json").write_text(json.dumps(response, indent=2) + "\n")
    print(json.dumps({key: response[key] for key in ("status", "elapsed_seconds")}))
    return 0 if response["status"] == "available" else 1


if __name__ == "__main__":
    raise SystemExit(main())
