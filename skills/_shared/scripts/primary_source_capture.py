#!/usr/bin/env python3
"""Capture an authenticated, read-only Jira or GitHub primary source.

This captures source bytes and provenance, not a verdict that a claim is true.
It intentionally supports only OSAC Jira issues and explicit GitHub resources.
The caller supplies the capture directory; each request creates fresh files.
"""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import quote, unquote, urlsplit
import uuid

MAX_BYTES = 1_000_000
NAME = re.compile(r"[A-Za-z0-9_.-]+\Z")


def api(path):
    return command(["gh", "api", "--method", "GET", path])


def command(argv):
    result = subprocess.run(argv, capture_output=True, timeout=90, check=False)
    if result.returncode:
        raise RuntimeError("read-only source request failed")
    if len(result.stdout) > MAX_BYTES:
        raise ValueError("source exceeds capture size limit")
    data = json.loads(result.stdout.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("primary source response must be a JSON object")
    return data


def identify(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username is not None or parsed.password is not None or parsed.port:
        raise ValueError("source must be an HTTPS URL without credentials or a port")
    if parsed.query:
        raise ValueError("source query parameters are unsupported")
    parts = [unquote(part) for part in parsed.path.strip("/").split("/")]
    if any(re.search(r"%[0-9a-fA-F]{2}", part) for part in parts):
        raise ValueError("nested URL encoding is unsupported")
    if parsed.hostname == "redhat.atlassian.net":
        if len(parts) != 2 or parts[0] != "browse" or not re.fullmatch(r"OSAC-[1-9][0-9]*", parts[1]):
            raise ValueError("only explicit OSAC Jira issue URLs are supported")
        return ("jira", parts[1])
    if parsed.hostname not in {"github.com", "raw.githubusercontent.com"}:
        raise ValueError("unsupported primary source host")
    if len(parts) < 4 or not all(NAME.fullmatch(part) and part not in {".", ".."} for part in parts[:2]):
        raise ValueError("invalid GitHub repository URL")
    owner, repo = parts[:2]
    if parsed.hostname == "raw.githubusercontent.com":
        kind, ref, path = "file", parts[2], parts[3:]
    elif parts[2] in {"blob", "raw"} and len(parts) >= 5:
        kind, ref, path = "file", parts[3], parts[4:]
    elif parts[2] in {"pull", "issues"} and len(parts) == 4 and re.fullmatch(r"[1-9][0-9]*", parts[3]):
        return ("github_" + parts[2], owner, repo, parts[3])
    elif parts[2] == "commit" and len(parts) == 4 and re.fullmatch(r"[0-9a-fA-F]{7,40}", parts[3]):
        return ("github_commit", owner, repo, parts[3])
    else:
        raise ValueError("use an explicit GitHub blob, raw file, PR, issue, or commit URL")
    if not ref or any(part in {"", ".", ".."} or "/" in part or "\x00" in part for part in [ref, *path]):
        raise ValueError("invalid GitHub file path")
    return (kind, owner, repo, ref, "/".join(path))


def capture(url, output_dir):
    """Return a receipt plus text; persist failed attempts as well as captures."""
    observed = datetime.now(timezone.utc).isoformat()
    directory = Path(output_dir).resolve() / (hashlib.sha256(url.encode()).hexdigest()[:16] + "-" + uuid.uuid4().hex[:12])
    directory.mkdir(parents=True, exist_ok=False)
    try:
        parsed = urlsplit(url)
        safe_url = parsed._replace(netloc=parsed.hostname or "", query="", fragment="").geturl()
    except ValueError:
        safe_url = "invalid-url"
    receipt = {"schema_version": 1, "url": safe_url, "observed_at": observed,
               "status": "unavailable", "revision": None,
               "receipt_path": str(directory / "receipt.json")}
    try:
        target = identify(url)
        revision = None
        resolved_url = url
        if target[0] == "jira":
            key = target[1]
            raw = command(["jira", "issue", "view", key, "--raw", "--comments", "100"])
            if raw.get("key") != key:
                raise ValueError("Jira response identifies a different issue")
            # JSON preserves the original ADF, issue status, timestamps and comments.
            body = json.dumps(raw, indent=2, ensure_ascii=False) + "\n"
            metadata = {"issue_key": key, "updated": raw.get("fields", {}).get("updated")}
        elif target[0] == "file":
            _, owner, repo, ref, path = target
            commit = api(f"repos/{owner}/{repo}/commits/{quote(ref, safe='')}")
            revision = commit.get("sha")
            if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
                raise ValueError("GitHub did not resolve an immutable commit")
            raw = api(f"repos/{owner}/{repo}/contents/{quote(path, safe='/')}?ref={revision}")
            if raw.get("type") != "file" or raw.get("encoding") != "base64":
                raise ValueError("GitHub resource is not a supported text file")
            data = base64.b64decode("".join(raw["content"].split()), validate=True)
            if len(data) > MAX_BYTES:
                raise ValueError("source exceeds capture size limit")
            body = data.decode("utf-8")
            resolved_url = f"https://github.com/{owner}/{repo}/blob/{revision}/{quote(path, safe='/')}"
            metadata = {"repository": f"{owner}/{repo}", "path": path,
                        "requested_ref": ref, "blob_sha": raw.get("sha"),
                        "commit_date": commit.get("commit", {}).get("committer", {}).get("date")}
        else:
            _, owner, repo, identifier = target
            endpoint = {"github_pull": "pulls", "github_issues": "issues", "github_commit": "commits"}[target[0]]
            raw = api(f"repos/{owner}/{repo}/{endpoint}/{identifier}")
            body = json.dumps(raw, indent=2, ensure_ascii=False) + "\n"
            if target[0] == "github_commit":
                revision = raw.get("sha")
            elif target[0] == "github_pull":
                revision = raw.get("merge_commit_sha") if raw.get("merged") else raw.get("head", {}).get("sha")
            metadata = {"repository": f"{owner}/{repo}", "resource": target[0],
                        "updated": raw.get("updated_at"), "state": raw.get("state"),
                        "merged": raw.get("merged"), "merged_at": raw.get("merged_at")}
        if "\x00" in body:
            raise ValueError("binary sources are unsupported")
        data = body.encode("utf-8")
        if len(data) > MAX_BYTES:
            raise ValueError("source exceeds capture size limit")
        capture_path = directory / "source.txt"
        capture_path.write_bytes(data)
        receipt.update(status="captured", capture_path=str(capture_path),
                       sha256=hashlib.sha256(data).hexdigest(), revision=revision,
                       resolved_url=resolved_url, metadata=metadata)
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired, KeyError, TypeError, AttributeError) as error:
        # Never save arbitrary command stderr, environment variables or credentials.
        receipt["error"] = str(error) if isinstance(error, (ValueError, RuntimeError)) else type(error).__name__
    Path(receipt["receipt_path"]).write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    return {**receipt, **({"text": body} if receipt["status"] == "captured" else {})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="action", required=True)
    action = subcommands.add_parser("capture")
    action.add_argument("url")
    action.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    receipt = capture(args.url, args.output_dir)
    print(json.dumps(receipt, ensure_ascii=False))
    return 0 if receipt["status"] == "captured" else 1


if __name__ == "__main__":
    raise SystemExit(main())
