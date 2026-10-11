#!/usr/bin/env python3
"""
Design Creator Pipeline State Machine.

Thin dispatcher modeled on prd-creator's pipeline_state.py.
Manages phases, transitions, wave dispatch, and barrier synchronization
for autonomous design document generation.

Pipeline:
  BATCH_START → FETCH → FETCH_PRD → GENERATE → ASSESS → REVIEW → REVISE → FIXUP
  → REASSESS_CHECK → [REASSESS loop max 2] → REPORT → DONE

Usage:
  python3 scripts/pipeline_state.py init [--batch-size N] [--headless]
  python3 scripts/pipeline_state.py next-action
  python3 scripts/pipeline_state.py wait-for-wave
  python3 scripts/pipeline_state.py set key=value ...
  python3 scripts/pipeline_state.py set-phase PHASE
  python3 scripts/pipeline_state.py get-phase
  python3 scripts/pipeline_state.py run-phase
"""

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import yaml
import uuid
from datetime import datetime, timezone
from pathlib import Path


STATE_FILE = Path("tmp/pipeline-state.yaml")
DISPATCH_MARKER = Path("tmp/.dispatch-marker")

PHASE_CONFIG = {
    "BATCH_START": {
        "type": "noop",
        "next": "FETCH",
    },
    "FETCH": {
        "type": "script",
        "command": "fetch_all",
        "ids_file": "tmp/pipeline-active-ids.txt",
        "next": "FETCH_PRD",
    },
    "FETCH_PRD": {
        "type": "script",
        "command": "fetch_prd",
        "ids_file": "tmp/pipeline-active-ids.txt",
        "next": "RESEARCH",
    },
    "RESEARCH": {
        "type": "agent",
        "prompt_file": "prompts/research-context.md",
        "ids_file": "tmp/pipeline-active-ids.txt",
        "poll_phase": "research",
        "research_stage": "design",
        "next": "GENERATE",
    },
    "GENERATE": {
        "type": "agent",
        "prompt_file": "prompts/generate-design.md",
        "ids_file": "tmp/pipeline-active-ids.txt",
        "poll_phase": "generate",
        "next": "ASSESS",
    },
    "ASSESS": {
        "type": "script",
        "command": "assess_all",
        "ids_file": "tmp/pipeline-active-ids.txt",
        "next": "REVIEW",
    },
    "REVIEW": {
        "type": "agent",
        "prompt_file": "prompts/review-design.md",
        "ids_file": "tmp/pipeline-active-ids.txt",
        "poll_phase": "review",
        "next": "REVISE",
    },
    "REVISE": {
        "type": "agent",
        "prompt_file": "prompts/revise-design.md",
        "ids_file": "tmp/pipeline-revise-ids.txt",
        "poll_phase": "revise",
        "next": "FIXUP",
    },
    "FIXUP": {
        "type": "script",
        "command": "fixup",
        "ids_file": "tmp/pipeline-active-ids.txt",
        "next": "REASSESS_CHECK",
    },
    "REASSESS_CHECK": {
        "type": "noop",
    },
    "REASSESS_ASSESS": {
        "type": "script",
        "command": "reassess",
        "ids_file": "tmp/pipeline-reassess-ids.txt",
        "next": "REASSESS_REVIEW",
    },
    "REASSESS_REVIEW": {
        "type": "agent",
        "prompt_file": "prompts/review-design.md",
        "ids_file": "tmp/pipeline-reassess-ids.txt",
        "poll_phase": "reassess_review",
        "next": "REASSESS_REVISE",
    },
    "REASSESS_REVISE": {
        "type": "agent",
        "prompt_file": "prompts/revise-design.md",
        "ids_file": "tmp/pipeline-reassess-revise-ids.txt",
        "poll_phase": "reassess_revise",
        "next": "REASSESS_FIXUP",
    },
    "REASSESS_FIXUP": {
        "type": "script",
        "command": "fixup",
        "ids_file": "tmp/pipeline-reassess-ids.txt",
        "next": "REASSESS_CHECK",
    },
    "REPORT": {
        "type": "script",
        "command": "report",
        "ids_file": "tmp/pipeline-all-ids.txt",
        "next": "DONE",
    },
    "DONE": {
        "type": "noop",
    },
}

