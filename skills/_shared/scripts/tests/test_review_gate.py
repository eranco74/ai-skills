"""Focused tests for the deterministic and subprocess boundaries of review_gate."""

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest


# Import the shared script as a module without requiring a package install.
SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
import review_gate  # noqa: E402


class ReviewGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.requirement_text = "The product shall retain review evidence."
        self.source_text = (
            "OSAC-6285 source requirement: " + self.requirement_text + "\n"
        )
        self.capture_text = "The approved policy retains review evidence for 30 days.\n"
        self.document_text = (
            "# Review evidence\n\n"
            "## User-facing behavior\n"
            "The product retains review evidence.\n\n"
            "[Chai:C1](https://example.org/policy)\n"
        )
        self.record = {
            "schema_version": 1,
            "feature_key": "OSAC-6285",
            "stage": "prd",
            "run_id": "run-6285",
            "research_mode": "replay",
            "status": "available",
            "sources": [{
                "id": "S1", "url": "https://example.org/policy",
                "date": None, "revision": "r1", "verification": "verified",
            }],
            "requirements": [{
                "id": "R1", "statement": self.requirement_text,
                "scope": "in", "source_ids": ["S1"],
            }],
            "claims": [{
                "id": "C1", "statement": "Retention period is 30 days.",
                "source_ids": ["S1"], "decision_state": "accepted",
            }],
            "conflicts": [],
            "questions": [],
        }
        self.coverage = {
            "schema_version": 1,
            "feature_key": self.record["feature_key"],
            "stage": self.record["stage"],
            "run_id": self.record["run_id"],
            "requirements": [{
                "id": "R1", "status": "covered",
                "evidence": "The product retains review evidence.",
            }],
        }
        self.paths = self.write_inputs()
        self.review_command_path = self.write_command(
            "review-command.json", [sys.executable, str(self.write_reviewer())]
        )

    def tearDown(self):
        self.temp.cleanup()

    def write_json(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        return path

    def write_text(self, name, value):
        path = self.root / name
        path.write_text(value, encoding="utf-8")
        return path

    def write_inputs(self, *, prefix=""):
        def p(name):
            return prefix + name

        return {
            "record": self.write_json(p("record.json"), self.record),
            "brief": self.write_text(p("brief.md"), "Evidence for run-6285\n"),
            "document": self.write_text(p("document.md"), self.document_text),
            "coverage": self.write_json(p("coverage.json"), self.coverage),
            "source": self.write_text(p("source.md"), self.source_text),
            "capture": self.write_text(p("capture-S1.md"), self.capture_text),
        }

    def write_command(self, name, argv):
        return self.write_json(name, argv)

    def write_reviewer(self, *, mutate_path=None):
        """Create a tiny local reviewer which returns packet-bound evidence."""
        mutation = ""
        if mutate_path is not None:
            mutation = (
                "from pathlib import Path\n"
                f"Path({str(mutate_path)!r}).write_text("
                "Path(" + repr(str(mutate_path)) + ").read_text() + '\\nchanged after review\\n')\n"
            )
        script = '''import json, re, sys
packet = json.load(sys.stdin)
artifacts = packet["artifacts"]
requirements = [
    {"id": row["id"], "status": "covered", "rationale": "The draft preserves it.",
     "evidence": [{"artifact": "document", "quote": artifacts["document"]["text"].strip()}]}
    for row in packet["record"]["requirements"]
]
claim_ids = set(re.findall(r"\\[Chai:([^\\]]+)\\]", artifacts["document"]["text"]))
claims = []
for claim in packet["record"]["claims"]:
    if claim["id"] in claim_ids:
        sid = claim["source_ids"][0]
        claims.append({"id": claim["id"], "status": "supported", "rationale": "The primary capture supports it.",
                       "evidence": [{"artifact": "source:" + sid,
                                     "quote": artifacts["source:" + sid]["text"].strip()}]})
source_obligations = [{
    "statement": row["statement"], "requirement_ids": [row["id"]],
    "evidence": [{"artifact": "source", "quote": row["statement"]}],
} for row in packet["record"]["requirements"]]
review = {
    "schema_version": packet["schema_version"], "feature_key": packet["feature_key"],
    "stage": packet["stage"], "run_id": packet["run_id"],
    "input_sha256": packet["input_sha256"], "reviewer_id": packet["reviewer_id"],
    "source_obligations": source_obligations,
    "requirements": requirements, "claims": claims,
    "findings": [], "owner_questions": [],
    # These fields are deliberately untrusted; the gate derives its decision.
    "ready_for_owner_review": True, "owner_approval_required": False,
}
''' + mutation + "print(json.dumps(review))\n"
        return self.write_text("local-reviewer.py", script)

    def packet_files(self):
        return {
            "source": self.paths["source"],
            "record": self.paths["record"],
            "brief": self.paths["brief"],
            "document": self.paths["document"],
            "coverage": self.paths["coverage"],
            "source:S1": self.paths["capture"],
        }

    def valid_review(self, packet):
        doc = packet["artifacts"]["document"]["text"].strip()
        return {
            "schema_version": packet["schema_version"],
            "feature_key": packet["feature_key"],
            "stage": packet["stage"],
            "run_id": packet["run_id"],
            "input_sha256": packet["input_sha256"],
            "reviewer_id": packet["reviewer_id"],
            "source_obligations": [{
                "statement": self.requirement_text,
                "requirement_ids": ["R1"],
                "evidence": [{"artifact": "source", "quote": self.requirement_text}],
            }],
            "requirements": [{
                "id": "R1", "status": "covered", "rationale": "The draft preserves it.",
                "evidence": [{"artifact": "document", "quote": doc}],
            }],
            "claims": [{
                "id": "C1", "status": "supported", "rationale": "The primary capture supports it.",
                "evidence": [{"artifact": "source:S1",
                              "quote": packet["artifacts"]["source:S1"]["text"].strip()}],
            }],
            "findings": [], "owner_questions": [],
        }

    def gate_args(self, output_name="gate-output", **extra):
        args = [
            "--record", str(self.paths["record"]),
            "--brief", str(self.paths["brief"]),
            "--document", str(self.paths["document"]),
            "--coverage", str(self.paths["coverage"]),
            "--source", str(self.paths["source"]),
            "--source-capture", "S1=" + str(self.paths["capture"]),
            "--output", str(self.root / output_name),
            "--feature", self.record["feature_key"],
            "--stage", self.record["stage"],
            "--run-id", self.record["run_id"],
            "--mode", self.record["research_mode"],
            "--generator-id", "generator-run-1",
            "--reviewer-id", "reviewer-run-1",
            "--review-command", str(self.review_command_path),
            "--command-timeout", "10",
        ]
        for key, value in extra.items():
            if value is True:
                args.append("--" + key.replace("_", "-"))
            elif value is not False and value is not None:
                args.extend(["--" + key.replace("_", "-"), str(value)])
        return args

    def invoke_gate(self, args):
        with contextlib.redirect_stdout(io.StringIO()):
            return review_gate.main(args)

    def decision(self, output_name="gate-output"):
        return json.loads((self.root / output_name / "decision.json").read_text())

    def test_mechanical_artifact_gate_requires_clean_scope_coverage_and_citations(self):
        record = json.loads(self.paths["record"].read_text())
        valid = review_gate.check_artifacts(
            record, self.paths["brief"].read_text(), self.paths["document"].read_text(),
            json.loads(self.paths["coverage"].read_text()),
        )
        self.assertTrue(valid["ready_for_semantic_review"])
        self.assertTrue(valid["semantic_review_required"])

        stale_coverage = json.loads(self.paths["coverage"].read_text())
        stale_coverage["run_id"] = "old-run"
        result = review_gate.check_artifacts(
            record, self.paths["brief"].read_text(), self.paths["document"].read_text(), stale_coverage,
        )
        self.assertFalse(result["ready_for_semantic_review"])

        bad_document = self.document_text + "\n[Chai:NOT_IN_RECORD](https://example.org/policy)\n"
        result = review_gate.check_artifacts(
            record, self.paths["brief"].read_text(), bad_document,
            json.loads(self.paths["coverage"].read_text()),
        )
        self.assertFalse(result["valid"])

    def test_mechanical_failure_skips_reviewer_subprocess(self):
        coverage = json.loads(self.paths["coverage"].read_text())
        coverage["requirements"][0]["status"] = "unresolved"
        self.paths["coverage"].write_text(json.dumps(coverage), encoding="utf-8")
        marker = self.root / "reviewer-was-run"
        reviewer = self.write_text(
            "marker-reviewer.py",
            "from pathlib import Path\nimport sys\nPath(" + repr(str(marker)) + ").write_text('ran')\n",
        )
        self.review_command_path = self.write_command(
            "marker-command.json", [sys.executable, str(reviewer)]
        )

        self.assertEqual(1, self.invoke_gate(self.gate_args()))
        self.assertFalse(marker.exists())
        output = self.root / "gate-output"
        self.assertTrue((output / "mechanical.json").exists())
        self.assertFalse((output / "review-execution.json").exists())
        self.assertFalse(self.decision()["ready_for_owner_review"])

    def test_review_accounts_for_every_requirement_and_cited_claim_exactly_once(self):
        packet = review_gate.build_packet(self.record, self.packet_files(), "reviewer-run-1")
        review = self.valid_review(packet)
        self.assertEqual([], review_gate.validate_review(review, packet))

        mutations = []
        missing_requirement = json.loads(json.dumps(review))
        missing_requirement["requirements"] = []
        mutations.append(missing_requirement)
        duplicate_requirement = json.loads(json.dumps(review))
        duplicate_requirement["requirements"].append(duplicate_requirement["requirements"][0])
        mutations.append(duplicate_requirement)
        extra_claim = json.loads(json.dumps(review))
        extra_claim["claims"].append({
            "id": "NOT_CITED", "status": "supported", "rationale": "Extra",
            "evidence": [{"artifact": "source:S1", "quote": self.capture_text.strip()}],
        })
        mutations.append(extra_claim)

        for candidate in mutations:
            with self.subTest(candidate=candidate):
                self.assertTrue(review_gate.validate_review(candidate, packet))

    def test_evidence_must_be_an_exact_quote_from_a_packet_artifact(self):
        packet = review_gate.build_packet(self.record, self.packet_files(), "reviewer-run-1")
        fabricated_requirement = self.valid_review(packet)
        fabricated_requirement["requirements"][0]["evidence"][0]["quote"] = "A passage that is absent."
        fabricated_claim = self.valid_review(packet)
        fabricated_claim["claims"][0]["evidence"][0]["quote"] = "A fabricated source quote."
        for candidate in (fabricated_requirement, fabricated_claim):
            with self.subTest(candidate=candidate):
                self.assertTrue(review_gate.validate_review(candidate, packet))

    def test_supported_claim_cannot_borrow_an_unrelated_declared_source(self):
        self.record["sources"].append({
            "id": "S2", "url": "https://example.org/unrelated",
            "date": None, "revision": "r2", "verification": "verified",
        })
        self.paths = self.write_inputs(prefix="two-")
        unrelated_capture = self.write_text("capture-S2.md", "Unrelated source says nothing about retention.\n")
        files = self.packet_files()
        files["source:S2"] = unrelated_capture
        packet = review_gate.build_packet(self.record, files, "reviewer-run-1")
        review = self.valid_review(packet)
        review["claims"][0]["evidence"] = [{
            "artifact": "source:S2", "quote": unrelated_capture.read_text().strip(),
        }]
        self.assertTrue(review_gate.validate_review(review, packet))

    def test_covered_requirement_requires_draft_or_handoff_evidence(self):
        packet = review_gate.build_packet(self.record, self.packet_files(), "reviewer-run-1")
        review = self.valid_review(packet)
        review["requirements"][0]["evidence"] = [{
            "artifact": "source:S1", "quote": self.capture_text.strip(),
        }]
        self.assertTrue(review_gate.validate_review(review, packet))

    def test_stale_packet_hash_or_identity_is_rejected(self):
        packet = review_gate.build_packet(self.record, self.packet_files(), "reviewer-run-1")
        review = self.valid_review(packet)
        review["input_sha256"] = "stale-hash"
        self.assertTrue(review_gate.validate_review(review, packet))

        review = self.valid_review(packet)
        review["reviewer_id"] = "different-reviewer"
        self.assertTrue(review_gate.validate_review(review, packet))

    def test_source_captures_and_design_prd_are_required_packet_artifacts(self):
        files = self.packet_files()
        files.pop("source:S1")
        with self.assertRaises(ValueError):
            review_gate.build_packet(self.record, files, "reviewer-run-1")

        design_record = json.loads(json.dumps(self.record))
        design_record["stage"] = "design"
        files = self.packet_files()
        files.pop("source:S1")
        files["source:S1"] = self.paths["capture"]
        with self.assertRaises(ValueError):
            review_gate.build_packet(design_record, files, "reviewer-run-1")
        files["record"] = self.write_json("design-record.json", design_record)
        files["approved_prd"] = self.write_text("approved-prd.md", "Owner-approved PRD.\n")
        packet = review_gate.build_packet(design_record, files, "reviewer-run-1")
        self.assertIn("approved_prd", packet["artifacts"])

    def test_original_source_must_be_nonempty_and_record_snapshot_must_match(self):
        files = self.packet_files()
        empty_source = self.write_text("blank-source.md", "  \n")
        files["source"] = empty_source
        with self.assertRaises(ValueError):
            review_gate.build_packet(self.record, files, "reviewer-run-1")

        files = self.packet_files()
        files["record"].write_text(json.dumps({**self.record, "run_id": "drifted"}), encoding="utf-8")
        with self.assertRaises(ValueError):
            review_gate.build_packet(self.record, files, "reviewer-run-1")

    def test_original_fetch_header_cannot_identify_a_different_feature(self):
        files = self.packet_files()
        files["source"] = self.write_text(
            "wrong-feature-source.md",
            "# OSAC-999\n\nThis source belongs to another feature.\n",
        )
        with self.assertRaisesRegex(ValueError, "different feature"):
            review_gate.build_packet(self.record, files, "reviewer-run-1")

    def test_design_covered_requirement_needs_document_evidence_not_brief_alone(self):
        design_record = json.loads(json.dumps(self.record))
        design_record["stage"] = "design"
        files = self.packet_files()
        files["record"] = self.write_json("design-record.json", design_record)
        files["approved_prd"] = self.write_text("approved-prd.md", "Approved scope.\n")
        packet = review_gate.build_packet(design_record, files, "reviewer-run-1")
        review = self.valid_review(packet)
        review["requirements"][0]["evidence"] = [{
            "artifact": "brief", "quote": packet["artifacts"]["brief"]["text"].strip(),
        }]
        self.assertTrue(review_gate.validate_review(review, packet))

        review["requirements"][0]["evidence"] = [{
            "artifact": "document", "quote": packet["artifacts"]["document"]["text"].strip(),
        }]
        self.assertEqual([], review_gate.validate_review(review, packet))

    def test_omitted_requirement_needs_original_scope_quote(self):
        packet = review_gate.build_packet(self.record, self.packet_files(), "reviewer-run-1")
        review = self.valid_review(packet)
        review["requirements"][0]["status"] = "omitted"
        review["requirements"][0]["evidence"] = [{
            "artifact": "document", "quote": packet["artifacts"]["document"]["text"].strip(),
        }]
        self.assertTrue(review_gate.validate_review(review, packet))

        review["requirements"][0]["evidence"] = [{
            "artifact": "source", "quote": self.requirement_text,
        }]
        self.assertEqual([], review_gate.validate_review(review, packet))

    def test_timeout_saves_partial_output_and_metadata_then_fails(self):
        slow_reviewer = self.write_text(
            "slow-reviewer.py",
            "import sys, time\nsys.stdout.write('partial reviewer output')\nsys.stdout.flush()\ntime.sleep(3)\n",
        )
        self.review_command_path = self.write_command(
            "slow-review-command.json", [sys.executable, str(slow_reviewer)]
        )
        self.assertEqual(1, self.invoke_gate(self.gate_args("timed-out", command_timeout=1)))

        output = self.root / "timed-out"
        self.assertEqual("partial reviewer output", (output / "review-stdout.txt").read_text())
        execution = json.loads((output / "review-execution.json").read_text())
        self.assertEqual("timeout", execution["exit_code"])
        self.assertTrue(execution["argv_sha256"])
        self.assertGreaterEqual(execution["duration_seconds"], 0)
        result = self.decision("timed-out")
        self.assertFalse(result["ready_for_owner_review"])
        self.assertEqual("command timed out", result["error"])

    def test_generation_cannot_rewrite_authoritative_source(self):
        source_rewriter = self.write_text(
            "source-rewriter.py",
            "from pathlib import Path\nimport sys\n"
            "path = Path(sys.argv[1])\npath.write_text(path.read_text() + '\\nchanged by generator\\n')\n"
            "print('rewrote source')\n",
        )
        generation_command = self.write_command(
            "source-rewriter-command.json", [sys.executable, str(source_rewriter), str(self.paths["source"])],
        )
        # Generation gets fresh artifact paths; these do not exist before invocation.
        generated = {
            "record": self.root / "generated-record.json",
            "brief": self.root / "generated-brief.md",
            "document": self.root / "generated-document.md",
            "coverage": self.root / "generated-coverage.json",
        }
        self.assertTrue(all(not path.exists() for path in generated.values()))
        args = self.gate_args(
            "source-rewrite", generation_command=generation_command,
            **generated,
        )
        self.assertEqual(1, self.invoke_gate(args))

        result = self.decision("source-rewrite")
        self.assertFalse(result["ready_for_owner_review"])
        self.assertIn("authoritative scope input changed during generation", result["error"])
        self.assertEqual("rewrote source", (self.root / "source-rewrite" / "generation-stdout.txt").read_text().strip())
        self.assertTrue(all(not path.exists() for path in generated.values()))

    def test_source_obligation_inventory_must_quote_source_and_map_requirements(self):
        packet = review_gate.build_packet(self.record, self.packet_files(), "reviewer-run-1")
        no_inventory = self.valid_review(packet)
        no_inventory["source_obligations"] = []
        unmapped = self.valid_review(packet)
        unmapped["source_obligations"][0]["requirement_ids"] = []
        fabricated = self.valid_review(packet)
        fabricated["source_obligations"][0]["evidence"][0]["quote"] = "Not in original source."

        for candidate in (no_inventory, unmapped, fabricated):
            with self.subTest(candidate=candidate):
                result = review_gate.review_result(candidate, packet)
                self.assertFalse(result["valid"] and result["ready_for_owner_review"])

    def test_malformed_finding_severity_fails_closed_without_type_error(self):
        packet = review_gate.build_packet(self.record, self.packet_files(), "reviewer-run-1")
        review = self.valid_review(packet)
        review["findings"] = [{
            "severity": ["minor"], "description": "Malformed severity",
            "evidence": [{"artifact": "document", "quote": self.document_text.strip()}],
        }]
        errors = review_gate.validate_review(review, packet)
        self.assertTrue(errors)
        result = review_gate.review_result(review, packet)
        self.assertFalse(result["ready_for_owner_review"])
        self.assertTrue(result["owner_approval_required"])

    def test_generator_and_reviewer_must_have_distinct_identities(self):
        args = self.gate_args()
        generator_at = args.index("--generator-id") + 1
        reviewer_at = args.index("--reviewer-id") + 1
        args[reviewer_at] = args[generator_at]
        self.assertEqual(1, self.invoke_gate(args))
        result = self.decision()
        self.assertFalse(result["ready_for_owner_review"])
        self.assertTrue(result["owner_approval_required"])

    def test_generation_and_review_subprocess_failures_are_saved_and_fail_closed(self):
        generation_command = self.write_command(
            "generation-failure.json",
            [sys.executable, "-c", "import sys; print('generation out'); print('generation err', file=sys.stderr); sys.exit(7)"],
        )
        # A generation command owns these paths, so use fresh output locations.
        args = self.gate_args(
            "generation-failed",
            record=self.root / "generated-record.json",
            brief=self.root / "generated-brief.md",
            document=self.root / "generated-document.md",
            coverage=self.root / "generated-coverage.json",
            generation_command=generation_command,
        )
        self.assertEqual(1, self.invoke_gate(args))
        generation_output = self.root / "generation-failed"
        self.assertEqual("generation out", (generation_output / "generation-stdout.txt").read_text().strip())
        self.assertEqual("generation err", (generation_output / "generation-stderr.txt").read_text().strip())
        self.assertFalse(self.decision("generation-failed")["ready_for_owner_review"])

        review_command = self.write_command(
            "review-failure.json",
            [sys.executable, "-c", "import sys; print('review out'); print('review err', file=sys.stderr); sys.exit(9)"],
        )
        self.review_command_path = review_command
        self.assertEqual(1, self.invoke_gate(self.gate_args("review-failed")))
        review_output = self.root / "review-failed"
        self.assertEqual("review out", (review_output / "review-stdout.txt").read_text().strip())
        self.assertEqual("review err", (review_output / "review-stderr.txt").read_text().strip())
        self.assertFalse(self.decision("review-failed")["ready_for_owner_review"])

    def test_malformed_reviewer_json_and_mid_review_input_mutation_fail_closed(self):
        malformed = self.write_command(
            "malformed-review.json", [sys.executable, "-c", "print('{malformed')"],
        )
        self.review_command_path = malformed
        self.assertEqual(1, self.invoke_gate(self.gate_args("malformed-json")))
        result = self.decision("malformed-json")
        self.assertFalse(result["valid"])
        self.assertFalse(result["ready_for_owner_review"])
        self.assertTrue(result["owner_approval_required"])

        mutating_reviewer = self.write_reviewer(mutate_path=self.paths["document"])
        self.review_command_path = self.write_command(
            "mutating-review.json", [sys.executable, str(mutating_reviewer)]
        )
        self.assertEqual(1, self.invoke_gate(self.gate_args("mutated-input")))
        result = self.decision("mutated-input")
        self.assertFalse(result["valid"])
        self.assertFalse(result["ready_for_owner_review"])
        self.assertIn("input changed during semantic review", " ".join(result["errors"]))

    def test_readiness_is_not_owner_approval_or_reviewer_claimed_approval(self):
        packet = review_gate.build_packet(self.record, self.packet_files(), "reviewer-run-1")
        review = self.valid_review(packet)
        review["ready_for_owner_review"] = True
        review["owner_approval_required"] = False
        result = review_gate.review_result(review, packet)
        self.assertTrue(result["valid"])
        self.assertTrue(result["ready_for_owner_review"])
        self.assertTrue(result["owner_approval_required"])
        self.assertNotIn("owner_approved", result)

        review["requirements"][0]["status"] = "unresolved"
        result = review_gate.review_result(review, packet)
        self.assertFalse(result["ready_for_owner_review"])
        self.assertTrue(result["owner_approval_required"])


if __name__ == "__main__":
    unittest.main()
