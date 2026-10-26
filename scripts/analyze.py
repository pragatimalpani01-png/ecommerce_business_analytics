"""End-to-end Olist-style marketplace analysis.

Usage:
    python scripts/analyze.py --source auto
    python scripts/analyze.py --source demo
    python scripts/analyze.py --source raw

The included demo tables are synthetic and are intended only to test the workflow.
The raw mode uses CSVs downloaded from the official Olist dataset page.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "data" / "demo"
RAW = ROOT / "data" / "raw"
OUT = ROOT / "outputs"
TABLES = OUT / "tables"
FIGURES = ROOT / "visualizations"

# A restrained palette that holds up in README screenshots and PDF reports.
NAVY = "#17324D"
TEAL = "#168C8C"
ORANGE = "#E28B43"
RED = "#C95C54"
BLUE = "#4C78A8"
MUTED = "#66788A"
GRID = "#E6EBF0"
BG = "#FFFFFF"

REQUIRED_RAW = {
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
}
DEMO_FILES = {
    "orders": "demo_orders.csv",
    "items": "demo_order_items.csv",
    "customers": "demo_customers.csv",
    "products": "demo_products.csv",
    "payments": "demo_order_payments.csv",
    "reviews": "demo_order_reviews.csv",
    "sellers": "demo_sellers.csv",
}


def load_tables(source: str) -> tuple[dict[str, pd.DataFrame], str]:
    raw_ok = all((RAW / f).exists() for f in REQUIRED_RAW.values())
    if source == "raw" and not raw_ok:
        missing = [f for f in REQUIRED_RAW.values() if not (RAW / f).exists()]
        raise FileNotFoundError("Raw data is incomplete. Missing: " + ", ".join(missing))
    use_raw = source == "raw" or (source == "auto" and raw_ok)
    if use_raw:
        tables = {k: pd.read_csv(RAW / filename) for k, filename in REQUIRED_RAW.items()}
        tr_path = RAW / "product_category_name_translation.csv"
        tables["translation"] = pd.read_csv(tr_path) if tr_path.exists() else pd.DataFrame(columns=["product_category_name", "product_category_name_english"])
        return tables, "Olist public dataset"
    tables = {k: pd.read_csv(DEMO / filename) for k, filename in DEMO_FILES.items()}
    tables["translation"] = pd.read_csv(DEMO / "demo_category_translation.csv")
    return tables, "synthetic demo data"


def standardize_tables(t: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Standardize known fields without changing the source files."""
    t = {k: df.copy() for k, df in t.items()}
    # Some older copies use slightly different spelling in product metadata; we only need the category here.
    for name, df in t.items():
        df.columns = [str(c).strip() for c in df.columns]
        t[name] = df
    for name in ["orders", "items", "customers", "products", "payments", "reviews", "sellers"]:
        if name not in t:
            raise KeyError(f"Missing table: {name}")
    for col in ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"]:
        if col in t["orders"].columns:
            t["orders"][col] = pd.to_datetime(t["orders"][col], errors="coerce")
    if "review_score" in t["reviews"].columns:
        t["reviews"]["review_score"] = pd.to_numeric(t["reviews"]["review_score"], errors="coerce")
    for col in ["price", "freight_value"]:
        if col in t["items"].columns:
            t["items"][col] = pd.to_numeric(t["items"][col], errors="coerce").fillna(0)
    if "payment_value" in t["payments"].columns:
        t["payments"]["payment_value"] = pd.to_numeric(t["payments"]["payment_value"], errors="coerce").fillna(0)
    if "product_category_name_english" not in t["translation"].columns:
        t["translation"] = pd.DataFrame(columns=["product_category_name", "product_category_name_english"])
    return t


def safe_divide(a, b):
    return float(a / b) if pd.notna(b) and b not in (0, None) else None


