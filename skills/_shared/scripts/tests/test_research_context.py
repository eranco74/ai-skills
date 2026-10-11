"""Deterministic evidence safety and parity checks; no network or model calls."""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("research_context", SCRIPTS / "research_context.py")
research = importlib.util.module_from_spec(spec)
spec.loader.exec_module(research)


def fixture():
    return {
        "schema_version": 1, "feature_key": "OSAC-1", "stage": "prd",
        "run_id": "current", "research_mode": "replay", "status": "available",
        "sources": [{"id": "J", "url": "https://example.org/issue/1",
                     "date": "2026-10-01", "revision": "v1", "verification": "verified"}],
        "requirements": [{"id": "R1", "statement": "Preserve tenant ownership.",
                          "scope": "in", "source_ids": ["J"]}],
        "claims": [], "conflicts": [], "questions": []}


class EvidenceChecks(unittest.TestCase):
    def test_valid_identity(self):
        self.assertEqual([], research.validate_record(fixture(), feature="OSAC-1", stage="prd", run_id="current"))

    def test_previous_run_cannot_complete_current_run(self):
        self.assertTrue(research.validate_record(fixture(), run_id="different"))

    def test_feature_and_stage_bound(self):
        self.assertTrue(research.validate_record(fixture(), feature="OSAC-2", stage="design"))

    def test_mode_bound(self):
        self.assertTrue(research.validate_record(fixture(), mode="off"))

    def test_unknown_reference_rejected(self):
        record = fixture(); record["requirements"][0]["source_ids"] = ["missing"]
        self.assertTrue(research.validate_record(record))

    def test_duplicate_source_rejected(self):
        record = fixture(); record["sources"].append(copy.deepcopy(record["sources"][0]))
        self.assertTrue(research.validate_record(record))

    def test_invalid_enums_report_errors_without_crashing(self):
        for field in ("stage", "research_mode", "status"):
            record = fixture(); record[field] = []
            self.assertTrue(research.validate_record(record))

    def test_boolean_is_not_schema_version(self):
        record = fixture(); record["schema_version"] = True
        self.assertTrue(research.validate_record(record))

    def test_real_date_required(self):
        record = fixture(); record["sources"][0]["date"] = "2026-99-99"
        self.assertTrue(research.validate_record(record))

    def test_credentials_in_url_rejected(self):
        record = fixture(); record["sources"][0]["url"] = "https://user:secret@example.org/"
        self.assertTrue(research.validate_record(record))

    def test_unverified_claim_never_enters_rendered_facts(self):
        record = fixture(); record["sources"][0]["verification"] = "unverified"
        self.assertNotIn("Preserve tenant ownership", research.render_record(record))
        self.assertIn("Unverified items excluded", research.render_record(record))

    def test_unresolved_material_conflict_blocks_readiness(self):
        record = fixture(); record["conflicts"] = [{"id": "C", "description": "Conflicting owners.",
            "source_ids": ["J"], "material": True, "resolved": False}]
        self.assertEqual(["C"], research.readiness(record)["blocked_by_material_conflicts"])
        self.assertIn("material, unresolved", research.render_record(record))

    def test_render_does_not_truncate_conflicts(self):
        with self.assertRaises(ValueError): research.render_record(fixture(), max_chars=1)

    def test_off_and_failed_retrieval_preserve_requirements(self):
        for mode, status in (("off", "skipped"), ("live", "timeout"), ("live", "unavailable")):
            record = fixture(); record.update(research_mode=mode, status=status)
            self.assertEqual([], research.validate_record(record))
            self.assertIn("Preserve tenant ownership", research.render_record(record))

    def test_unknown_scope_date_does_not_discard_scope_or_verify_org_claims(self):
        for mode, status in (("off", "skipped"), ("live", "timeout"),
                             ("live", "unavailable"), ("live", "available")):
            with self.subTest(mode=mode, status=status):
                record = fixture()
                record.update(research_mode=mode, status=status)
                record["sources"][0].update(date=None, revision=None)
                record["sources"].append({"id": "ORG", "url": "https://example.org/context",
                    "date": None, "revision": None, "verification": "unverified"})
                record["claims"] = [{"id": "C1", "statement": "Email delivery already exists.",
                    "source_ids": ["ORG"], "decision_state": "implemented"}]
                self.assertEqual([], research.validate_record(record))
                brief = research.render_record(record)
                self.assertIn("Preserve tenant ownership", brief)
                self.assertNotIn("Email delivery already exists", brief)
                self.assertIn("Unverified items excluded from factual input: C1", brief)

    def test_render_never_auto_verifies_a_source_from_its_feature_url(self):
        record = fixture()
        record["sources"][0].update(url="https://redhat.atlassian.net/browse/OSAC-1",
                                     verification="unverified")
        self.assertNotIn("Preserve tenant ownership", research.render_record(record))
        self.assertEqual("unverified", record["sources"][0]["verification"])

    def test_oversized_record_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "record.json"
            record = fixture(); record["questions"] = ["x" * 65536]
            path.write_text(json.dumps(record))
            with self.assertRaises(ValueError): research.load_record(path)

    def test_all_environment_contracts_identical(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "sync_research_context.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
