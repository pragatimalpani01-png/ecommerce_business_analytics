import json
import unittest
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

class ProjectOutputTests(unittest.TestCase):
    def test_demo_run_is_marked_as_demo(self):
        metrics = json.loads((ROOT / "outputs" / "metrics.json").read_text(encoding="utf-8"))
        self.assertEqual(metrics["dataset_mode"], "synthetic_demo")
        self.assertEqual(metrics["order_count"], 1800)
        self.assertGreater(metrics["delivered_orders"], 0)
        self.assertIn("not profit", metrics["note"])

    def test_order_fact_has_one_row_per_order(self):
        fact = pd.read_csv(ROOT / "outputs" / "tables" / "order_fact.csv")
        self.assertEqual(len(fact), 1800)
        self.assertEqual(fact["order_id"].nunique(), len(fact))
        self.assertIn("promise_gap_days", fact.columns)

    def test_main_artifacts_exist(self):
        for rel in [
            "outputs/dashboard.html",
            "outputs/service_recovery_planner.html",
            "outputs/marketplace_analysis.db",
            "outputs/analysis_summary.md",
            "reports/marketplace_performance_review.pdf",
            "visualizations/category_opportunity_map.png",
            "outputs/tables/data_quality_checks.csv",
        ]:
            self.assertTrue((ROOT / rel).exists(), rel)

    def test_report_and_dashboard_disclose_demo_data(self):
        summary = (ROOT / "outputs" / "analysis_summary.md").read_text(encoding="utf-8")
        dashboard = (ROOT / "outputs" / "dashboard.html").read_text(encoding="utf-8")
        self.assertIn("synthetic demo data", summary)
        self.assertIn("DEMO DATA", dashboard)

if __name__ == "__main__":
    unittest.main()