def build_analysis(t: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame | dict]:
    orders = t["orders"].copy()
    items = t["items"].copy()
    customers = t["customers"].copy()
    products = t["products"].copy()
    payments = t["payments"].copy()
    reviews = t["reviews"].copy()
    sellers = t["sellers"].copy()
    translation = t["translation"].copy()

    # Protect the joins from accidental row multiplication.
    if "order_id" not in orders or "order_id" not in items:
        raise KeyError("Both the orders and items tables must contain order_id.")
    items = items.merge(products[[c for c in ["product_id", "product_category_name"] if c in products]], on="product_id", how="left")
    if len(translation) and "product_category_name" in translation:
        items = items.merge(translation[["product_category_name", "product_category_name_english"]].drop_duplicates("product_category_name"), on="product_category_name", how="left")
        items["category"] = items["product_category_name_english"].fillna(items["product_category_name"])
    elif "product_category_name" in items:
        items["category"] = items["product_category_name"]
    else:
        items["category"] = "Unclassified"
    items["category"] = items["category"].fillna("Unclassified").astype(str).str.replace("_", " ", regex=False).str.title()
    items["price"] = pd.to_numeric(items.get("price", 0), errors="coerce").fillna(0)
    items["freight_value"] = pd.to_numeric(items.get("freight_value", 0), errors="coerce").fillna(0)

    item_agg = items.groupby("order_id", as_index=False).agg(
        item_sales_brl=("price", "sum"),
        freight_brl=("freight_value", "sum"),
        item_count=("order_item_id", "count") if "order_item_id" in items.columns else ("price", "size"),
        seller_count=("seller_id", "nunique") if "seller_id" in items.columns else ("order_id", "size"),
    )
    pay_agg = payments.groupby("order_id", as_index=False).agg(
        payment_value_brl=("payment_value", "sum"),
        payment_type_count=("payment_type", "nunique") if "payment_type" in payments.columns else ("order_id", "size"),
    )
    if "review_score" in reviews.columns:
        review_agg = reviews.groupby("order_id", as_index=False).agg(
            review_score=("review_score", "mean"),
            review_count=("review_score", "count"),
        )
    else:
        review_agg = pd.DataFrame(columns=["order_id", "review_score", "review_count"])

    customer_cols = [c for c in ["customer_id", "customer_unique_id", "customer_state", "customer_city"] if c in customers.columns]
    fact = orders.merge(item_agg, on="order_id", how="left", validate="one_to_one")
    fact = fact.merge(pay_agg, on="order_id", how="left", validate="one_to_one")
    fact = fact.merge(review_agg, on="order_id", how="left", validate="one_to_one")
    if "customer_id" in customers.columns:
        fact = fact.merge(customers[customer_cols].drop_duplicates("customer_id"), on="customer_id", how="left", validate="many_to_one")
    for col in ["item_sales_brl", "freight_brl", "item_count", "seller_count", "payment_value_brl", "review_count"]:
        if col in fact:
            fact[col] = fact[col].fillna(0)
    fact["gross_order_value_brl"] = fact["item_sales_brl"] + fact["freight_brl"]
    fact["purchase_month"] = fact["order_purchase_timestamp"].dt.to_period("M").astype(str)
    fact["purchase_date"] = fact["order_purchase_timestamp"].dt.date.astype(str)
    if "order_delivered_customer_date" in fact and "order_estimated_delivery_date" in fact:
        fact["delivery_days"] = (fact["order_delivered_customer_date"] - fact["order_purchase_timestamp"]).dt.total_seconds() / 86400
        fact["promise_gap_days"] = (fact["order_delivered_customer_date"] - fact["order_estimated_delivery_date"]).dt.total_seconds() / 86400
    else:
        fact["delivery_days"] = np.nan
        fact["promise_gap_days"] = np.nan
    delivered = fact["order_status"].eq("delivered") if "order_status" in fact.columns else fact["order_delivered_customer_date"].notna()
    fact["is_delivered"] = delivered
    fact["is_late"] = fact["is_delivered"] & fact["promise_gap_days"].gt(0)
    fact["is_reviewed"] = fact["review_score"].notna()
    fact["is_low_review"] = fact["review_score"].le(2)
    fact["is_late_low_review"] = fact["is_delivered"] & fact["is_late"] & fact["is_low_review"]
    fact["friction_order_value_brl"] = np.where(fact["is_late_low_review"], fact["item_sales_brl"], 0.0)
    fact["freight_share"] = np.where(fact["item_sales_brl"] > 0, fact["freight_brl"] / fact["item_sales_brl"], np.nan)

    delivered_fact = fact[fact["is_delivered"]].copy()
    reviewed_delivered = delivered_fact[delivered_fact["review_score"].notna()]
    order_count = len(fact)
    delivered_count = int(fact["is_delivered"].sum())
    reviewed_count = int(fact["is_reviewed"].sum())
    unique_customers = int(fact["customer_unique_id"].nunique()) if "customer_unique_id" in fact else None
    if "customer_unique_id" in fact:
        customer_orders = fact.groupby("customer_unique_id").size()
        repeat_customers = int((customer_orders > 1).sum())
        repeat_rate = safe_divide(repeat_customers, len(customer_orders))
    else:
        repeat_customers = None
        repeat_rate = None
    late_rate = safe_divide(int(delivered_fact["is_late"].sum()), delivered_count)
    low_rating_rate = safe_divide(int(reviewed_delivered["review_score"].le(2).sum()), len(reviewed_delivered))

    metrics = {
        "dataset_mode": "synthetic_demo" if t.get("_mode") == "synthetic demo data" else "source_data",
        "order_count": int(order_count),
        "delivered_orders": int(delivered_count),
        "delivered_order_share": safe_divide(delivered_count, order_count),
        "canceled_orders": int(fact.get("order_status", pd.Series(dtype=str)).eq("canceled").sum()),
        "cancellation_rate": safe_divide(int(fact.get("order_status", pd.Series(dtype=str)).eq("canceled").sum()), order_count),
        "delivered_item_sales_brl": float(delivered_fact["item_sales_brl"].sum()),
        "all_order_item_value_brl": float(fact["item_sales_brl"].sum()),
        "delivered_freight_brl": float(delivered_fact["freight_brl"].sum()),
        "average_delivered_order_item_value_brl": safe_divide(delivered_fact["item_sales_brl"].sum(), delivered_count),
        "average_freight_share": float(delivered_fact.loc[delivered_fact["item_sales_brl"] > 0, "freight_share"].mean()) if (delivered_fact["item_sales_brl"] > 0).any() else None,
        "on_time_delivery_rate": safe_divide(int((delivered_fact["promise_gap_days"] <= 0).sum()), int(delivered_fact["promise_gap_days"].notna().sum())),
        "late_delivery_rate": late_rate,
        "median_delivery_days": float(delivered_fact["delivery_days"].median()) if delivered_fact["delivery_days"].notna().any() else None,
        "average_promise_gap_days": float(delivered_fact["promise_gap_days"].mean()) if delivered_fact["promise_gap_days"].notna().any() else None,
        "average_review_score": float(reviewed_delivered["review_score"].mean()) if len(reviewed_delivered) else None,
        "low_review_share_among_reviewed_deliveries": low_rating_rate,
        "review_coverage_among_delivered_orders": safe_divide(len(reviewed_delivered), delivered_count),
        "unique_customers": unique_customers,
        "repeat_customer_share": repeat_rate,
        "orders_late_and_rated_1_or_2": int(fact["is_late_low_review"].sum()),
        "item_value_in_late_low_review_orders_brl": float(fact["friction_order_value_brl"].sum()),
        "note": "Item value and freight are not profit. This dataset does not include cost of goods, returns, discounts, taxes, or full operating costs.",
    }

    # Monthly performance. Delivered item value is shown separately from all order item value.
    monthly = fact.groupby("purchase_month", as_index=False).agg(
        orders=("order_id", "nunique"),
        delivered_orders=("is_delivered", "sum"),
        all_order_item_value_brl=("item_sales_brl", "sum"),
        delivered_item_sales_brl=("item_sales_brl", lambda s: float(s[fact.loc[s.index, "is_delivered"]].sum())),
        freight_brl=("freight_brl", lambda s: float(s[fact.loc[s.index, "is_delivered"]].sum())),
    ).sort_values("purchase_month")

    # Category performance is item-weighted, so orders with multiple categories can appear in more than one row.
    cat = items.merge(fact[["order_id", "order_purchase_timestamp", "order_status", "promise_gap_days", "review_score", "is_delivered", "customer_state"]].drop_duplicates("order_id"), on="order_id", how="left")
    cat["delivered_flag"] = cat["is_delivered"].fillna(False).astype(int)
    cat["delivered_order_id"] = cat["order_id"].where(cat["is_delivered"].fillna(False))
    cat["delivered_item_sales_brl"] = np.where(cat["delivered_flag"].eq(1), cat["price"], 0.0)
    cat["delivered_freight_brl"] = np.where(cat["delivered_flag"].eq(1), cat["freight_value"], 0.0)
    cat["late_line_flag"] = (cat["delivered_flag"].eq(1) & cat["promise_gap_days"].gt(0)).astype(int)
    cat["reviewed_delivery_line_flag"] = (cat["delivered_flag"].eq(1) & cat["review_score"].notna()).astype(int)
    cat["low_review_delivery_line_flag"] = (cat["reviewed_delivery_line_flag"].eq(1) & cat["review_score"].le(2)).astype(int)
    cat_summary = cat.groupby("category", as_index=False).agg(
        item_lines=("order_id", "size"),
        orders=("order_id", "nunique"),
        delivered_orders=("delivered_order_id", "nunique"),
        item_sales_brl=("price", "sum"),
        delivered_item_sales_brl=("delivered_item_sales_brl", "sum"),
        freight_brl=("freight_value", "sum"),
        delivered_freight_brl=("delivered_freight_brl", "sum"),
        average_item_price_brl=("price", "mean"),
        delivered_item_lines=("delivered_flag", "sum"),
        late_item_lines=("late_line_flag", "sum"),
        reviewed_item_lines=("reviewed_delivery_line_flag", "sum"),
        low_review_item_lines=("low_review_delivery_line_flag", "sum"),
    )
    cat_summary["freight_share"] = np.where(cat_summary["delivered_item_sales_brl"] > 0, cat_summary["delivered_freight_brl"] / cat_summary["delivered_item_sales_brl"], np.nan)
    cat_summary["low_review_share"] = np.where(cat_summary["reviewed_item_lines"] > 0, cat_summary["low_review_item_lines"] / cat_summary["reviewed_item_lines"], np.nan)
    cat_summary["late_share_item_line_proxy"] = np.where(cat_summary["delivered_item_lines"] > 0, cat_summary["late_item_lines"] / cat_summary["delivered_item_lines"], np.nan)
    cat_summary = cat_summary.sort_values("delivered_item_sales_brl", ascending=False)

    # Seller service scorecard. Only rank sellers with a meaningful minimum order count.
    if "seller_id" in items.columns:
        seller_lines = items.merge(fact[["order_id", "is_delivered", "promise_gap_days", "review_score", "item_sales_brl"]], on="order_id", how="left")
        seller_lines["delivered_flag"] = seller_lines["is_delivered"].fillna(False).astype(int)
        seller_lines["delivered_price"] = np.where(seller_lines["delivered_flag"].eq(1), seller_lines["price"], 0.0)
        seller_lines["delivered_order_id"] = seller_lines["order_id"].where(seller_lines["delivered_flag"].eq(1))
        seller_lines["late_line_flag"] = (seller_lines["delivered_flag"].eq(1) & seller_lines["promise_gap_days"].gt(0)).astype(int)
        seller_lines["reviewed_line_flag"] = (seller_lines["delivered_flag"].eq(1) & seller_lines["review_score"].notna()).astype(int)
        seller_lines["low_review_line_flag"] = (seller_lines["reviewed_line_flag"].eq(1) & seller_lines["review_score"].le(2)).astype(int)
        seller_lines["delivered_review_score"] = seller_lines["review_score"].where(seller_lines["reviewed_line_flag"].eq(1))
        seller_summary = seller_lines.groupby("seller_id", as_index=False).agg(
            item_lines=("order_id", "size"),
            orders=("order_id", "nunique"),
            delivered_orders=("delivered_order_id", "nunique"),
            delivered_item_lines=("delivered_flag", "sum"),
            delivered_item_value_brl=("delivered_price", "sum"),
            late_lines=("late_line_flag", "sum"),
            reviewed_lines=("reviewed_line_flag", "sum"),
            low_review_lines=("low_review_line_flag", "sum"),
            average_review=("delivered_review_score", "mean"),
        )
        seller_summary["late_share"] = seller_summary["late_lines"] / seller_summary["delivered_item_lines"].replace(0, np.nan)
        seller_summary["low_review_share"] = seller_summary["low_review_lines"] / seller_summary["reviewed_lines"].replace(0, np.nan)
        seller_summary["service_friction_index"] = 100 * (0.55 * seller_summary["late_share"].fillna(0) + 0.45 * seller_summary["low_review_share"].fillna(0))
        seller_summary["rank_eligible"] = seller_summary["delivered_orders"] >= 10
        seller_summary = seller_summary.sort_values("service_friction_index", ascending=False)
    else:
        seller_summary = pd.DataFrame()

    # Customer cohorts: monthly retention measured in repeat order activity, not active users.
    cohort_table = pd.DataFrame()
    if "customer_unique_id" in fact and fact["customer_unique_id"].notna().any():
        cust = fact.dropna(subset=["customer_unique_id", "order_purchase_timestamp"]).copy()
        cust["order_month"] = cust["order_purchase_timestamp"].dt.to_period("M")
        cust["cohort_month"] = cust.groupby("customer_unique_id")["order_purchase_timestamp"].transform("min").dt.to_period("M")
        cust["cohort_age_month"] = (cust["order_month"].dt.year - cust["cohort_month"].dt.year) * 12 + (cust["order_month"].dt.month - cust["cohort_month"].dt.month)
        cohort_table = cust.groupby(["cohort_month", "cohort_age_month"])["customer_unique_id"].nunique().reset_index(name="customers_with_orders")
        cohort_sizes = cust.groupby("cohort_month")["customer_unique_id"].nunique().rename("cohort_size")
        cohort_table = cohort_table.join(cohort_sizes, on="cohort_month")
        cohort_table["order_activity_share"] = cohort_table["customers_with_orders"] / cohort_table["cohort_size"]
        cohort_table["cohort_month"] = cohort_table["cohort_month"].astype(str)
        cohort_table = cohort_table.sort_values(["cohort_month", "cohort_age_month"])

    if "payment_type" in payments.columns:
        payments_with_delivery = payments.merge(fact[["order_id", "is_delivered"]], on="order_id", how="left")
        payments_with_delivery["delivered_payment_flag"] = payments_with_delivery["is_delivered"].fillna(False).astype(int)
        payment_summary = payments_with_delivery.groupby("payment_type", as_index=False).agg(
            payment_rows=("order_id", "size"),
            payment_value_brl=("payment_value", "sum"),
            payment_rows_on_delivered_orders=("delivered_payment_flag", "sum"),
        )
    else:
        payment_summary = pd.DataFrame()

    # Quality checks matter because joins and timestamps can quietly distort business metrics.
    checks = []
    def check(name, value, detail): checks.append({"check": name, "value": value, "interpretation": detail})
    check("orders_rows", len(orders), "Expected one row per order.")
    check("duplicate_order_ids", int(orders["order_id"].duplicated().sum()), "Should be zero.")
    check("items_without_order", int((~items["order_id"].isin(orders["order_id"])).sum()), "Item lines without a matching order.")
    check("orders_without_items", int((~orders["order_id"].isin(items["order_id"])).sum()), "May be valid for canceled or unavailable orders; inspect before treating as missing revenue.")
    check("delivered_orders_missing_delivery_date", int((fact["is_delivered"] & fact["order_delivered_customer_date"].isna()).sum()), "A delivered status without a delivery timestamp needs attention.")
    check("delivered_orders_missing_estimate", int((fact["is_delivered"] & fact["order_estimated_delivery_date"].isna()).sum()), "Cannot assess promise performance for these orders.")
    check("reviews_without_order", int((~reviews["order_id"].isin(orders["order_id"])).sum()), "Reviews without a matching order.")
    check("orders_with_multiple_review_rows", int((reviews.groupby("order_id").size() > 1).sum()), "Review rows grouped to order-level average for this analysis.")
    if "payment_value_brl" in fact:
        paid = fact["payment_value_brl"].notna() & (fact["payment_value_brl"] > 0)
        abs_diff = (fact.loc[paid, "payment_value_brl"] - fact.loc[paid, "gross_order_value_brl"]).abs()
        check("median_abs_payment_vs_item_plus_freight_gap_brl", round(float(abs_diff.median()), 2) if len(abs_diff) else None, "Differences can arise from data issues, installments, or source-table conventions; investigate large gaps.")
    quality = pd.DataFrame(checks)

    # Keep both the item-level table and one row per order for transparent reuse.
    fact_columns = [c for c in ["order_id", "customer_id", "customer_unique_id", "customer_state", "order_status", "order_purchase_timestamp", "purchase_month", "item_count", "seller_count", "item_sales_brl", "freight_brl", "gross_order_value_brl", "payment_value_brl", "delivery_days", "promise_gap_days", "is_delivered", "is_late", "review_score", "is_reviewed", "is_low_review", "is_late_low_review", "friction_order_value_brl", "freight_share"] if c in fact.columns]
    return {
        "metrics": metrics,
        "order_fact": fact[fact_columns].copy(),
        "monthly": monthly,
        "categories": cat_summary,
        "sellers": seller_summary,
        "cohorts": cohort_table,
        "payments": payment_summary,
        "quality": quality,
        "items_enriched": items,
    }


