"""Create a small, clearly synthetic dataset for a local demo run.

This is not Olist's original data. It mirrors the public dataset's table structure
so the full workflow can be tested before downloading the real files.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "demo"
OUT.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(20261025)

N_ORDERS = 1800
N_CUSTOMERS = 1480
N_PRODUCTS = 190
N_SELLERS = 68

categories = [
    ("bed_bath_table", "bed_bath_table", 85),
    ("health_beauty", "health_beauty", 115),
    ("computers_accessories", "computers_accessories", 245),
    ("furniture_decor", "furniture_decor", 135),
    ("watches_gifts", "watches_gifts", 210),
    ("sports_leisure", "sports_leisure", 110),
    ("housewares", "housewares", 95),
    ("auto", "auto", 155),
    ("toys", "toys", 80),
    ("cool_stuff", "cool_stuff", 175),
    ("telephony", "telephony", 120),
    ("fashion_bags_accessories", "fashion_bags_accessories", 90),
    ("garden_tools", "garden_tools", 100),
    ("office_furniture", "office_furniture", 65),
]
category_codes = [x[0] for x in categories]
category_weights = np.array([.13,.12,.12,.11,.09,.08,.08,.07,.06,.04,.04,.03,.02,.01], dtype=float)
category_weights /= category_weights.sum()
category_base_price = {k:v for k,_,v in categories}
category_en = {
    "bed_bath_table":"bed_bath_table", "health_beauty":"health_beauty",
    "computers_accessories":"computers_accessories", "furniture_decor":"furniture_decor",
    "watches_gifts":"watches_gifts", "sports_leisure":"sports_leisure",
    "housewares":"housewares", "auto":"auto", "toys":"toys",
    "cool_stuff":"cool_stuff", "telephony":"telephony",
    "fashion_bags_accessories":"fashion_bags_accessories", "garden_tools":"garden_tools",
    "office_furniture":"office_furniture"
}

states = ["SP","RJ","MG","RS","PR","SC","BA","DF","GO","ES","PE","CE","PA","MT","MS"]
state_p = np.array([.38,.12,.10,.07,.06,.05,.05,.04,.03,.025,.02,.015,.01,.01,.01], dtype=float)
state_p /= state_p.sum()
state_city = {
    "SP":["sao paulo","campinas","santos","ribeirao preto"], "RJ":["rio de janeiro","niteroi"],
    "MG":["belo horizonte","uberlandia"], "RS":["porto alegre","canoas"],
    "PR":["curitiba","londrina"], "SC":["florianopolis","joinville"],
    "BA":["salvador","feira de santana"], "DF":["brasilia"], "GO":["goiania"],
    "ES":["vitoria"], "PE":["recife"], "CE":["fortaleza"], "PA":["belem"],
    "MT":["cuiaba"], "MS":["campo grande"]
}

# Customer identity persists across orders; each order gets a separate customer_id.
customer_states = RNG.choice(states, size=N_CUSTOMERS, p=state_p)
customer_rows = []
customer_unique = [f"demo_customer_{i:05d}" for i in range(1, N_CUSTOMERS+1)]
for i, st in enumerate(customer_states, 1):
    customer_rows.append({
        "customer_id": f"demo_order_customer_{i:06d}",
        "customer_unique_id": customer_unique[i-1],
        "customer_zip_code_prefix": int(RNG.integers(1000, 99999)),
        "customer_city": RNG.choice(state_city[st]),
        "customer_state": st,
    })
customers_base = pd.DataFrame(customer_rows)

seller_rows = []
seller_effects = {}
for i in range(1, N_SELLERS+1):
    st = RNG.choice(states, p=state_p)
    seller_id = f"demo_seller_{i:04d}"
    # A few sellers have more delivery trouble, intentionally, so the demo can show how outliers are found.
    effect = float(RNG.normal(0, 2.0) + (3.8 if i in {7, 19, 41, 53} else 0))
    seller_effects[seller_id] = effect
    seller_rows.append({
        "seller_id": seller_id,
        "seller_zip_code_prefix": int(RNG.integers(1000, 99999)),
        "seller_city": RNG.choice(state_city[st]),
        "seller_state": st,
    })
sellers = pd.DataFrame(seller_rows)

product_rows = []
product_cats = []
for i in range(1, N_PRODUCTS+1):
    cat = RNG.choice(category_codes, p=category_weights)
    product_cats.append(cat)
    product_rows.append({
        "product_id": f"demo_product_{i:04d}",
        "product_category_name": cat,
        "product_name_lenght": int(RNG.integers(20, 70)),
        "product_description_lenght": int(RNG.integers(150, 1800)),
        "product_photos_qty": int(RNG.integers(1, 7)),
        "product_weight_g": int(RNG.integers(150, 9500)),
        "product_length_cm": int(RNG.integers(8, 90)),
        "product_height_cm": int(RNG.integers(3, 55)),
        "product_width_cm": int(RNG.integers(6, 70)),
    })
products = pd.DataFrame(product_rows)
product_cat_map = dict(zip(products.product_id, products.product_category_name))

# Repeat-customer weighting: some customers place 2-4 orders.
customer_prob = RNG.lognormal(mean=0.0, sigma=0.55, size=N_CUSTOMERS)
customer_prob /= customer_prob.sum()
selected_customer_idx = RNG.choice(np.arange(N_CUSTOMERS), size=N_ORDERS, p=customer_prob)
# Create a realistic-looking time window with a mild year-end peak.
start = pd.Timestamp("2016-10-01")
end = pd.Timestamp("2018-08-31")
days = pd.date_range(start, end, freq="D")
day_weights = np.ones(len(days), dtype=float)
for j, d in enumerate(days):
    if d.month in (11, 12): day_weights[j] *= 1.23
    if d.month == 1: day_weights[j] *= 0.84
    # gradual increase as the small marketplace grows
    day_weights[j] *= 0.7 + 0.6 * j / max(1, len(days)-1)
day_weights /= day_weights.sum()
purchase_dates = RNG.choice(days.to_numpy(), size=N_ORDERS, p=day_weights)
purchase_dates = pd.to_datetime(purchase_dates) + pd.to_timedelta(RNG.integers(8*60, 22*60, size=N_ORDERS), unit="m")

# Create unique order customer IDs, while allowing repeated unique identities.
orders = []
customer_table_rows = []
items = []
payments = []
reviews = []
order_statuses = []
customer_order_number = {}

for i in range(N_ORDERS):
    order_id = f"demo_order_{i+1:06d}"
    ci = int(selected_customer_idx[i])
    unique_id = customer_unique[ci]
    customer_id = f"demo_order_customer_{i+1:06d}"
    customer_order_number[unique_id] = customer_order_number.get(unique_id, 0) + 1
    st = customer_states[ci]
    purchase = pd.Timestamp(purchase_dates[i])
    approval = purchase + pd.Timedelta(hours=float(RNG.uniform(0.2, 20)))
    status_r = RNG.random()
    status = "delivered" if status_r < 0.955 else ("canceled" if status_r < 0.977 else "unavailable")

    # Estimate delivery promise and actual service experience.
    estimated_days = int(RNG.integers(9, 24)) + (3 if st in {"PA","MT","MS","CE"} else 0)
    estimated_date = purchase + pd.Timedelta(days=estimated_days)
    seller_count = int(RNG.choice([1,2,3,4], p=[.78,.16,.05,.01]))
    line_prices = []
    line_freights = []
    chosen_categories = []
    chosen_sellers = []
    for item_no in range(1, seller_count+1):
        product_idx = int(RNG.integers(0, len(products)))
        product = products.iloc[product_idx]
        cat = product["product_category_name"]
        base = category_base_price[cat]
        price = float(np.clip(RNG.lognormal(np.log(base), 0.58), 12, 2400))
        quantity = 1 if RNG.random() < .93 else 2
        price *= quantity
        seller_idx = int(RNG.integers(0, len(sellers)))
        seller = sellers.iloc[seller_idx]
        freight = float(np.clip(RNG.normal(18 + price*0.045 + (5 if st != seller["seller_state"] else 0), 7), 5, 95))
        line_prices.append(price)
        line_freights.append(freight)
        chosen_categories.append(cat)
        chosen_sellers.append(seller["seller_id"])
        items.append({
            "order_id": order_id, "order_item_id": item_no,
            "product_id": product["product_id"], "seller_id": seller["seller_id"],
            "shipping_limit_date": (purchase + pd.Timedelta(days=int(RNG.integers(1, 5)))).strftime("%Y-%m-%d %H:%M:%S"),
            "price": round(price, 2), "freight_value": round(freight, 2),
        })

    customer_table_rows.append({
        "customer_id": customer_id, "customer_unique_id": unique_id,
        "customer_zip_code_prefix": int(RNG.integers(1000, 99999)),
        "customer_city": RNG.choice(state_city[st]), "customer_state": st,
    })

    if status == "delivered":
        base_actual = int(np.clip(RNG.normal(12.2 + (2.8 if st in {"PA","MT","MS","CE"} else 0), 4.2), 3, 30))
        seller_effect = np.mean([seller_effects[s] for s in chosen_sellers])
        category_penalty = 1.2 if any(c in {"furniture_decor","bed_bath_table","office_furniture"} for c in chosen_categories) else 0
        actual_days = int(np.clip(base_actual + seller_effect + category_penalty + RNG.normal(0, 2.2), 2, 38))
        delivered_carrier = purchase + pd.Timedelta(days=max(1, int(actual_days*0.22)))
        delivered_customer = purchase + pd.Timedelta(days=actual_days)
        delay_days = max(0, actual_days - estimated_days)
        score_latent = 4.45 - delay_days * 0.28 - max(0, delay_days - 2) * 0.07
        score_latent += -0.35 if any(c in {"office_furniture","furniture_decor","bed_bath_table"} for c in chosen_categories) else 0
        score_latent += RNG.normal(0, 0.82)
        score = int(np.clip(np.rint(score_latent), 1, 5))
    else:
        delivered_carrier = pd.NaT
        delivered_customer = pd.NaT
        actual_days = None
        score = None

    orders.append({
        "order_id": order_id, "customer_id": customer_id, "order_status": status,
        "order_purchase_timestamp": purchase.strftime("%Y-%m-%d %H:%M:%S"),
        "order_approved_at": approval.strftime("%Y-%m-%d %H:%M:%S"),
        "order_delivered_carrier_date": "" if pd.isna(delivered_carrier) else delivered_carrier.strftime("%Y-%m-%d %H:%M:%S"),
        "order_delivered_customer_date": "" if pd.isna(delivered_customer) else delivered_customer.strftime("%Y-%m-%d %H:%M:%S"),
        "order_estimated_delivery_date": estimated_date.strftime("%Y-%m-%d %H:%M:%S"),
    })
    order_statuses.append(status)

    # Payments roughly reconcile to item + freight value.
    order_value = sum(line_prices) + sum(line_freights)
    payment_type = RNG.choice(["credit_card","boleto","voucher","debit_card"], p=[.69,.21,.06,.04])
    installments = int(RNG.choice([1,2,3,4,5,6,8,10], p=[.44,.14,.11,.08,.06,.06,.05,.06])) if payment_type == "credit_card" else 1
    payments.append({
        "order_id": order_id, "payment_sequential": 1,
        "payment_type": payment_type, "payment_installments": installments,
        "payment_value": round(max(0, order_value + RNG.normal(0, 0.45)), 2),
    })

    # Most delivered orders receive a review; ratings are related to delivery performance.
    if status == "delivered" and RNG.random() < 0.84:
        delay = actual_days - estimated_days
        if score <= 2:
            msg = "Delivery took longer than expected" if delay > 0 else "The order did not meet expectations"
            title = "Could be better"
        elif score == 3:
            msg, title = "The order was acceptable", "Average experience"
        else:
            msg, title = "Order arrived and matched the request", "Satisfied"
        creation = delivered_customer + pd.Timedelta(days=int(RNG.integers(1, 8)))
        reviews.append({
            "review_id": f"demo_review_{len(reviews)+1:06d}", "order_id": order_id,
            "review_score": score, "review_comment_title": title,
            "review_comment_message": msg,
            "review_creation_date": creation.strftime("%Y-%m-%d %H:%M:%S"),
            "review_answer_timestamp": (creation + pd.Timedelta(days=int(RNG.integers(0, 3)))).strftime("%Y-%m-%d %H:%M:%S"),
        })

orders_df = pd.DataFrame(orders)
items_df = pd.DataFrame(items)
payments_df = pd.DataFrame(payments)
reviews_df = pd.DataFrame(reviews)
# The public dataset has one customer record per order, including a stable unique key.
customers_df = pd.DataFrame(customer_table_rows)
# Avoid any customer IDs outside the order population and preserve the original-style relationship.

# Use more descriptive, explicitly synthetic demo filenames.
orders_df.to_csv(OUT / "demo_orders.csv", index=False)
items_df.to_csv(OUT / "demo_order_items.csv", index=False)
payments_df.to_csv(OUT / "demo_order_payments.csv", index=False)
reviews_df.to_csv(OUT / "demo_order_reviews.csv", index=False)
customers_df.to_csv(OUT / "demo_customers.csv", index=False)
products.to_csv(OUT / "demo_products.csv", index=False)
sellers.to_csv(OUT / "demo_sellers.csv", index=False)
pd.DataFrame({"product_category_name":list(category_en.keys()), "product_category_name_english":list(category_en.values())}).to_csv(OUT / "demo_category_translation.csv", index=False)

print(f"Created demo tables in {OUT}")
print(f"Orders: {len(orders_df):,}; delivered: {(orders_df.order_status == 'delivered').sum():,}; items: {len(items_df):,}; reviews: {len(reviews_df):,}")
