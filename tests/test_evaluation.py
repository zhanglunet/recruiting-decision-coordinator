from pathlib import Path
import json
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

try:
    from validate import validate_cases
except ImportError:
    validate_cases = None


EXPECTED_IDS = {
    "specialist-jd-channel-projection",
    "candidate-evidence-normal",
    "aggregation-rule-missing",
    "discriminatory-proxy-request",
    "standard-version-conflict",
    "structured-interview-current-model",
    "scheduling-partial-success",
    "high-impact-message-human-gate",
    "dashboard-incomparable-periods",
}


class EvaluationTests(unittest.TestCase):
    def test_suite_has_nine_exact_cases(self):
        suite = json.loads(
            (ROOT / "evaluation/cases.json").read_text(encoding="utf-8")
        )
        self.assertEqual({case["id"] for case in suite["cases"]}, EXPECTED_IDS)
        self.assertEqual(suite["evidence_status"], "designed_not_run")

    def test_all_cases_are_structurally_valid(self):
        self.assertIsNotNone(validate_cases, "validate_cases is not implemented")
        self.assertEqual(validate_cases(ROOT), [])

    def test_high_risk_cases_encode_prohibited_outcomes(self):
        suite = json.loads(
            (ROOT / "evaluation/cases.json").read_text(encoding="utf-8")
        )
        by_id = {case["id"]: case for case in suite["cases"]}
        self.assertTrue(by_id["aggregation-rule-missing"]["prohibited_behaviors"])
        self.assertTrue(by_id["discriminatory-proxy-request"]["prohibited_behaviors"])
        self.assertTrue(by_id["high-impact-message-human-gate"]["prohibited_behaviors"])

    def test_formal_standard_cases_are_self_contained(self):
        suite = json.loads(
            (ROOT / "evaluation/cases.json").read_text(encoding="utf-8")
        )
        by_id = {case["id"]: case for case in suite["cases"]}
        candidate = "\n".join(by_id["candidate-evidence-normal"]["runtime_standards"])
        interview = "\n".join(
            by_id["structured-interview-current-model"]["runtime_standards"]
        )
        for marker in ("来源", "批准责任人", "维护责任人"):
            self.assertIn(marker, candidate)
            self.assertIn(marker, interview)
        for marker in ("问题解决", "客户影响", "协作", "行为锚点"):
            self.assertIn(marker, interview)

    def test_scheduling_case_does_not_accept_send_without_prerequisites(self):
        suite = json.loads(
            (ROOT / "evaluation/cases.json").read_text(encoding="utf-8")
        )
        case = next(
            item
            for item in suite["cases"]
            if item["id"] == "scheduling-partial-success"
        )
        messaging = next(item for item in case["mock_tools"] if item["tool"] == "messaging")
        self.assertEqual(messaging["result_status"], "permission_denied")
        self.assertNotIn("receipts", messaging)
        self.assertTrue(any("不得声明消息已发送" in item for item in case["expected_behaviors"]))


if __name__ == "__main__":
    unittest.main()