def fmt_money(x, _pos=None):
    return f"R${x:,.0f}"


def setup_ax(ax, title, ylabel=None):
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color=NAVY, pad=12)
    if ylabel: ax.set_ylabel(ylabel, color=MUTED)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, labelsize=9)


def make_charts(a: dict, display_name: str):
    FIGURES.mkdir(parents=True, exist_ok=True)
    metrics = a["metrics"]
    monthly = a["monthly"]
    categories = a["categories"]
    sellers = a["sellers"]
    cohorts = a["cohorts"]
    order_fact = a["order_fact"]
    items = a["items_enriched"]
    demo_flag = "DEMO DATA" if display_name == "synthetic demo data" else "OLIST SOURCE DATA"

    # 1. Monthly performance
    fig, ax1 = plt.subplots(figsize=(11, 5.6), facecolor=BG)
    ax1.set_facecolor(BG)
    x = np.arange(len(monthly))
    ax1.bar(x, monthly["orders"], color=GRID, width=.72, label="Orders placed")
    ax1.set_ylabel("Orders", color=MUTED)
    ax2 = ax1.twinx()
    ax2.plot(x, monthly["delivered_item_sales_brl"], color=TEAL, linewidth=2.6, marker="o", markersize=3.5, label="Delivered item value")
    ax2.set_ylabel("Delivered item value (BRL)", color=MUTED)
    ax2.yaxis.set_major_formatter(FuncFormatter(fmt_money))
    ax1.set_xticks(x)
    ax1.set_xticklabels(monthly["purchase_month"], rotation=45, ha="right", fontsize=8)
    ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False); ax1.spines["left"].set_color(GRID); ax1.spines["bottom"].set_color(GRID)
    ax2.spines["top"].set_visible(False); ax2.spines["left"].set_visible(False); ax2.spines["right"].set_color(GRID)
    ax1.grid(axis="y", color=GRID)
    ax1.set_axisbelow(True)
    ax1.set_title("Order activity and delivered item value", loc="left", fontsize=15, color=NAVY, fontweight="bold", pad=16)
    fig.text(.01, .01, f"{demo_flag} | Item value excludes freight and is not profit.", fontsize=9, color=MUTED)
    fig.tight_layout(rect=[0, .04, 1, 1])
    fig.savefig(FIGURES / "monthly_performance.png", dpi=170, bbox_inches="tight")
    plt.close(fig)

    # 2. Category opportunity map: revenue and service friction.
    c = categories.copy()
    c = c[c["delivered_orders"] >= max(3, int(c["delivered_orders"].median() * .35))].copy()
    if len(c):
        fig, ax = plt.subplots(figsize=(10.5, 6.5), facecolor=BG)
        ax.set_facecolor(BG)
        xval = c["delivered_item_sales_brl"]
        yval = c["low_review_share"].fillna(0) * 100
        sizes = 70 + 450 * c["delivered_orders"] / max(1, c["delivered_orders"].max())
        colors = c["late_share_item_line_proxy"].fillna(0) * 100
        sc = ax.scatter(xval, yval, s=sizes, c=colors, cmap="YlOrRd", alpha=.85, edgecolor="white", linewidth=.9)
        # Label only the larger sales categories and the categories with the strongest low-review signal.
        label_rows = pd.concat([c.nlargest(5, "delivered_item_sales_brl"), c.nlargest(3, "low_review_share")]).drop_duplicates("category")
        short_names = {"Computers Accessories": "Computers & acc.", "Fashion Bags Accessories": "Fashion & bags", "Bed Bath Table": "Bed/bath/table", "Health Beauty": "Health/beauty"}
        xmax = float(c["delivered_item_sales_brl"].max()) if len(c) else 0
        for _, r in label_rows.iterrows():
            yy = (r["low_review_share"] if pd.notna(r["low_review_share"]) else 0)*100
            label = short_names.get(r["category"], r["category"])
            if r["item_sales_brl"] > xmax * .82:
                ax.annotate(label, (r["delivered_item_sales_brl"], yy), xytext=(-7, 5), textcoords="offset points", ha="right", fontsize=7.5, color=NAVY)
            else:
                ax.annotate(label, (r["delivered_item_sales_brl"], yy), xytext=(5, 5), textcoords="offset points", ha="left", fontsize=7.5, color=NAVY)
        ax.xaxis.set_major_formatter(FuncFormatter(fmt_money))
        ax.set_xlabel("Delivered item value (BRL)", color=MUTED)
        ax.set_ylabel("Low-review share among reviewed item lines (%)", color=MUTED)
        setup_ax(ax, "Where sales and service problems meet")
        ax.grid(axis="x", color=GRID)
        cb = fig.colorbar(sc, ax=ax, pad=.02); cb.set_label("Late item-line share (%)", color=MUTED)
        fig.text(.01, .01, f"{demo_flag} | Bubble size reflects order count. This is a prioritization view, not proof of cause.", fontsize=8.5, color=MUTED)
        fig.tight_layout(rect=[0, .04, 1, 1])
        fig.savefig(FIGURES / "category_opportunity_map.png", dpi=170, bbox_inches="tight")
        plt.close(fig)

    # 3. Promise gap distribution
    gaps = order_fact.loc[order_fact["is_delivered"].eq(True), "promise_gap_days"].dropna()
    fig, ax = plt.subplots(figsize=(10.5, 5.5), facecolor=BG)
    ax.set_facecolor(BG)
    if len(gaps):
        lo, hi = np.percentile(gaps, [1, 99])
        bins = np.arange(np.floor(lo)-1, np.ceil(hi)+2, 1)
        ax.hist(gaps.clip(lo, hi), bins=bins, color=BLUE, alpha=.9, edgecolor="white")
        ax.axvline(0, color=RED, linewidth=2, linestyle="--", label="Promised date")
        ax.axvline(gaps.median(), color=TEAL, linewidth=2, label=f"Median: {gaps.median():.1f} days")
        ax.legend(frameon=False, loc="upper right")
    ax.set_xlabel("Actual delivery minus estimated delivery (days)", color=MUTED)
    ax.set_ylabel("Delivered orders", color=MUTED)
    setup_ax(ax, "The delivery promise gap")
    fig.text(.01, .01, f"{demo_flag} | Positive values mean late delivery; zero or below means on time or early.", fontsize=9, color=MUTED)
    fig.tight_layout(rect=[0, .04, 1, 1])
    fig.savefig(FIGURES / "promise_gap_distribution.png", dpi=170, bbox_inches="tight")
    plt.close(fig)

    # 4. Delivery versus review score, summarized in bins.
    tmp = order_fact[order_fact["is_delivered"].eq(True) & order_fact["review_score"].notna()].copy()
    tmp["gap_band"] = pd.cut(tmp["promise_gap_days"], bins=[-100,-7,-1,0,3,7,100], labels=["7+ days early","1-6 days early","On promise","1-3 days late","4-7 days late","8+ days late"], right=True)
    rel = tmp.groupby("gap_band", observed=False).agg(orders=("order_id","nunique"), average_review=("review_score","mean"), low_review_share=("is_low_review","mean")).reset_index()
    fig, ax = plt.subplots(figsize=(10.5, 5.5), facecolor=BG)
    ax.set_facecolor(BG)
    xx = np.arange(len(rel))
    bars = ax.bar(xx, rel["average_review"], color=[TEAL if str(x) in ("7+ days early", "1-6 days early", "On promise") else ORANGE for x in rel["gap_band"]], width=.66)
    ax.set_ylim(1, 5.25)
    ax.set_ylabel("Average review score (1 to 5)", color=MUTED)
    ax.set_xticks(xx); ax.set_xticklabels([str(x) for x in rel["gap_band"]], rotation=20, ha="right")
    for bar, n in zip(bars, rel["orders"]):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+.05, f"n={int(n)}", ha="center", va="bottom", fontsize=8, color=MUTED)
    setup_ax(ax, "Customer ratings across delivery experiences")
    ax.grid(axis="y", color=GRID)
    fig.text(.01, .01, f"{demo_flag} | Group differences are descriptive, not evidence that delays alone caused ratings.", fontsize=8.8, color=MUTED)
    fig.tight_layout(rect=[0, .04, 1, 1])
    fig.savefig(FIGURES / "delivery_review_relationship.png", dpi=170, bbox_inches="tight")
    plt.close(fig)

    # 5. Seller service friction: eligible sellers only, rank worst 12 and best 8 separately.
    s = sellers[sellers["rank_eligible"]].copy() if len(sellers) and "rank_eligible" in sellers else pd.DataFrame()
    if len(s):
        worst = s.nlargest(min(10, len(s)), "service_friction_index").sort_values("service_friction_index")
        fig, ax = plt.subplots(figsize=(10.5, 6), facecolor=BG)
        ax.set_facecolor(BG)
        bars = ax.barh(worst["seller_id"].str.replace("demo_", "", regex=False), worst["service_friction_index"], color=RED, alpha=.88)
        for b, n in zip(bars, worst["orders"]):
            ax.text(b.get_width()+.6, b.get_y()+b.get_height()/2, f"{b.get_width():.0f} | {int(n)} orders", va="center", fontsize=8, color=MUTED)
        ax.set_xlim(0, max(100, float(worst["service_friction_index"].max())+18))
        ax.set_xlabel("Service friction index (0 to 100)", color=MUTED)
        setup_ax(ax, "Sellers worth a closer look")
        fig.text(.01, .01, f"{demo_flag} | Index = 55% late share + 45% low-review share. Review small samples with care.", fontsize=8.6, color=MUTED)
        fig.tight_layout(rect=[0, .04, 1, 1])
        fig.savefig(FIGURES / "seller_service_friction.png", dpi=170, bbox_inches="tight")
        plt.close(fig)

    # 6. Retention/cohort heatmap (customer order activity, not subscription retention).
    if len(cohorts):
        piv = cohorts.pivot(index="cohort_month", columns="cohort_age_month", values="order_activity_share")
        # Limit columns to 12 months after acquisition for a readable portfolio screenshot.
        piv = piv.loc[:, [c for c in piv.columns if c <= 12]]
        fig, ax = plt.subplots(figsize=(11, max(4.5, min(8, len(piv)*.28))), facecolor=BG)
        ax.set_facecolor(BG)
        im = ax.imshow(piv.values * 100, cmap="Blues", aspect="auto", vmin=0, vmax=100)
        ax.set_yticks(np.arange(len(piv.index))); ax.set_yticklabels(piv.index, fontsize=7.5)
        ax.set_xticks(np.arange(len(piv.columns))); ax.set_xticklabels([f"M{int(c)}" for c in piv.columns])
        ax.set_xlabel("Months after first observed order", color=MUTED)
        ax.set_ylabel("First-order cohort", color=MUTED)
        ax.set_title("Repeat-order activity by customer cohort", loc="left", fontsize=14, color=NAVY, fontweight="bold", pad=14)
        cb = fig.colorbar(im, ax=ax, pad=.02); cb.set_label("Share of cohort placing an order (%)", color=MUTED)
        fig.text(.01, .01, f"{demo_flag} | Cohorts near the end of the period have less time to return.", fontsize=8.5, color=MUTED)
        fig.tight_layout(rect=[0, .04, 1, 1])
        fig.savefig(FIGURES / "customer_cohort_activity.png", dpi=170, bbox_inches="tight")
        plt.close(fig)

    # Interactive standalone dashboard using Plotly.
    try:
        fig = make_subplots(rows=2, cols=2, subplot_titles=(
            "Monthly delivered item value", "Category sales and low-review share",
            "Delivery promise gap", "Seller service friction"
        ), vertical_spacing=.14, horizontal_spacing=.11)
        fig.add_trace(go.Scatter(x=monthly["purchase_month"], y=monthly["delivered_item_sales_brl"], mode="lines+markers", name="Delivered item value", line=dict(color=TEAL, width=3)), row=1, col=1)
        cc = categories.nlargest(12, "delivered_item_sales_brl").sort_values("delivered_item_sales_brl")
        fig.add_trace(go.Bar(x=cc["delivered_item_sales_brl"], y=cc["category"], orientation="h", name="Item sales", marker_color=BLUE, customdata=np.stack([cc["low_review_share"].fillna(0)*100,cc["delivered_orders"]],axis=-1), hovertemplate="%{y}<br>Delivered item value: R$%{x:,.0f}<br>Low-review share: %{customdata[0]:.1f}%<br>Delivered orders: %{customdata[1]}<extra></extra>"), row=1, col=2)
        if len(gaps):
            fig.add_trace(go.Histogram(x=gaps, nbinsx=30, name="Promise gap", marker_color=ORANGE, opacity=.85), row=2, col=1)
            fig.add_vline(x=0, line_dash="dash", line_color=RED, row=2, col=1)
        if len(s):
            sw = s.nlargest(10, "service_friction_index").sort_values("service_friction_index")
            fig.add_trace(go.Bar(x=sw["service_friction_index"], y=sw["seller_id"], orientation="h", name="Friction index", marker_color=RED, customdata=sw["orders"], hovertemplate="%{y}<br>Index: %{x:.1f}<br>Orders: %{customdata}<extra></extra>"), row=2, col=2)
        fig.update_layout(
            title=dict(text=f"Marketplace performance review <sup>({demo_flag})</sup>", x=.02, xanchor="left", font=dict(size=24, color=NAVY)),
            template="plotly_white", height=900, width=1400, showlegend=False,
            margin=dict(l=45,r=45,t=95,b=55), font=dict(family="Arial, sans-serif", color=NAVY),
        )
        fig.update_xaxes(showgrid=True, gridcolor=GRID, zerolinecolor=GRID)
        fig.update_yaxes(showgrid=True, gridcolor=GRID, zerolinecolor=GRID)
        OUT.mkdir(exist_ok=True, parents=True)
        fig.write_html(OUT / "dashboard.html", include_plotlyjs=True, full_html=True)
    except Exception as e:
        warnings.warn(f"Could not build interactive Plotly dashboard: {e}")


