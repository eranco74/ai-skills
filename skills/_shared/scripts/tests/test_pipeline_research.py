"""Standalone PRD/design research phase checks; no network or generation calls."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import yaml


REPO = Path(__file__).resolve().parents[4]
PIPELINES = {
    "prd": {"directory": "prd-creator", "artifact_dir": "prd-tasks"},
    "design": {"directory": "design-creator", "artifact_dir": "design-tasks"},
}
KEY = "OSAC-1"


def record(stage, *, run_id="fixture-run", mode="live", status="available", key=KEY):
    return {
        "schema_version": 1,
        "feature_key": key,
        "stage": stage,
        "run_id": run_id,
        "research_mode": mode,
        "status": status,
        "sources": [{"id": "J", "url": "https://example.org/issue/1",
                     "date": "2026-10-01", "revision": "v1", "verification": "verified"}],
        "requirements": [],
        "claims": [],
        "conflicts": [],
        "questions": [],
    }


class PipelineHarness:
    """Copy the minimum creator tree needed for isolated CLI state checks."""

    def __init__(self, root, stage):
        self.stage = stage
        self.config = PIPELINES[stage]
        self.work = Path(root) / self.config["directory"]
        self.work.mkdir()
        (self.work / "scripts").mkdir()
        shutil.copy(REPO / "skills" / self.config["directory"] / "scripts" / "pipeline_state.py",
                    self.work / "scripts" / "pipeline_state.py")
        shared = Path(root) / "_shared" / "scripts"
        shared.mkdir(parents=True)
        shutil.copy(REPO / "skills" / "_shared" / "scripts" / "research_context.py",
                    shared / "research_context.py")
        self.artifacts = self.work / "artifacts" / self.config["artifact_dir"]
        self.artifacts.mkdir(parents=True)
        self.tmp = self.work / "tmp"
        self.tmp.mkdir()
        self.fixture_dir = self.work / "fixtures"
        self.fixture_dir.mkdir()
        (self.artifacts / f"{KEY}-source.md").write_text("Feature source fixture\n")
        if stage == "design":
            (self.artifacts / f"{KEY}-prd.md").write_text("PRD fixture\n")
        self.command = [sys.executable, "scripts/pipeline_state.py"]

    def run(self, *args, expected=0):
        proc = subprocess.run(self.command + list(args), cwd=self.work,
                              capture_output=True, text=True)
        if proc.returncode != expected:
            raise AssertionError(
                f"{self.stage} command {args!r}: expected exit {expected}, got "
                f"{proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
            )
        return proc

    def initialize_and_dispatch_research(self, mode="replay", replay_path="fixtures"):
        args = ["init", "--research-mode", mode, "--run-id", "current-run"]
        if replay_path is not None:
            args += ["--replay-record", replay_path]
        self.run(*args)
        (self.tmp / "pipeline-batch-1-ids.txt").write_text(KEY + "\n")
        self.run("next-action")  # BATCH_START -> FETCH
        self.run("run-phase")    # FETCH -> FETCH_PRD (design) or RESEARCH (PRD)
        if self.stage == "design":
            self.run("run-phase")  # FETCH_PRD -> RESEARCH
        action = yaml.safe_load(self.run("next-action").stdout)
        self.assert_research_dispatch(action, mode)
        return action

    def assert_research_dispatch(self, action, mode):
        if action["action"] != "launch_wave" or action["phase"] != "RESEARCH":
            raise AssertionError(f"expected RESEARCH dispatch, got {action}")
        state = yaml.safe_load((self.tmp / "pipeline-state.yaml").read_text())
        if state["phase"] != "RESEARCH" or state["wave_phase"] != "RESEARCH":
            raise AssertionError(f"research dispatch state not persisted: {state}")
        agent_vars = action["agents"][0]["vars"]
        expected_vars = [
            f"RESEARCH_MODE={mode}", "RESEARCH_RUN_ID=current-run",
            f"RESEARCH_STAGE={self.stage}",
            f"RESEARCH_RECORD=artifacts/{self.config['artifact_dir']}/{KEY}-research.json",
        ]
        for value in expected_vars:
            if value not in agent_vars:
                raise AssertionError(f"missing dispatch variable {value!r}: {agent_vars}")
        if mode == "replay" and f"RESEARCH_REPLAY_RECORD=fixtures/{KEY}-research.json" not in agent_vars:
            raise AssertionError(f"missing replay fixture variable: {agent_vars}")

    def write_fixture(self, status="available"):
        path = self.fixture_dir / f"{KEY}-research.json"
        path.write_text(json.dumps(record(self.stage, status=status)))
        return path

    def write_output(self, *, run_id="current-run", mode="replay", status="available",
                     key=KEY, stage=None):
        output = record(stage or self.stage, run_id=run_id, mode=mode, status=status, key=key)
        path = self.artifacts / f"{KEY}-research.json"
        path.write_text(json.dumps(output))
        return path

    def wait_pending(self):
        self.run("wait-for-wave", expected=3)
        state = yaml.safe_load((self.tmp / "pipeline-state.yaml").read_text())
        if state["phase"] != "RESEARCH" or state["wave_phase"] != "RESEARCH":
            raise AssertionError(f"invalid research result advanced the phase: {state}")


class PipelineResearchTests(unittest.TestCase):
    def test_replay_barrier_identity_and_completion_for_both_stages(self):
        for stage in PIPELINES:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                h = PipelineHarness(tmp, stage)
                h.write_fixture()
                h.initialize_and_dispatch_research()

                # A completion record is required and must be bound to this run,
                # feature, stage, and configured mode.
                h.wait_pending()  # missing output
                h.write_output(run_id="stale-run")
                h.wait_pending()
                h.write_output(key="OSAC-2")
                h.wait_pending()
                wrong_stage = "design" if stage == "prd" else "prd"
                h.write_output(stage=wrong_stage)
                h.wait_pending()
                h.write_output(mode="live")
                h.wait_pending()

                h.write_output(status="unavailable")
                h.run("wait-for-wave")
                state = yaml.safe_load((h.tmp / "pipeline-state.yaml").read_text())
                self.assertEqual("GENERATE", state["phase"])
                self.assertNotIn("wave_phase", state)
                brief = h.artifacts / f"{KEY}-research.md"
                self.assertTrue(brief.is_file())
                self.assertIn("Run: current-run; mode: replay; research: unavailable", brief.read_text())

    def test_missing_replay_fixture_does_not_advance(self):
        for stage in PIPELINES:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                h = PipelineHarness(tmp, stage)
                h.initialize_and_dispatch_research()
                h.write_output()
                h.wait_pending()

    def test_replay_input_cannot_be_output_record(self):
        for stage, config in PIPELINES.items():
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                h = PipelineHarness(tmp, stage)
                collision = f"artifacts/{config['artifact_dir']}/{KEY}-research.json"
                h.run("init", "--research-mode", "replay", "--run-id", "current-run",
                      "--replay-record", collision)
                (h.tmp / "pipeline-batch-1-ids.txt").write_text(KEY + "\n")
                h.run("next-action")
                h.run("run-phase")
                if stage == "design":
                    h.run("run-phase")
                proc = h.run("next-action", expected=1)
                self.assertIn("must be separate", proc.stderr)

    def test_off_mode_skipped_record_completes_both_stages(self):
        for stage in PIPELINES:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                h = PipelineHarness(tmp, stage)
                h.initialize_and_dispatch_research(mode="off", replay_path=None)
                h.write_output(mode="off", status="skipped")
                h.run("wait-for-wave")
                state = yaml.safe_load((h.tmp / "pipeline-state.yaml").read_text())
                self.assertEqual("GENERATE", state["phase"])
                self.assertIn("research: skipped", (h.artifacts / f"{KEY}-research.md").read_text())

    def test_over_budget_brief_does_not_complete_research(self):
        for stage in PIPELINES:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                h = PipelineHarness(tmp, stage)
                h.initialize_and_dispatch_research(mode="off", replay_path=None)
                path = h.write_output(mode="off", status="skipped")
                output = json.loads(path.read_text())
                output["questions"] = ["Unresolved question: " + "x" * 17000]
                path.write_text(json.dumps(output))
                h.wait_pending()

    def test_review_pass_is_blocked_by_material_conflict_without_revision_loop(self):
        for stage, config in PIPELINES.items():
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                cwd = Path.cwd()
                os.chdir(tmp)
                try:
                    module_path = REPO / "skills" / config["directory"] / "scripts" / "pipeline_state.py"
                    spec = importlib.util.spec_from_file_location(f"pipeline_{stage}_research_test", module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    artifact_dir = Path("artifacts") / config["artifact_dir"]
                    review_dir = Path("artifacts") / f"{stage}-reviews"
                    artifact_dir.mkdir(parents=True)
                    review_dir.mkdir(parents=True)
                    (review_dir / f"{KEY}-review.md").write_text(
                        "---\nscore: 10\npass: true\nrecommendation: pass\nauto_revised: true\n---\n"
                    )
                    evidence = record(stage, key=KEY)
                    evidence["conflicts"] = [{
                        "id": "C1", "description": "Material scope decision is unresolved.",
                        "source_ids": ["J"], "material": True, "resolved": False,
                    }]
                    evidence_path = artifact_dir / f"{KEY}-research.json"
                    evidence_path.write_text(json.dumps(evidence))
                    (review_dir / f"{KEY}-coverage.json").write_text(json.dumps({
                        "schema_version": 1, "feature_key": KEY, "stage": stage,
                        "run_id": "fixture-run", "requirements": [],
                    }))
                    self.assertEqual((10, False, "clarify"), module.get_review_score(KEY))
                    self.assertEqual([], module.filter_for_revision([KEY]))
                    self.assertEqual([], module.filter_for_reassess([KEY]))

                    evidence["conflicts"][0]["resolved"] = True
                    evidence_path.write_text(json.dumps(evidence))
                    self.assertEqual((10, True, "pass"), module.get_review_score(KEY))
                finally:
                    os.chdir(cwd)

    def test_requirement_coverage_gate_for_both_stages(self):
        for stage, config in PIPELINES.items():
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                cwd = Path.cwd()
                os.chdir(tmp)
                try:
                    module_path = REPO / "skills" / config["directory"] / "scripts" / "pipeline_state.py"
                    spec = importlib.util.spec_from_file_location(f"pipeline_{stage}_coverage_test", module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    artifact_dir = Path("artifacts") / config["artifact_dir"]
                    review_dir = Path("artifacts") / f"{stage}-reviews"
                    artifact_dir.mkdir(parents=True)
                    review_dir.mkdir(parents=True)
                    (review_dir / f"{KEY}-review.md").write_text(
                        "---\nscore: 10\npass: true\nrecommendation: pass\nauto_revised: true\n---\n"
                    )
                    evidence = record(stage, run_id="run-1", key=KEY)
                    evidence["requirements"] = [
                        {"id": "R-IN", "statement": "An included requirement.", "scope": "in", "source_ids": ["J"]},
                        {"id": "R-CONSTRAINT", "statement": "A constraint.", "scope": "constraint", "source_ids": ["J"]},
                        {"id": "R-OUT", "statement": "An excluded boundary.", "scope": "out", "source_ids": ["J"]},
                    ]
                    evidence_path = artifact_dir / f"{KEY}-research.json"
                    evidence_path.write_text(json.dumps(evidence))
                    coverage_path = review_dir / f"{KEY}-coverage.json"

                    def coverage(rows=None, **identity):
                        data = {
                            "schema_version": 1, "feature_key": KEY, "stage": stage,
                            "run_id": "run-1",
                            "requirements": rows if rows is not None else [
                                {"id": rid, "status": "covered", "evidence": "Addressed in section 2."}
                                for rid in ("R-IN", "R-CONSTRAINT", "R-OUT")
                            ],
                        }
                        data.update(identity)
                        coverage_path.write_text(json.dumps(data))

                    coverage()
                    self.assertEqual((10, True, "pass"), module.get_review_score(KEY))
                    coverage([
                        {"id": "R-IN", "status": "covered", "evidence": "Section 2."},
                        {"id": "R-CONSTRAINT", "status": "covered", "evidence": "Section 2."},
                        {"id": "R-OUT", "status": "omitted", "evidence": "No out-of-scope boundary was needed."},
                    ])
                    self.assertEqual((10, True, "pass"), module.get_review_score(KEY))

                    # Material requirements left unresolved or omitted block
                    # readiness without entering the automatic revision loop.
                    coverage([
                        {"id": "R-IN", "status": "unresolved", "evidence": "Needs owner input."},
                        {"id": "R-CONSTRAINT", "status": "covered", "evidence": "Section 2."},
                        {"id": "R-OUT", "status": "covered", "evidence": "Out of scope section."},
                    ])
                    self.assertEqual((10, False, "clarify"), module.get_review_score(KEY))
                    self.assertEqual([], module.filter_for_revision([KEY]))
                    self.assertEqual([], module.filter_for_reassess([KEY]))
                    coverage([
                        {"id": "R-IN", "status": "covered", "evidence": "Section 2."},
                        {"id": "R-CONSTRAINT", "status": "omitted", "evidence": "Not addressed."},
                        {"id": "R-OUT", "status": "covered", "evidence": "Out of scope section."},
                    ])
                    self.assertEqual((10, False, "clarify"), module.get_review_score(KEY))

                    # Coverage must be bound to this feature, stage, and run,
                    # and must account for the exact requirement IDs.
                    for identity in (
                        {"feature_key": "OSAC-2"},
                        {"stage": "design" if stage == "prd" else "prd"},
                        {"run_id": "stale-run"},
                        {"schema_version": 2},
                    ):
                        with self.subTest(identity=identity):
                            coverage(**identity)
                            self.assertEqual((10, False, "clarify"), module.get_review_score(KEY))
                    coverage([
                        {"id": "UNKNOWN", "status": "covered", "evidence": "Section 2."},
                    ])
                    self.assertEqual((10, False, "clarify"), module.get_review_score(KEY))
                    coverage_path.unlink()
                    self.assertEqual((10, False, "clarify"), module.get_review_score(KEY))
                finally:
                    os.chdir(cwd)

    def test_legacy_review_without_research_record_remains_supported(self):
        for stage, config in PIPELINES.items():
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                cwd = Path.cwd()
                os.chdir(tmp)
                try:
                    module_path = REPO / "skills" / config["directory"] / "scripts" / "pipeline_state.py"
                    spec = importlib.util.spec_from_file_location(f"pipeline_{stage}_legacy_review_test", module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    review_dir = Path("artifacts") / f"{stage}-reviews"
                    review_dir.mkdir(parents=True)
                    (review_dir / f"{KEY}-review.md").write_text(
                        "---\nscore: 8\npass: true\nrecommendation: pass\n---\n"
                    )
                    self.assertEqual((8, True, "pass"), module.get_review_score(KEY))
                finally:
                    os.chdir(cwd)

    def test_design_generation_assessment_and_fixup_share_canonical_filename(self):
        config = PIPELINES["design"]
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path.cwd()
            os.chdir(tmp)
            try:
                module_path = REPO / "skills" / config["directory"] / "scripts" / "pipeline_state.py"
                spec = importlib.util.spec_from_file_location("design_pipeline_path_test", module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                task_dir = Path("artifacts/design-tasks")
                original_dir = Path("artifacts/design-originals")
                review_dir = Path("artifacts/design-reviews")
                task_dir.mkdir(parents=True)
                original_dir.mkdir(parents=True)
                review_dir.mkdir(parents=True)
                generated = task_dir / f"{KEY}-design.md"
                generated.write_text(
                    "---\ntitle: Fixture design\nauthors: [test@example.org]\n"
                    "creation-date: 2026-10-11\nlast-updated: 2026-10-11\n---\n"
                    "# Fixture design\n\n## Summary\nSynthetic valid artifact for path checks.\n"
                )
                original = original_dir / f"{KEY}-design.md"
                original.write_text("# Earlier design\n")
                review = review_dir / f"{KEY}-review.md"
                review.write_text("---\nauto_revised: false\n---\n")

                self.assertTrue(module.check_design_exists(KEY))
                self.assertFalse((task_dir / f"{KEY}.md").exists())

                score_result = SimpleNamespace(
                    returncode=0, stdout='{"pass": true, "issues": []}', stderr=""
                )
                with patch.object(module.subprocess, "run", return_value=score_result) as run:
                    module.assess_all([KEY])
                self.assertEqual(6, run.call_count)
                for call in run.call_args_list:
                    self.assertEqual(str(generated), call.args[0][-1])

                with patch.object(module.subprocess, "run") as run:
                    module.fixup([KEY])
                self.assertEqual(1, run.call_count)
                self.assertIn(f"artifacts/design-reviews/{KEY}-review.md", run.call_args.args[0])
                self.assertIn("auto_revised=true", run.call_args.args[0])
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
