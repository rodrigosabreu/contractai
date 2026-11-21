import unittest

from app.services.analysis import AnalysisService


class RiskSummaryTests(unittest.TestCase):
    def test_recalculates_missing_and_existing_counts(self):
        result = AnalysisService()._validate_and_enhance_result(
            {"clauses": [{"content": "Cláusula fictícia A", "risk_level": "low"},
                         {"content": "Cláusula fictícia B", "risk_level": "high"}],
             "risk_summary": {"high_risk": 42, "note": "context"}}, "full"
        )
        self.assertEqual(result["risk_summary"]["low_risk"], 1)
        self.assertEqual(result["risk_summary"]["high_risk"], 1)
        self.assertEqual(result["risk_summary"]["total_clauses"], 2)
        self.assertEqual(result["risk_summary"]["note"], "context")


if __name__ == "__main__":
    unittest.main()