def write_scenario_planner(metrics: dict, display_name: str):
    flagged_orders = int(metrics.get("orders_late_and_rated_1_or_2") or 0)
    flagged_value = float(metrics.get("item_value_in_late_low_review_orders_brl") or 0)
    banner = "DEMO DATA - illustrative only" if display_name == "synthetic demo data" else "Olist public dataset - historical data"
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Service Recovery Budget Planner</title>
<style>
:root{{--navy:#17324d;--teal:#168c8c;--orange:#e28b43;--muted:#64748b;--line:#e3eaf0;--paper:#f7f9fb}}
body{{margin:0;background:var(--paper);font:16px/1.5 Arial, sans-serif;color:var(--navy)}}
main{{max-width:920px;margin:40px auto;padding:0 20px}}h1{{font-size:30px;line-height:1.2;margin:10px 0}}.label{{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:var(--teal);font-weight:bold}}
.banner{{border-left:4px solid var(--orange);background:#fff5e9;padding:12px 16px;margin:20px 0;border-radius:4px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin:22px 0}}
.card{{background:white;border:1px solid var(--line);border-radius:12px;padding:18px;box-shadow:0 2px 7px #17324d0b}}
.value{{font-size:28px;font-weight:bold;margin-top:6px}}.muted{{color:var(--muted);font-size:13px}}
label{{display:block;font-weight:bold;margin:18px 0 8px}}input[type=range]{{width:100%;accent-color:var(--teal)}}input[type=number]{{padding:10px;border:1px solid var(--line);border-radius:8px;font-size:16px;width:120px}}
.row{{display:flex;gap:16px;align-items:center;flex-wrap:wrap}}.result{{background:var(--navy);color:white;border-radius:12px;padding:20px;margin-top:18px}}.result .muted{{color:#d8e2eb}}footer{{margin-top:26px;color:var(--muted);font-size:13px}}
</style></head><body><main>
<div class="label">E-commerce operations | Planning tool</div><h1>Service recovery budget planner</h1>
<p>Use this page to estimate the cost of contacting a subset of orders that were both delivered late and rated 1 or 2. It is a workload and budget estimate, not a forecast of recovered revenue.</p>
<div class="banner"><strong>{banner}</strong><br>The figures on this page come from the current project run. Run the analysis again after changing the dataset to refresh them.</div>
<div class="grid"><div class="card"><div class="muted">Orders meeting the flag</div><div class="value" id="flaggedOrders">{flagged_orders:,}</div><div class="muted">Late delivery and review score of 1 or 2</div></div>
<div class="card"><div class="muted">Item value linked to these orders</div><div class="value" id="flaggedValue">R$ {flagged_value:,.0f}</div><div class="muted">Not a financial loss or recoverable revenue</div></div></div>
<div class="card"><label for="coverage">Share of flagged orders to contact: <span id="coverageLabel">50%</span></label>
<input id="coverage" type="range" min="0" max="100" step="5" value="50">
<div class="row"><div><label for="unitCost">Cost per contact (R$)</label><input id="unitCost" type="number" min="0" max="1000" value="5" step="0.5"></div><div class="muted">Include staff time, messaging and any service credit if your team uses one. Keep the estimate consistent with your own cost assumptions.</div></div>
<div class="result"><div class="muted">Estimated contact workload</div><div class="value" id="contactCount">{round(flagged_orders*0.5):,} orders</div><div class="muted" style="margin-top:12px">Indicative budget</div><div class="value" id="budget">R$ {flagged_orders*0.5*5:,.2f}</div><div class="muted" style="margin-top:12px">Item value associated with the selected cases</div><div class="value" id="associatedValue">R$ {flagged_value*0.5:,.0f}</div></div></div>
<footer>Use this to compare coverage and cost assumptions before a pilot. To assess whether outreach pays off, track customer response, repeat purchases and actual intervention costs against a comparable group.</footer>
</main><script>
const flaggedOrders = {flagged_orders}; const flaggedValue = {flagged_value:.6f};
const coverage = document.getElementById('coverage'); const cost = document.getElementById('unitCost');
const money = n => new Intl.NumberFormat('en-US', {{style:'currency',currency:'BRL',maximumFractionDigits:2}}).format(n);
function update() {{ const rate = Number(coverage.value)/100; const n = Math.round(flaggedOrders*rate); const c = Math.max(0, Number(cost.value)||0);
 document.getElementById('coverageLabel').textContent = coverage.value+'%';
 document.getElementById('contactCount').textContent = n.toLocaleString('en-US')+' orders';
 document.getElementById('budget').textContent = money(n*c);
 document.getElementById('associatedValue').textContent = money(flaggedValue*rate);
}}
coverage.addEventListener('input',update); cost.addEventListener('input',update); update();
</script></body></html>'''
    (OUT / "service_recovery_planner.html").write_text(html, encoding="utf-8")


def write_outputs(a: dict, display_name: str):
    OUT.mkdir(exist_ok=True, parents=True); TABLES.mkdir(exist_ok=True, parents=True)
    metrics = a["metrics"]
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    write_scenario_planner(metrics, display_name)
    a["order_fact"].to_csv(TABLES / "order_fact.csv", index=False)
    a["items_enriched"].to_csv(TABLES / "item_fact.csv", index=False)
    a["monthly"].to_csv(TABLES / "monthly_performance.csv", index=False)
    a["categories"].to_csv(TABLES / "category_performance.csv", index=False)
    a["sellers"].to_csv(TABLES / "seller_service_scorecard.csv", index=False)
    a["cohorts"].to_csv(TABLES / "customer_cohort_activity.csv", index=False)
    a["payments"].to_csv(TABLES / "payment_method_summary.csv", index=False)
    a["quality"].to_csv(TABLES / "data_quality_checks.csv", index=False)

    currency = lambda x: "not available" if x is None or pd.isna(x) else f"R$ {x:,.0f}"
    pct = lambda x: "not available" if x is None or pd.isna(x) else f"{x*100:.1f}%"
    demo = display_name == "synthetic demo data"
    median_delivery_text = "not available" if metrics["median_delivery_days"] is None else f"{metrics['median_delivery_days']:.1f} days"
    average_review_text = "not available" if metrics["average_review_score"] is None else f"{metrics['average_review_score']:.2f} / 5"
    lines = [
        "# Analyst notes: marketplace performance review",
        "",
        ("**Important: this run uses synthetic demo data, not Olist's original transactions.** The figures below confirm that the workflow runs; they are not business findings about Olist." if demo else "This report was generated from the Olist public dataset. It is a descriptive analysis, not a causal study."),
        "",
        "## What the run covers",
        "",
        f"The analysis processed {metrics['order_count']:,} orders, of which {metrics['delivered_orders']:,} are marked delivered. Item value is tracked separately from freight. The source does not include enough cost information to calculate actual profit or margin.",
        "",
        "## Scorecard",
        "",
        "| Measure | Result |",
        "|---|---:|",
        f"| Orders | {metrics['order_count']:,} |",
        f"| Delivered orders | {metrics['delivered_orders']:,} |",
        f"| Delivered order share | {pct(metrics['delivered_order_share'])} |",
        f"| Canceled orders | {metrics['canceled_orders']:,} |",
        f"| Cancellation rate | {pct(metrics['cancellation_rate'])} |",
        f"| Delivered item value | {currency(metrics['delivered_item_sales_brl'])} |",
        f"| Delivered freight value | {currency(metrics['delivered_freight_brl'])} |",
        f"| Average item value per delivered order | {currency(metrics['average_delivered_order_item_value_brl'])} |",
        f"| On-time delivery rate | {pct(metrics['on_time_delivery_rate'])} |",
        f"| Median delivery time | {median_delivery_text} |",
        f"| Average review score | {average_review_text} |",
        f"| Review coverage among delivered orders | {pct(metrics['review_coverage_among_delivered_orders'])} |",
        f"| Repeat-customer share | {pct(metrics['repeat_customer_share'])} |",
        f"| Item value in late, low-rated orders | {currency(metrics['item_value_in_late_low_review_orders_brl'])} |",
        "",
        "## How to read the analysis",
        "",
        "### 1. Follow the delivery promise, not only average delivery time",
        "The promise gap is the actual delivery date minus the estimated delivery date. A positive value means the order arrived late. Median delivery time can look reasonable even while a meaningful group of customers receive orders after the promised date, so the distribution and the share arriving late deserve separate attention.",
        "",
        "### 2. Prioritize categories where sales and poor experiences overlap",
        "The category opportunity chart puts delivered item value beside low-review share and uses late delivery as another signal. It helps narrow the first set of categories to investigate. Reviews are attached to the order, not to individual product lines, so a review for a multi-item order is associated with each category in that order. It does not prove that shipping delays caused the lower ratings, and a category with few reviews should not be treated as a reliable outlier.",
        "",
        "### 3. Use seller rankings as a queue for investigation",
        "The seller service-friction index is a simple screening score: 55% late share plus 45% low-review share, scaled to 0-100. It is not an official performance measure. Review eligibility, order count, product mix and destination mix before taking action on any seller.",
        "",
        "### 4. Separate value at risk from a financial loss",
        "The report counts item value in orders that were both late and rated 1 or 2. That is the value of orders associated with a poor service outcome, not lost revenue and not an estimate of refunds. The data does not show whether customers returned items or stopped buying.",
        "",
        "### 5. Look at customer cohorts without overstating retention",
        "Cohort activity shows the share of customers in each first-order month who placed an order again in a later month. It is a practical repeat-order view, but the newest cohorts have less time to return and the historical window ends in 2018.",
        "",
        "## Business actions to test",
        "",
        "1. Start with the categories that combine material sales with high late-delivery and low-review rates. Check stock location, carrier hand-offs, estimated delivery promises and product handling before changing assortment or pricing.",
        "2. Give the operations team a weekly seller exception list, but suppress sellers with small samples. Ask for a root-cause explanation before making commercial decisions.",
        "3. Review the worst service cases alongside customer comments. Use those cases to define a small recovery test, such as proactive delay messaging or a targeted service credit, and measure whether ratings or repeat orders improve.",
        "4. Keep item sales, freight and cost of goods separate. Add real cost and refund data before describing any measure as profit, margin or recoverable revenue.",
        "",
        "## Data limits",
        "",
        "- The original public dataset covers historical transactions, not current marketplace performance.",
        "- It does not provide a complete cost-of-goods, returns, advertising, tax, discount or operating-expense ledger. Actual profit cannot be calculated from these tables alone.",
        "- Review data is self-selected. Buyers who leave a review may not represent all customers.",
        "- The relationships shown are descriptive. They should not be presented as proof of cause and effect.",
        "- Category reviews are order-level reviews carried onto item lines. This is a useful screening proxy, not a product-level rating measure.",
        "- Category and seller comparisons may be affected by sample size, price, product mix and customer location.",
        "",
        "## Files created by the run",
        "",
        "- `outputs/dashboard.html`: standalone interactive dashboard.",
        "- `outputs/service_recovery_planner.html`: interactive contact-coverage and cost planner.",
        "- `outputs/marketplace_analysis.db`: SQLite database for the SQL examples.",
        "- `outputs/metrics.json`: headline metrics for the run.",
        "- `outputs/tables/order_fact.csv`: one row per order with derived measures.",
        "- `outputs/tables/item_fact.csv`: item lines with category and order attributes.",
        "- `outputs/tables/category_performance.csv`: category comparison table.",
        "- `outputs/tables/seller_service_scorecard.csv`: seller screening scorecard.",
        "- `outputs/tables/customer_cohort_activity.csv`: repeat-order activity by cohort.",
        "- `outputs/tables/monthly_performance.csv`: monthly activity and value summary.",
        "- `outputs/tables/payment_method_summary.csv`: payment-method summary.",
        "- `outputs/tables/data_quality_checks.csv`: checks to review before interpreting metrics.",
        "- `visualizations/`: static charts used in this report.",
        "",
        "## Data source and credit",
        "",
        "Olist, & Sionek, A. (2018). Brazilian E-Commerce Public Dataset by Olist. Kaggle. https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce. The published dataset is licensed under CC BY-NC-SA 4.0; follow the source terms and attribution requirements when sharing adapted material.",
    ]
    (OUT / "analysis_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Analyze marketplace order, delivery, review and seller performance.")
    parser.add_argument("--source", choices=["auto", "demo", "raw"], default="auto", help="Use demo tables, downloaded Olist data, or raw if available and otherwise demo.")
    args = parser.parse_args()
    tables, display_name = load_tables(args.source)
    tables = standardize_tables(tables)
    tables["_mode"] = display_name
    analysis = build_analysis(tables)
    write_outputs(analysis, display_name)
    make_charts(analysis, display_name)
    print(f"Analysis complete using {display_name}.")
    print(f"Orders: {analysis['metrics']['order_count']:,}; delivered item value: R$ {analysis['metrics']['delivered_item_sales_brl']:,.0f}")
    print(f"Dashboard: {OUT / 'dashboard.html'}")
    print(f"Summary: {OUT / 'analysis_summary.md'}")

if __name__ == "__main__":
    main()