MAIN_SEQUENCE = ["FETCH", "FETCH_PRD", "RESEARCH", "GENERATE", "ASSESS", "REVIEW", "REVISE", "FIXUP"]
REASSESS_SEQUENCE = ["REASSESS_ASSESS", "REASSESS_REVIEW", "REASSESS_REVISE", "REASSESS_FIXUP"]


def load_state():
    if not STATE_FILE.exists():
        return {}
    with open(STATE_FILE) as f:
        return yaml.safe_load(f) or {}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        yaml.dump(state, f, default_flow_style=False)


def read_ids(path):
    p = Path(path)
    if not p.exists():
        return []
    return [line.strip() for line in p.read_text().splitlines() if line.strip()]


def write_ids(path, ids):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(sorted(set(ids))) + "\n" if ids else "")


def replay_record_for(state, feature_key):
    """Resolve a replay fixture path, allowing a directory of per-feature records."""
    replay_record = state.get("replay_record")
    if not replay_record:
        return ""
    path = Path(replay_record)
    if path.is_dir():
        path = path / f"{feature_key}-research.json"
    return str(path)


def check_design_exists(design_id):
    return design_document_path(design_id).exists()


def design_document_path(design_id):
    """Canonical standalone design output path used by generation and bridge."""
    return Path(f"artifacts/design-tasks/{design_id}-design.md")


def design_original_path(design_id):
    """Canonical pre-revision backup path."""
    return Path(f"artifacts/design-originals/{design_id}-design.md")


def check_review_exists(design_id):
    return Path(f"artifacts/design-reviews/{design_id}-review.md").exists()


def has_unresolved_material_conflict(design_id):
    """Whether the design evidence record blocks readiness for this feature."""
    record_path = Path(f"artifacts/design-tasks/{design_id}-research.json")
    try:
        record = json.loads(record_path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(record, dict) or record.get("feature_key") != design_id or record.get("stage") != "design":
        return False
    conflicts = record.get("conflicts", [])
    return isinstance(conflicts, list) and any(
        isinstance(conflict, dict)
        and conflict.get("material") is True
        and conflict.get("resolved") is False
        for conflict in conflicts
    )


def coverage_blocks_readiness(design_id):
    """Require same-run coverage using the shared schema validator."""
    record_path = Path(f"artifacts/design-tasks/{design_id}-research.json")
    if not record_path.exists():
        return False  # Preserve compatibility with legacy reviews.
    try:
        record = json.loads(record_path.read_text())
        coverage = json.loads(Path(f"artifacts/design-reviews/{design_id}-coverage.json").read_text())
        helper_path = Path(__file__).resolve().parents[2] / "_shared/scripts/research_context.py"
        spec = importlib.util.spec_from_file_location("research_coverage_validator", helper_path)
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        if helper.validate_record(record, feature=design_id, stage="design"):
            return True
        if helper.validate_coverage(coverage, record):
            return True
    except (OSError, UnicodeDecodeError, ValueError, ImportError, AttributeError):
        return True
    scopes = {r["id"]: r["scope"] for r in record["requirements"]}
    return any(scopes[row["id"]] in {"in", "constraint"} and row["status"] != "covered"
               for row in coverage["requirements"])


def get_review_score(design_id):
    review_path = Path(f"artifacts/design-reviews/{design_id}-review.md")
    if not review_path.exists():
        return None
    content = review_path.read_text()
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        fm = yaml.safe_load(parts[1])
        if not isinstance(fm, dict):
            return None
        score, passed, recommendation = fm.get("score"), fm.get("pass"), fm.get("recommendation")
        if coverage_blocks_readiness(design_id):
            return score, False, "clarify"
        if has_unresolved_material_conflict(design_id):
            # Keep this out of automatic revision loops; an owner must resolve
            # the conflict before the result can be considered ready.
            return score, False, "clarify"
        return score, passed, recommendation
    except yaml.YAMLError:
        return None


def get_review_auto_revised(design_id):
    review_path = Path(f"artifacts/design-reviews/{design_id}-review.md")
    if not review_path.exists():
        return False
    content = review_path.read_text()
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False
    try:
        fm = yaml.safe_load(parts[1])
        return fm.get("auto_revised", False)
    except yaml.YAMLError:
        return False


def filter_for_revision(ids):
    """Return IDs that need revision (score < 5/8, not already passing)."""
    revise_ids = []
    for design_id in ids:
        result = get_review_score(design_id)
        if result is None:
            continue
        score, passed, recommendation = result
        if not passed and recommendation in ("revise", None):
            revise_ids.append(design_id)
    return revise_ids


def filter_for_reassess(ids):
    """Return IDs that were auto-revised but still failing."""
    reassess_ids = []
    for design_id in ids:
        result = get_review_score(design_id)
        if result is None:
            continue
        score, passed, recommendation = result
        if not passed and recommendation != "clarify" and get_review_auto_revised(design_id):
            reassess_ids.append(design_id)
    return reassess_ids


def fetch_all(ids):
    """Fetch Jira features for all IDs."""
    for design_id in ids:
        source_path = f"artifacts/design-tasks/{design_id}-source.md"
        if Path(source_path).exists():
            print(f"  {design_id}: source already exists, skipping", file=sys.stderr)
            continue
        try:
            subprocess.run(
                ["python3", "scripts/fetch_feature.py", design_id,
                 "--output", source_path],
                check=True, capture_output=True, text=True, timeout=60
            )
            print(f"  {design_id}: fetched", file=sys.stderr)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"  {design_id}: fetch failed: {e}", file=sys.stderr)


