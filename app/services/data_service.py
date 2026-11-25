from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from ..extensions import db
from ..models import Inventory, Product, SalesRecord


REQUIRED_CSV_COLUMNS = {"date", "store_id", "product_id", "sales_units"}


def _bool_value(value) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def seed_demo_data(sales_file: Path, inventory_file: Path) -> bool:
    """Seed a fresh database with the bundled, clearly-labelled demo dataset."""
    if SalesRecord.query.first() is not None:
        return False

    if not sales_file.exists():
        raise FileNotFoundError(f"Demo sales file not found: {sales_file}")

    sales = pd.read_csv(sales_file)
    inventory = pd.read_csv(inventory_file) if inventory_file.exists() else pd.DataFrame()

    product_columns = [c for c in ["product_id", "product_name", "category", "unit_price"] if c in sales.columns]
    products = sales[product_columns].drop_duplicates("product_id")
    for row in products.to_dict("records"):
        db.session.add(Product(
            product_id=str(row["product_id"]),
            product_name=str(row.get("product_name", row["product_id"])),
            category=str(row.get("category", "Uncategorised")),
            default_price=float(row.get("unit_price", 0) or 0),
        ))

    db.session.flush()

    records = []
    for row in sales.to_dict("records"):
        records.append({
            "sale_date": pd.to_datetime(row["date"]).date(),
            "store_id": str(row["store_id"]),
            "product_id": str(row["product_id"]),
            "unit_price": float(row.get("unit_price", 0) or 0),
            "promotion": _bool_value(row.get("promotion", False)),
            "holiday": _bool_value(row.get("holiday", False)),
            "sales_units": int(max(0, float(row["sales_units"]))),
        })
    db.session.bulk_insert_mappings(SalesRecord, records)

    if not inventory.empty:
        for row in inventory.to_dict("records"):
            db.session.add(Inventory(
                product_id=str(row["product_id"]),
                store_id=str(row["store_id"]),
                current_stock=int(row.get("current_stock", 0)),
                lead_time_days=int(row.get("lead_time_days", 3)),
                safety_stock_days=int(row.get("safety_stock_days", 3)),
            ))

    db.session.commit()
    return True


def records_to_frame(records=None) -> pd.DataFrame:
    records = records if records is not None else SalesRecord.query.order_by(SalesRecord.sale_date).all()
    if not records:
        return pd.DataFrame()
    rows = [{
        "date": record.sale_date,
        "store_id": record.store_id,
        "product_id": record.product_id,
        "unit_price": record.unit_price,
        "promotion": int(record.promotion),
        "holiday": int(record.holiday),
        "sales_units": record.sales_units,
    } for record in records]
    frame = pd.DataFrame(rows)
    product_meta = {p.product_id: {"product_name": p.product_name, "category": p.category}
                    for p in Product.query.all()}
    frame["product_name"] = frame["product_id"].map(lambda key: product_meta.get(key, {}).get("product_name", key))
    frame["category"] = frame["product_id"].map(lambda key: product_meta.get(key, {}).get("category", "Uncategorised"))
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.sort_values(["product_id", "store_id", "date"]).reset_index(drop=True)


def import_sales_csv(file_stream) -> dict:
    """Validate and upsert a user-provided sales CSV."""
    frame = pd.read_csv(file_stream)
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    missing = sorted(REQUIRED_CSV_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    if frame.empty:
        raise ValueError("The uploaded CSV contains no data rows.")
    if len(frame) > 10000:
        raise ValueError("Please upload at most 10,000 rows at a time.")

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["sales_units"] = pd.to_numeric(frame["sales_units"], errors="coerce")
    if frame["date"].isna().any() or frame["sales_units"].isna().any():
        raise ValueError("Some dates or sales_units values are invalid.")
    if (frame["sales_units"] < 0).any():
        raise ValueError("sales_units cannot contain negative values.")

    if frame["store_id"].isna().any() or frame["product_id"].isna().any():
        raise ValueError("store_id and product_id cannot be blank.")
    frame["store_id"] = frame["store_id"].astype(str).str.strip()
    frame["product_id"] = frame["product_id"].astype(str).str.strip()
    if (frame["store_id"] == "").any() or (frame["product_id"] == "").any():
        raise ValueError("store_id and product_id cannot be blank.")

    defaults = {"unit_price": 0.0, "promotion": 0, "holiday": 0,
                "product_name": None, "category": "Uncategorised"}
    for column, default in defaults.items():
        if column not in frame.columns:
            frame[column] = default
    frame["unit_price"] = pd.to_numeric(frame["unit_price"], errors="coerce").fillna(0).clip(lower=0)
    frame["sales_units"] = frame["sales_units"].round().astype(int)
    frame["promotion"] = frame["promotion"].map(_bool_value)
    frame["holiday"] = frame["holiday"].map(_bool_value)
    frame = frame.drop_duplicates(["date", "store_id", "product_id"], keep="last")

    for product_id, group in frame.groupby("product_id"):
        first = group.iloc[0]
        product = db.session.get(Product, product_id)
        if product is None:
            raw_name = first.get("product_name")
            raw_category = first.get("category")
            product_name = product_id if pd.isna(raw_name) or not str(raw_name).strip() else str(raw_name)
            category = "Uncategorised" if pd.isna(raw_category) or not str(raw_category).strip() else str(raw_category)
            product = Product(
                product_id=product_id,
                product_name=product_name,
                category=category,
                default_price=float(first["unit_price"]),
            )
            db.session.add(product)
        else:
            if first.get("product_name") and str(first.get("product_name")) != "nan":
                product.product_name = str(first.get("product_name"))
            if first.get("category") and str(first.get("category")) != "nan":
                product.category = str(first.get("category"))
            if float(first["unit_price"]) > 0:
                product.default_price = float(first["unit_price"])

    db.session.flush()
    inserted_or_updated = 0
    min_date = frame["date"].min().date()
    max_date = frame["date"].max().date()
    existing_sales = SalesRecord.query.filter(
        SalesRecord.sale_date >= min_date, SalesRecord.sale_date <= max_date
    ).all()
    sales_lookup = {(row.sale_date, row.store_id, row.product_id): row for row in existing_sales}
    inventory_lookup = {(row.product_id, row.store_id): row for row in Inventory.query.all()}

    for row in frame.to_dict("records"):
        sale_date = row["date"].date()
        key = (sale_date, row["store_id"], row["product_id"])
        values = {
            "unit_price": float(row["unit_price"]),
            "promotion": bool(row["promotion"]),
            "holiday": bool(row["holiday"]),
            "sales_units": int(row["sales_units"]),
        }
        record = sales_lookup.get(key)
        if record is None:
            record = SalesRecord(
                sale_date=sale_date, store_id=row["store_id"],
                product_id=row["product_id"], **values,
            )
            db.session.add(record)
            sales_lookup[key] = record
        else:
            for column, value in values.items():
                setattr(record, column, value)
        inserted_or_updated += 1

        inventory_key = (row["product_id"], row["store_id"])
        if inventory_key not in inventory_lookup:
            inventory_row = Inventory(
                product_id=row["product_id"], store_id=row["store_id"],
                current_stock=0, lead_time_days=3, safety_stock_days=3,
            )
            db.session.add(inventory_row)
            inventory_lookup[inventory_key] = inventory_row

    db.session.commit()
    return {"rows_processed": inserted_or_updated, "products_seen": int(frame["product_id"].nunique()),
            "stores_seen": int(frame["store_id"].nunique())}
