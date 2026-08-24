from pathlib import Path
import json
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

try:
    from freeze_source import build_snapshot
    from validate_source_receipt import validate_receipt
    from package_release import package_release
except ImportError:
    build_snapshot = None
    validate_receipt = None
    package_release = None

try:
    from install_local import install_local
except ImportError:
    install_local = None


class DeliveryTests(unittest.TestCase):
    def test_snapshot_is_stable_and_excludes_generated_outputs(self):
        self.assertIsNotNone(build_snapshot, "build_snapshot is not implemented")
        first = build_snapshot(ROOT)
        second = build_snapshot(ROOT)
        self.assertEqual(first, second)
        self.assertRegex(first["source_snapshot_id"], r"^sha256:[0-9a-f]{64}$")
        paths = [record["path"] for record in first["files"]]
        self.assertFalse(any("__pycache__" in path for path in paths))
        self.assertFalse(any(path.endswith(".DS_Store") for path in paths))

    def test_non_pass_or_mismatched_receipt_is_rejected(self):
        self.assertIsNotNone(build_snapshot, "build_snapshot is not implemented")
        self.assertIsNotNone(validate_receipt, "validate_receipt is not implemented")
        snapshot = build_snapshot(ROOT)
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            snapshot_path = base / "snapshot.json"
            receipt_path = base / "receipt.json"
            snapshot_path.write_text(
                json.dumps(snapshot, ensure_ascii=False), encoding="utf-8"
            )
            receipt = self._valid_pass_receipt("wrong")
            receipt["verdict"] = "revision_required"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            errors = validate_receipt(receipt_path, snapshot_path)
        self.assertIn("receipt verdict must be pass", errors)
        self.assertIn("receipt snapshot id does not match", errors)

    def test_valid_pass_receipt_requires_complete_semantic_audits(self):
        self.assertIsNotNone(build_snapshot, "build_snapshot is not implemented")
        self.assertIsNotNone(validate_receipt, "validate_receipt is not implemented")
        snapshot = build_snapshot(ROOT)
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            snapshot_path = base / "snapshot.json"
            receipt_path = base / "receipt.json"
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
            receipt = self._valid_pass_receipt(snapshot["source_snapshot_id"])
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            self.assertEqual(validate_receipt(receipt_path, snapshot_path), [])

            receipt["source_audit"]["normal_case_replay"] = "fail"
            receipt["materiality_audit"]["material_blocker_found"] = True
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            errors = validate_receipt(receipt_path, snapshot_path)
        self.assertIn("source audit normal case replay must pass", errors)
        self.assertIn("pass receipt must not contain a material blocker", errors)

    def test_semantically_empty_pass_receipts_are_rejected(self):
        self.assertIsNotNone(build_snapshot, "build_snapshot is not implemented")
        self.assertIsNotNone(validate_receipt, "validate_receipt is not implemented")
        snapshot = build_snapshot(ROOT)
        mutations = (
            ("missing grounding audit", lambda receipt: receipt.pop("grounding_audit"), "receipt missing fields"),
            ("empty evidence", lambda receipt: receipt.update(evidence=[]), "receipt evidence must be a non-empty list"),
            ("empty preserve", lambda receipt: receipt.update(preserve=[]), "receipt preserve must be a non-empty list"),
            ("empty stable rules", lambda receipt: receipt["authority_audit"].update(stable_rules_reviewed=[]), "pass receipt must review at least one stable rule"),
            ("incomplete stable rule", lambda receipt: receipt["authority_audit"].update(stable_rules_reviewed=[{"rule": "x"}]), "stable rule audit 0 missing fields"),
        )
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            snapshot_path = base / "snapshot.json"
            receipt_path = base / "receipt.json"
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
            for label, mutate, expected_error in mutations:
                with self.subTest(label=label):
                    receipt = self._valid_pass_receipt(snapshot["source_snapshot_id"])
                    mutate(receipt)
                    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                    errors = validate_receipt(receipt_path, snapshot_path)
                    self.assertTrue(
                        any(expected_error in error for error in errors),
                        f"{expected_error!r} not found in {errors!r}",
                    )

    def test_partial_authority_coverage_is_rejected(self):
        self.assertIsNotNone(build_snapshot, "build_snapshot is not implemented")
        self.assertIsNotNone(validate_receipt, "validate_receipt is not implemented")
        snapshot = build_snapshot(ROOT)
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            snapshot_path = base / "snapshot.json"
            receipt_path = base / "receipt.json"
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
            receipt = self._valid_pass_receipt(snapshot["source_snapshot_id"])
            receipt["authority_audit"]["stable_rules_reviewed"] = receipt[
                "authority_audit"
            ]["stable_rules_reviewed"][:1]
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            errors = validate_receipt(receipt_path, snapshot_path)
        self.assertTrue(
            any("missing required stable rule audits" in error for error in errors),
            errors,
        )

    def test_package_requires_valid_pass_receipt(self):
        self.assertIsNotNone(package_release, "package_release is not implemented")
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                package_release(
                    ROOT,
                    Path(folder) / "missing.json",
                    Path(folder) / "x.zip",
                )

    def test_install_rejects_relative_destination(self):
        self.assertIsNotNone(install_local, "install_local is not implemented")
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "empty.zip"
            with zipfile.ZipFile(archive, "w"):
                pass
            with self.assertRaises(ValueError):
                install_local(archive, Path("relative-install"))

    def test_install_rejects_existing_destination_and_reads_back_files(self):
        self.assertIsNotNone(install_local, "install_local is not implemented")
        archive = ROOT / "dist/recruiting-decision-coordinator-0.1.0.zip"
        if not archive.is_file():
            self.skipTest("release archive is created only after Source Gate pass")
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "installed-agent"
            installed = install_local(archive, destination)
            self.assertEqual(installed, destination)
            self.assertTrue((destination / "SYSTEM_PROMPT.md").is_file())
            self.assertTrue((destination / ".installation-receipt.json").is_file())
            with self.assertRaises(FileExistsError):
                install_local(archive, destination)

    @staticmethod
    def _valid_pass_receipt(snapshot_id):
        return {
            "review_mode": "source-gate",
            "review_scope": "isolated-subagent",
            "review_round": 2,
            "verdict": "pass",
            "lowest_failed_layer": "none",
            "decisive_reason": "No material blocker remains.",
            "evidence": ["evaluation/cases.json contains nine self-contained fixtures"],
            "preserve": ["SYSTEM_PROMPT.md preserves the human decision boundary"],
            "return_to": "delivery-finalizer",
            "next_action": "Package unchanged source.",
            "change_condition": "Source or authority changes.",
            "reviewed_snapshot_id": snapshot_id,
            "grounding_audit": "not_applicable",
            "source_audit": {
                "normal_case_replay": "pass",
                "highest_risk_case_replay": "pass",
                "finding_classification_consistent": True,
                "unsupported_scope_expansion_found": False,
                "skill_dependency_closure": "pass",
            },
            "materiality_audit": {
                "overall_goal": "Support recruiter decisions.",
                "consumer_decision": "Choose the next lawful recruiting action.",
                "first_release_boundary": "Job, evidence, interview, coordination.",
                "material_blocker_found": False,
                "material_effect": "No unresolved material effect.",
                "same_failure_family_scope": ["all source assets"],
                "deferred_non_blocking": [],
                "late_round_blocking_justification": "not_applicable",
            },
            "authority_audit": {
                "stable_rules_reviewed": [
                    {
                        "rule_id": "consumer-decision-responsibility",
                        "rule": "Recruiters consume the result; hiring managers retain professional hiring responsibility.",
                        "artifact": "SYSTEM_PROMPT.md, README.md and three skills",
                        "business_effect": "Defines the consumer and final responsibility boundary.",
                        "source_kind": "user-confirmed",
                        "source": "DESIGN_CONTEXT.md DEC-0003",
                    },
                    {
                        "rule_id": "high-impact-human-gate",
                        "rule": "High-impact messages require human approval.",
                        "artifact": "SYSTEM_PROMPT.md and runtime contract",
                        "business_effect": "Prevents unauthorized candidate communication.",
                        "source_kind": "user-confirmed",
                        "source": "DESIGN_CONTEXT.md DEC-0004",
                    },
                    {
                        "rule_id": "runtime-standard-authority",
                        "rule": "Formal standards require identity, source, version, scope and responsibility.",
                        "artifact": "SYSTEM_PROMPT.md, three skills and runtime contract",
                        "business_effect": "Controls whether formal professional judgments are effective.",
                        "source_kind": "reversible-design-default",
                        "source": "Grounding Gate runtime-input-only authority contract",
                    },
                    {
                        "rule_id": "aggregation-authorization",
                        "rule": "Formal scores require authorized aggregation and deterministic scoring.",
                        "artifact": "SYSTEM_PROMPT.md and candidate evidence skill",
                        "business_effect": "Prevents invented ranking and rejection decisions.",
                        "source_kind": "reversible-design-default",
                        "source": "Approved responsibility boundary and runtime standard contract",
                    },
                    {
                        "rule_id": "fair-screening-boundary",
                        "rule": "Unrelated protected traits and proxies cannot drive screening.",
                        "artifact": "SYSTEM_PROMPT.md, skills and evaluation cases",
                        "business_effect": "Prevents unfair candidate screening.",
                        "source_kind": "formal-material",
                        "source": "Grounded legal sources recorded in DESIGN_CONTEXT.md",
                    },
                    {
                        "rule_id": "platform-evidence-boundary",
                        "rule": "Unconnected tools and designed tests cannot be claimed as runtime evidence.",
                        "artifact": "PACKAGE.yaml, README.md, runtime contract and evaluation",
                        "business_effect": "Limits platform and behavior claims to actual evidence.",
                        "source_kind": "verified-platform-fact",
                        "source": "Current environment has no connected target platform tools or model runs",
                    },
                    {
                        "rule_id": "source-gate-packaging-authority",
                        "rule": "Packaging requires a complete pass receipt bound to the frozen source.",
                        "artifact": "delivery scripts and tests",
                        "business_effect": "Prevents unreviewed source from becoming an installable ZIP.",
                        "source_kind": "formal-material",
                        "source": "isolated-review-contract.md Source Gate pass contract",
                    }
                ],
                "unresolved_or_unauthorized": [],
            },
        }


if __name__ == "__main__":
    unittest.main()