def fetch_prd(ids):
    """Fetch PRD for each design (from enhancement-proposals or artifacts)."""
    for design_id in ids:
        prd_path = f"artifacts/design-tasks/{design_id}-prd.md"
        if Path(prd_path).exists():
            print(f"  {design_id}: PRD already exists, skipping", file=sys.stderr)
            continue
        try:
            subprocess.run(
                ["python3", "scripts/fetch_prd.py", design_id,
                 "--output", prd_path],
                check=True, capture_output=True, text=True, timeout=60
            )
            print(f"  {design_id}: PRD fetched", file=sys.stderr)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"  {design_id}: PRD fetch failed: {e}", file=sys.stderr)


def assess_all(ids):
    """Run deterministic scoring checks on all designs."""
    for design_id in ids:
        design_path = str(design_document_path(design_id))
        if not Path(design_path).exists():
            print(f"  {design_id}: design not found, skipping assess", file=sys.stderr)
            continue
        results = {}
        checks = [
            "check-structure",
            "check-frontmatter",
            "check-proto",
            "check-tenant-isolation",
            "check-placeholders",
            "check-length"
        ]
        for check in checks:
            try:
                proc = subprocess.run(
                    ["python3", "scripts/score_design.py", check, design_path],
                    capture_output=True, text=True, timeout=30
                )
                results[check] = json.loads(proc.stdout) if proc.stdout.strip() else {"pass": False}
            except Exception as e:
                results[check] = {"pass": False, "issues": [str(e)]}

        all_pass = all(r.get("pass", False) for r in results.values())
        status = "PASS" if all_pass else "FAIL"
        issues = []
        for check, result in results.items():
            for issue in result.get("issues", []):
                issues.append(f"{check}: {issue}")
        print(f"  {design_id}: {status}" + (f" ({'; '.join(issues[:3])})" if issues else ""),
              file=sys.stderr)


def fixup(ids):
    """Validate auto_revised flags match actual content changes."""
    for design_id in ids:
        orig_path = design_original_path(design_id)
        task_path = design_document_path(design_id)
        review_path = Path(f"artifacts/design-reviews/{design_id}-review.md")
        if not orig_path.exists() or not task_path.exists() or not review_path.exists():
            continue
        orig_text = orig_path.read_text()
        task_text = task_path.read_text()
        actually_revised = orig_text.strip() != task_text.strip()
        try:
            subprocess.run(
                ["python3", "scripts/frontmatter.py", "set",
                 str(review_path), f"auto_revised={str(actually_revised).lower()}"],
                check=True, capture_output=True, timeout=10
            )
        except Exception:
            pass


