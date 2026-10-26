"""Run the full project: analysis, charts, dashboard, SQL database and PDF report."""
from pathlib import Path
import argparse
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

def run(args):
    print("\n$", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)

def main():
    parser = argparse.ArgumentParser(description="Run the marketplace analytics project end to end.")
    parser.add_argument("--source", choices=["auto", "demo", "raw"], default="auto")
    args = parser.parse_args()
    py = sys.executable
    run([py, "scripts/analyze.py", "--source", args.source])
    run([py, "scripts/build_sqlite_db.py"])
    run([py, "scripts/build_report.py"])
    print("\nAll done. Open outputs/dashboard.html or reports/marketplace_performance_review.pdf.")

if __name__ == "__main__": main()
