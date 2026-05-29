"""
etl_and_eda.py
──────────────
ETL  → loads raw CSV, cleans and transforms it, exports a processed CSV
EDA  → generates 6 insight plots saved to ../data/charts/
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
import seaborn as sns
import os
import warnings

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(BASE_DIR, "..", "data")
RAW_PATH    = os.path.join(DATA_DIR, "sales_data.csv")
CLEAN_PATH  = os.path.join(DATA_DIR, "sales_data_clean.csv")
CHARTS_DIR  = os.path.join(DATA_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# ── Style ─────────────────────────────────────────────────────────────────────
sns.set_theme(style="whitegrid", palette="muted")
PALETTE   = sns.color_palette("muted", 8)
FIG_SIZE  = (12, 5)
TITLE_FS  = 14

# =============================================================================
# 1. ETL
# =============================================================================
print("=" * 60)
print("ETL PIPELINE")
print("=" * 60)

# Load
df = pd.read_csv(RAW_PATH, parse_dates=["order_date", "ship_date"])
print(f"  Loaded          : {len(df):,} rows, {df.shape[1]} columns")

# ── Transform ─────────────────────────────────────────────────────────────────
# Remove duplicates
before = len(df)
df.drop_duplicates(subset="order_id", inplace=True)
print(f"  Duplicates drop : {before - len(df)} rows removed")

# Fill / validate nulls
df.dropna(subset=["order_id", "sales", "profit"], inplace=True)
print(f"  Null drop       : {len(df):,} rows remain")

# Derived date columns
df["order_year"]    = df["order_date"].dt.year
df["order_month"]   = df["order_date"].dt.month
df["order_quarter"] = df["order_date"].dt.quarter
df["order_month_name"] = df["order_date"].dt.strftime("%b")
df["ship_days"]     = (df["ship_date"] - df["order_date"]).dt.days.clip(lower=0)

# Discount band
bins   = [-0.001, 0.001, 0.10, 0.20, 1.0]
labels = ["No Discount", "Low (1-10%)", "Medium (11-20%)", "High (>20%)"]
df["discount_band"] = pd.cut(df["discount"], bins=bins, labels=labels)

# Revenue tier per order
df["revenue_tier"] = pd.qcut(df["sales"], q=4,
                              labels=["Low", "Mid-Low", "Mid-High", "High"])

# Export cleaned CSV
df.to_csv(CLEAN_PATH, index=False)
print(f"\n✅ Clean data saved → {CLEAN_PATH}")
print(f"   Columns: {list(df.columns)}\n")


# =============================================================================
# 2. EDA
# =============================================================================
print("=" * 60)
print("EDA — EXPLORATORY DATA ANALYSIS")
print("=" * 60)

def save(fig, name):
    path = os.path.join(CHARTS_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Chart saved → {path}")


# ── Chart 1: Monthly Revenue & Profit Trend ───────────────────────────────────
monthly = (
    df.groupby(df["order_date"].dt.to_period("M"))
      .agg(revenue=("sales", "sum"), profit=("profit", "sum"))
      .reset_index()
)
monthly["order_date"] = monthly["order_date"].dt.to_timestamp()

fig, ax = plt.subplots(figsize=FIG_SIZE)
ax.plot(monthly["order_date"], monthly["revenue"], marker="o", label="Revenue",
        color=PALETTE[0], linewidth=2)
ax.plot(monthly["order_date"], monthly["profit"],  marker="s", label="Profit",
        color=PALETTE[2], linewidth=2, linestyle="--")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
plt.xticks(rotation=45)
ax.set_title("Monthly Revenue & Profit Trend", fontsize=TITLE_FS, fontweight="bold")
ax.set_xlabel("Month"); ax.set_ylabel("Amount (USD)")
ax.legend()
fig.tight_layout()
save(fig, "01_monthly_trend.png")


# ── Chart 2: Revenue by Region (Bar) ─────────────────────────────────────────
region = (
    df.groupby("region")
      .agg(revenue=("sales", "sum"), profit=("profit", "sum"))
      .sort_values("revenue", ascending=False)
      .reset_index()
)

fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(region["region"], region["revenue"], color=PALETTE[:len(region)],
              edgecolor="white", linewidth=0.8)
for bar in bars:
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5000,
            f"${bar.get_height():,.0f}", ha="center", va="bottom", fontsize=9)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax.set_title("Total Revenue by Region", fontsize=TITLE_FS, fontweight="bold")
ax.set_xlabel("Region"); ax.set_ylabel("Revenue (USD)")
fig.tight_layout()
save(fig, "02_revenue_by_region.png")


# ── Chart 3: Category Profit Margin (Horizontal Bar) ─────────────────────────
cat = (
    df.groupby(["category", "sub_category"])
      .agg(revenue=("sales", "sum"), margin=("profit_pct", "mean"))
      .reset_index()
      .sort_values("margin", ascending=True)
)

fig, ax = plt.subplots(figsize=(10, 6))
colors = [PALETTE[0] if m >= cat["margin"].mean() else PALETTE[5]
          for m in cat["margin"]]
ax.barh(cat["sub_category"], cat["margin"], color=colors, edgecolor="white")
ax.axvline(cat["margin"].mean(), color="red", linestyle="--", linewidth=1.2,
           label=f"Avg {cat['margin'].mean():.1f}%")
ax.set_title("Avg Profit Margin % by Sub-Category", fontsize=TITLE_FS, fontweight="bold")
ax.set_xlabel("Profit Margin (%)"); ax.legend()
fig.tight_layout()
save(fig, "03_profit_margin_subcategory.png")


# ── Chart 4: Discount Band vs Avg Profit Margin ───────────────────────────────
disc = (
    df.groupby("discount_band", observed=True)
      .agg(avg_margin=("profit_pct", "mean"), orders=("order_id", "count"))
      .reset_index()
)

fig, ax1 = plt.subplots(figsize=(9, 5))
ax2 = ax1.twinx()
ax1.bar(disc["discount_band"], disc["avg_margin"], color=PALETTE[1],
        alpha=0.8, label="Avg Margin %")
ax2.plot(disc["discount_band"], disc["orders"], marker="D", color=PALETTE[3],
         linewidth=2, label="Order Count")
ax1.set_ylabel("Avg Profit Margin (%)"); ax2.set_ylabel("Order Count")
ax1.set_title("Discount Band vs Avg Profit Margin", fontsize=TITLE_FS, fontweight="bold")
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")
fig.tight_layout()
save(fig, "04_discount_vs_margin.png")


# ── Chart 5: Top 10 Sales Reps by Revenue ────────────────────────────────────
reps = (
    df.groupby("sales_rep")
      .agg(revenue=("sales", "sum"), profit=("profit", "sum"))
      .nlargest(10, "revenue")
      .reset_index()
)

fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(reps))
w = 0.4
ax.bar(x - w/2, reps["revenue"], width=w, label="Revenue", color=PALETTE[0])
ax.bar(x + w/2, reps["profit"],  width=w, label="Profit",  color=PALETTE[2])
ax.set_xticks(x); ax.set_xticklabels(reps["sales_rep"], rotation=30, ha="right")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax.set_title("Top 10 Sales Reps — Revenue vs Profit", fontsize=TITLE_FS, fontweight="bold")
ax.legend()
fig.tight_layout()
save(fig, "05_top_reps.png")


# ── Chart 6: Quarterly Revenue Heatmap (Region × Quarter) ────────────────────
pivot = df.pivot_table(
    values="sales", index="region",
    columns="order_quarter", aggfunc="sum"
).rename(columns={1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"})

fig, ax = plt.subplots(figsize=(9, 5))
sns.heatmap(pivot, annot=True, fmt=",.0f", cmap="YlGnBu",
            linewidths=0.5, ax=ax,
            annot_kws={"size": 9})
ax.set_title("Revenue Heatmap — Region × Quarter", fontsize=TITLE_FS, fontweight="bold")
ax.set_xlabel("Quarter"); ax.set_ylabel("Region")
fig.tight_layout()
save(fig, "06_region_quarter_heatmap.png")


# ── Summary Stats ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("KEY METRICS SUMMARY")
print("=" * 60)
print(f"  Total Orders    : {len(df):,}")
print(f"  Total Revenue   : ${df['sales'].sum():,.2f}")
print(f"  Total Profit    : ${df['profit'].sum():,.2f}")
print(f"  Avg Margin      : {df['profit_pct'].mean():.2f}%")
print(f"  Avg Discount    : {df['discount'].mean()*100:.1f}%")
print(f"  Avg Ship Days   : {df['ship_days'].mean():.1f}")
print("=" * 60)
print("\n✅ EDA complete — all charts saved to", CHARTS_DIR)
