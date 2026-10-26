"""Download the original Olist public dataset through the Kaggle CLI.

A free Kaggle account and acceptance of the dataset terms are required.
No paid service or API subscription is used.
"""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATASET = "olistbr/brazilian-ecommerce"
REQUIRED = [
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_products_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_sellers_dataset.csv",
]


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    if not shutil.which("kaggle"):
        print("The Kaggle CLI is not installed. Run: pip install kaggle")
        print("Then configure your Kaggle API credentials, or download the dataset ZIP from:")
        print("https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce")
        print(f"Extract the CSV files into: {RAW}")
        return 2
    command = ["kaggle", "datasets", "download", "-d", DATASET, "-p", str(RAW), "--unzip"]
    print("Downloading the Olist public dataset. Kaggle may ask you to accept the data terms first.")
    result = subprocess.run(command, check=False)
    if result.returncode:
        print("Kaggle could not download the files. Check that your API token is configured and that you accepted the dataset terms.")
        print("You can also download the ZIP manually from the dataset page and extract it into data/raw/.")
        return result.returncode
    missing = [name for name in REQUIRED if not (RAW / name).exists()]
    if missing:
        print("Download finished, but some expected files are missing:")
        print("\n".join(missing))
        return 3
    print(f"Dataset files are ready in {RAW}")
    print("Next run: python run_project.py --source raw")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
