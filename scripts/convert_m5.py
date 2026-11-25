"""Convert a subset of the Kaggle M5 Forecasting files to ShelfSignal CSV format.

Example:
python scripts/convert_m5.py --sales sales_train_validation.csv \
  --calendar calendar.csv --prices sell_prices.csv --store CA_1 \
  --products 100 --output data/m5_sales.csv

Download the source files from the M5 Forecasting Accuracy competition on Kaggle.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def convert(sales_path: Path, calendar_path: Path, prices_path: Path,
            output_path: Path, store: str | None, product_limit: int) -> int:
    sales = pd.read_csv(sales_path)
    calendar = pd.read_csv(calendar_path, usecols=[
        "d", "date", "wm_yr_wk", "event_name_1", "event_name_2"
    ])
    prices = pd.read_csv(prices_path)

    if store:
        sales = sales[sales["store_id"] == store].copy()
        prices = prices[prices["store_id"] == store].copy()
    if product_limit > 0:
        item_ids = sorted(sales["item_id"].unique())[:product_limit]
        sales = sales[sales["item_id"].isin(item_ids)].copy()
        prices = prices[prices["item_id"].isin(item_ids)].copy()
    if sales.empty:
        raise ValueError("No sales rows found. Check the selected store and input files.")

    day_columns = [column for column in sales.columns if column.startswith("d_")]
    id_columns = [column for column in ["item_id", "cat_id", "store_id"] if column in sales.columns]
    long_sales = sales[id_columns + day_columns].melt(
        id_vars=id_columns, var_name="d", value_name="sales_units"
    )
    long_sales = long_sales.merge(calendar, on="d", how="left", validate="many_to_one")
    long_sales = long_sales.merge(
        prices[["store_id", "item_id", "wm_yr_wk", "sell_price"]],
        on=["store_id", "item_id", "wm_yr_wk"], how="left", validate="many_to_one"
    )

    event_flag = long_sales["event_name_1"].notna() | long_sales["event_name_2"].notna()
    result = pd.DataFrame({
        "date": pd.to_datetime(long_sales["date"]).dt.strftime("%Y-%m-%d"),
        "store_id": long_sales["store_id"],
        "product_id": long_sales["item_id"],
        "sales_units": pd.to_numeric(long_sales["sales_units"], errors="coerce").fillna(0).astype(int),
        "unit_price": pd.to_numeric(long_sales["sell_price"], errors="coerce").fillna(0),
        # M5 does not provide a direct retailer promotion field. Do not mislabel SNAP as promotion.
        "promotion": 0,
        "holiday": event_flag.astype(int),
        "product_name": long_sales["item_id"],
        "category": long_sales["cat_id"],
    })
    result = result.dropna(subset=["date", "store_id", "product_id"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    return len(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Kaggle M5 files for ShelfSignal.")
    parser.add_argument("--sales", type=Path, required=True, help="sales_train_validation.csv")
    parser.add_argument("--calendar", type=Path, required=True, help="calendar.csv")
    parser.add_argument("--prices", type=Path, required=True, help="sell_prices.csv")
    parser.add_argument("--output", type=Path, default=Path("data/m5_sales.csv"))
    parser.add_argument("--store", default=None, help="Optional store filter, e.g. CA_1")
    parser.add_argument("--products", type=int, default=100, help="Number of products to include; 0 means all")
    args = parser.parse_args()
    rows = convert(args.sales, args.calendar, args.prices, args.output, args.store, args.products)
    print(f"Wrote {rows:,} rows to {args.output}")
    print("Review data quality, then upload the CSV from the ShelfSignal Data & Model page.")


if __name__ == "__main__":
    main()