def generate_report(ids):
    """Generate a pipeline run report."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    results = {"timestamp": timestamp, "total": len(ids), "per_design": []}
    passed = 0
    failed = 0
    revised = 0

    for design_id in ids:
        entry = {"id": design_id}
        result = get_review_score(design_id)
        if result:
            score, is_pass, recommendation = result
            entry["score"] = score
            entry["pass"] = is_pass
            entry["recommendation"] = recommendation
            if is_pass:
                passed += 1
            else:
                failed += 1
        if get_review_auto_revised(design_id):
            entry["auto_revised"] = True
            revised += 1
        results["per_design"].append(entry)

    results["passed"] = passed
    results["failed"] = failed
    results["revised"] = revised

    report_dir = Path("artifacts/pipeline-runs")
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report_path = report_dir / f"{ts}.yaml"
    with open(report_path, "w") as f:
        yaml.dump(results, f, default_flow_style=False)

    print(f"\n=== Pipeline Report ===", file=sys.stderr)
    print(f"Total: {len(ids)} | Passed: {passed} | Failed: {failed} | Revised: {revised}",
          file=sys.stderr)
    for entry in results["per_design"]:
        status = "PASS" if entry.get("pass") else "FAIL"
        rev = " (revised)" if entry.get("auto_revised") else ""
        print(f"  {entry['id']}: {entry.get('score', '?')}/8 {status}{rev}",
              file=sys.stderr)
    print(f"Report: {report_path}", file=sys.stderr)


def advance(state):
    """Determine and execute the next phase transition."""
    phase = state.get("phase", "DONE")

    if phase == "DONE":
        return

    config = PHASE_CONFIG.get(phase, {})

    if phase == "BATCH_START":
        batch = state.get("batch", 0) + 1
        state["batch"] = batch
        state["reassess_cycle"] = 0
        batch_file = f"tmp/pipeline-batch-{batch}-ids.txt"
        ids = read_ids(batch_file)
        write_ids("tmp/pipeline-active-ids.txt", ids)
        state["phase"] = "FETCH"
        save_state(state)
        return

    if phase == "REASSESS_CHECK":
        active_ids = read_ids("tmp/pipeline-active-ids.txt")
        reassess_ids = filter_for_reassess(active_ids)
        cycle = state.get("reassess_cycle", 0)

        if reassess_ids and cycle < 2:
            state["reassess_cycle"] = cycle + 1
            write_ids("tmp/pipeline-reassess-ids.txt", reassess_ids)
            revise_ids = filter_for_revision(reassess_ids)
            write_ids("tmp/pipeline-reassess-revise-ids.txt", revise_ids)
            state["phase"] = "REASSESS_ASSESS"
            save_state(state)
        else:
            state["phase"] = "REPORT"
            save_state(state)
        return

    next_phase = config.get("next")
    if next_phase:
        if next_phase == "REVISE":
            active_ids = read_ids("tmp/pipeline-active-ids.txt")
            revise_ids = filter_for_revision(active_ids)
            write_ids("tmp/pipeline-revise-ids.txt", revise_ids)

        state["phase"] = next_phase
        save_state(state)


def next_action(state):
    """Return the next action the orchestrator should take."""
    phase = state.get("phase", "DONE")
    config = PHASE_CONFIG.get(phase, {})
    phase_type = config.get("type", "noop")

    if phase == "DONE":
        print(yaml.dump({"action": "done", "phase": "DONE", "message": "Pipeline complete."}))
        return

    if phase_type == "noop":
        advance(state)
        state = load_state()
        return next_action(state)

    if phase_type == "script":
        ids_file = config.get("ids_file", "tmp/pipeline-active-ids.txt")
        ids = read_ids(ids_file)
        command = config["command"]
        print(yaml.dump({
            "action": "run_script",
            "phase": phase,
            "command": command,
            "ids_count": len(ids),
            "message": f"{phase}: {command} on {len(ids)} IDs",
        }))
        return

    if phase_type == "agent":
        ids_file = config.get("ids_file", "tmp/pipeline-active-ids.txt")
        ids = read_ids(ids_file)

        if not ids:
            advance(state)
            state = load_state()
            return next_action(state)

        agents = []
        for design_id in ids:
            stage = config.get("research_stage")
            research_record = f"artifacts/design-tasks/{design_id}-research.json"
            replay_record = replay_record_for(state, design_id)
            if stage and state.get("research_mode") == "replay":
                if Path(replay_record).resolve() == Path(research_record).resolve():
                    print(f"{design_id}: replay input must be separate from the current-run output record", file=sys.stderr)
                    sys.exit(1)
            agent_vars = [
                f"JIRA_KEY={design_id}",
                f"DESIGN_ID={design_id}",
                f"RESEARCH_MODE={state.get('research_mode', 'live')}",
                f"RESEARCH_RUN_ID={state.get('run_id', '')}",
                f"RESEARCH_RECORD={research_record}",
                f"RESEARCH_REPLAY_RECORD={replay_record}",
            ]
            if stage:
                agent_vars.append(f"RESEARCH_STAGE={stage}")
            agent = {
                "prompt_file": config["prompt_file"],
                "vars": "\n".join(agent_vars),
            }
            agents.append(agent)

        # Persist the exact dispatched wave so wait-for-wave cannot mistake a
        # stale marker from an earlier phase for the current agent run.
        write_ids("tmp/pipeline-wave-ids.txt", ids)
        state["wave_phase"] = phase
        state["wave_ids"] = ids
        save_state(state)

        print(yaml.dump({
            "action": "launch_wave",
            "phase": phase,
            "message": f"{phase}: {len(agents)} agents",
            "agents": agents,
        }))
        return


def run_phase(state):
    """Execute a script phase."""
    phase = state.get("phase", "DONE")
    config = PHASE_CONFIG.get(phase, {})
    command = config.get("command")
    ids_file = config.get("ids_file", "tmp/pipeline-active-ids.txt")
    ids = read_ids(ids_file)

    print(f"[{phase}] Running {command} on {len(ids)} IDs...", file=sys.stderr)

    if command == "fetch_all":
        fetch_all(ids)
    elif command == "fetch_prd":
        fetch_prd(ids)
    elif command == "assess_all":
        assess_all(ids)
    elif command == "fixup":
        fixup(ids)
    elif command == "reassess":
        assess_all(ids)
    elif command == "report":
        all_ids = read_ids("tmp/pipeline-all-ids.txt")
        generate_report(all_ids)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)

    DISPATCH_MARKER.parent.mkdir(parents=True, exist_ok=True)
    DISPATCH_MARKER.write_text(f"{phase}\n")

    advance(state)


def wait_for_wave():
    """Check if current wave of agents has completed."""
    state = load_state()
    phase = state.get("phase", "DONE")
    config = PHASE_CONFIG.get(phase, {})
    wave_ids = state.get("wave_ids") or read_ids("tmp/pipeline-wave-ids.txt")
    if not wave_ids or state.get("wave_phase") != phase:
        print("No dispatched agent wave for the current phase.", file=sys.stderr)
        sys.exit(3)

    pending = []
    completed = []
    for design_id in wave_ids:
        if phase == "RESEARCH":
            record = f"artifacts/design-tasks/{design_id}-research.json"
            validator = "../_shared/scripts/research_context.py"
            try:
                if state.get("research_mode") == "replay":
                    fixture = replay_record_for(state, design_id)
                    fixture_proc = subprocess.run(
                        ["python3", validator, "validate", fixture,
                         "--feature", design_id, "--stage", config["research_stage"]],
                        capture_output=True, text=True, timeout=10
                    )
                    if fixture_proc.returncode != 0:
                        pending.append(design_id)
                        detail = (fixture_proc.stderr or fixture_proc.stdout).strip()
                        print(f"  {design_id}: replay fixture pending: {detail or 'invalid or unavailable fixture'}", file=sys.stderr)
                        continue

                proc = subprocess.run(
                    ["python3", validator, "validate", record,
                     "--feature", design_id, "--stage", config["research_stage"],
                     "--run-id", str(state.get("run_id", "")),
                     "--mode", state.get("research_mode", "live")],
                    capture_output=True, text=True, timeout=10
                )
                if proc.returncode == 0:
                    # Derive the current brief deterministically from the validated
                    # record; an absent or stale agent-written brief cannot pass.
                    proc = subprocess.run(
                        ["python3", validator, "render", record,
                         "--feature", design_id, "--stage", config["research_stage"],
                         "--run-id", str(state.get("run_id", "")),
                         "--mode", state.get("research_mode", "live"),
                         "--output", f"artifacts/design-tasks/{design_id}-research.md"],
                        capture_output=True, text=True, timeout=10
                    )
                if proc.returncode == 0:
                    completed.append(design_id)
                else:
                    pending.append(design_id)
                    detail = (proc.stderr or proc.stdout).strip()
                    if detail:
                        print(f"  {design_id}: research record pending: {detail}", file=sys.stderr)
            except (OSError, subprocess.TimeoutExpired) as e:
                pending.append(design_id)
                print(f"  {design_id}: research record pending: {e}", file=sys.stderr)
        elif phase in ("GENERATE",):
            if check_design_exists(design_id):
                completed.append(design_id)
            else:
                pending.append(design_id)
        elif phase in ("REVIEW", "REASSESS_REVIEW"):
            if check_review_exists(design_id):
                completed.append(design_id)
            else:
                pending.append(design_id)
        elif phase in ("REVISE", "REASSESS_REVISE"):
            if get_review_auto_revised(design_id):
                completed.append(design_id)
            else:
                pending.append(design_id)
        else:
            completed.append(design_id)

    if pending:
        print(f"PENDING: {len(pending)}/{len(wave_ids)} "
              f"(completed: {len(completed)})", file=sys.stderr)
        sys.exit(3)
    else:
        print(f"COMPLETE: {len(completed)}/{len(wave_ids)}", file=sys.stderr)
        state.pop("wave_phase", None)
        state.pop("wave_ids", None)
        save_state(state)
        write_ids("tmp/pipeline-wave-ids.txt", [])
        advance(state)
        sys.exit(0)


def cmd_init(args):
    run_id = args.run_id or f"design-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    state = {
        "phase": "BATCH_START",
        "batch": 0,
        "total_batches": 1,
        "batch_size": args.batch_size,
        "headless": args.headless,
        "research_mode": args.research_mode,
        "replay_record": args.replay_record,
        "run_id": run_id,
        "reassess_cycle": 0,
        "start_time": datetime.now(timezone.utc).isoformat(),
    }

    Path("tmp").mkdir(exist_ok=True)
    write_ids("tmp/pipeline-wave-ids.txt", [])
    Path("artifacts/design-tasks").mkdir(parents=True, exist_ok=True)
    Path("artifacts/design-reviews").mkdir(parents=True, exist_ok=True)
    Path("artifacts/design-originals").mkdir(parents=True, exist_ok=True)

    save_state(state)
    print(f"Pipeline initialized: batch_size={args.batch_size}, headless={args.headless}, research_mode={args.research_mode}, run_id={run_id}",
          file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Design Creator Pipeline State Machine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_p = subparsers.add_parser("init")
    init_p.add_argument("--batch-size", type=int, default=5)
    init_p.add_argument("--headless", action="store_true")
    init_p.add_argument("--research-mode", choices=("off", "live", "replay"), default="live")
    init_p.add_argument("--replay-record", help="Frozen evidence JSON file, or a directory containing {JIRA_KEY}-research.json records; required for replay mode.")
    init_p.add_argument("--run-id", help="Optional stable run ID for reproducible evaluation.")

    subparsers.add_parser("next-action")
    subparsers.add_parser("wait-for-wave")
    subparsers.add_parser("run-phase")
    subparsers.add_parser("get-phase")

    set_p = subparsers.add_parser("set")
    set_p.add_argument("kvs", nargs="+", help="key=value pairs")

    set_phase_p = subparsers.add_parser("set-phase")
    set_phase_p.add_argument("phase", help="Target phase")

    args = parser.parse_args()

    if args.command == "init":
        if args.research_mode == "replay" and not args.replay_record:
            parser.error("--replay-record is required when --research-mode=replay")
        if args.research_mode != "replay" and args.replay_record:
            parser.error("--replay-record requires --research-mode=replay")
        cmd_init(args)
        return

    state = load_state()

    if args.command == "next-action":
        next_action(state)
    elif args.command == "wait-for-wave":
        wait_for_wave()
    elif args.command == "run-phase":
        run_phase(state)
    elif args.command == "get-phase":
        print(state.get("phase", "DONE"))
    elif args.command == "set":
        for kv in args.kvs:
            key, val = kv.split("=", 1)
            if val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
            elif val.isdigit():
                val = int(val)
            state[key] = val
        save_state(state)
    elif args.command == "set-phase":
        state["phase"] = args.phase
        save_state(state)


if __name__ == "__main__":
    main()
