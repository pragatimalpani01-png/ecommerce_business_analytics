"""Create a small SQLite database from the project's analysis outputs."""
from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
TABLES = OUT / "tables"
DB_PATH = OUT / "marketplace_analysis.db"
TABLE_MAP = {
    "order_fact": "order_fact.csv",
    "item_fact": "item_fact.csv",
    "monthly_performance": "monthly_performance.csv",
    "category_performance": "category_performance.csv",
    "seller_service_scorecard": "seller_service_scorecard.csv",
    "customer_cohort_activity": "customer_cohort_activity.csv",
    "payment_method_summary": "payment_method_summary.csv",
    "data_quality_checks": "data_quality_checks.csv",
}

def main():
    if not (TABLES / "order_fact.csv").exists():
        raise FileNotFoundError("Run scripts/analyze.py before building the SQLite database.")
    if DB_PATH.exists(): DB_PATH.unlink()
    with sqlite3.connect(DB_PATH) as con:
        for table, filename in TABLE_MAP.items():
            path = TABLES / filename
            if path.exists():
                df = pd.read_csv(path)
                df.to_sql(table, con, index=False, if_exists="replace")
        con.execute("CREATE TABLE project_notes (note TEXT NOT NULL)")
        con.execute("INSERT INTO project_notes(note) VALUES (?)", (
            "Item value and freight are not profit. Reviews are order-level. Check outputs/tables/data_quality_checks.csv before interpreting results.",
        ))
    print(f"SQLite database created: {DB_PATH}")

if __name__ == "__main__": main()
