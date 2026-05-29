"""
generate_data.py
Generates a realistic dummy sales dataset and saves it to ../data/sales_data.csv
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

np.random.seed(42)
random.seed(42)

# ── Config ────────────────────────────────────────────────────────────────────
NUM_RECORDS = 2000
START_DATE  = datetime(2023, 1, 1)
END_DATE    = datetime(2024, 12, 31)

REGIONS     = ["North", "South", "East", "West", "Central"]
CATEGORIES  = ["Electronics", "Furniture", "Office Supplies", "Clothing", "Sports"]
SUB_CATS    = {
    "Electronics":      ["Laptops", "Phones", "Tablets", "Accessories"],
    "Furniture":        ["Chairs", "Desks", "Cabinets", "Tables"],
    "Office Supplies":  ["Pens", "Paper", "Staplers", "Binders"],
    "Clothing":         ["Shirts", "Pants", "Shoes", "Jackets"],
    "Sports":           ["Gym Equipment", "Outdoor Gear", "Sportswear", "Footwear"],
}
SALES_REPS  = [f"Rep_{i:02d}" for i in range(1, 21)]
CUSTOMERS   = [f"CUST_{i:04d}" for i in range(1, 301)]
SHIP_MODES  = ["Standard", "Express", "Same Day", "Economy"]

CATEGORY_BASE_PRICE = {
    "Electronics": (200, 2000),
    "Furniture":   (100, 800),
    "Office Supplies": (5, 80),
    "Clothing":    (20, 250),
    "Sports":      (30, 500),
}

# ── Generate rows ─────────────────────────────────────────────────────────────
def random_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))

rows = []
for i in range(1, NUM_RECORDS + 1):
    category   = random.choice(CATEGORIES)
    sub_cat    = random.choice(SUB_CATS[category])
    region     = random.choice(REGIONS)
    rep        = random.choice(SALES_REPS)
    customer   = random.choice(CUSTOMERS)
    ship_mode  = random.choice(SHIP_MODES)
    order_date = random_date(START_DATE, END_DATE)
    ship_date  = order_date + timedelta(days=random.randint(1, 7))

    lo, hi     = CATEGORY_BASE_PRICE[category]
    unit_price = round(random.uniform(lo, hi), 2)
    quantity   = random.randint(1, 10)
    discount   = round(random.choice([0, 0, 0, 0.05, 0.10, 0.15, 0.20]), 2)
    sales      = round(unit_price * quantity * (1 - discount), 2)
    cost       = round(sales * random.uniform(0.45, 0.75), 2)
    profit     = round(sales - cost, 2)
    profit_pct = round((profit / sales) * 100, 2) if sales > 0 else 0

    rows.append({
        "order_id":      f"ORD-{i:05d}",
        "order_date":    order_date.strftime("%Y-%m-%d"),
        "ship_date":     ship_date.strftime("%Y-%m-%d"),
        "ship_mode":     ship_mode,
        "customer_id":   customer,
        "region":        region,
        "sales_rep":     rep,
        "category":      category,
        "sub_category":  sub_cat,
        "unit_price":    unit_price,
        "quantity":      quantity,
        "discount":      discount,
        "sales":         sales,
        "cost":          cost,
        "profit":        profit,
        "profit_pct":    profit_pct,
    })

df = pd.DataFrame(rows)

out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "sales_data.csv")
df.to_csv(out_path, index=False)

print(f"✅ Dataset generated: {len(df):,} rows → {out_path}")
print(df.head())
