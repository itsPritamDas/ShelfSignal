from datetime import timedelta
import io

import pandas as pd
from flask import Blueprint, current_app, jsonify, request

from ..extensions import db
from ..models import Inventory, Product, SalesRecord
from ..services.data_service import import_sales_csv, records_to_frame
from ..services.forecasting import (
    MODEL_CACHE, forecast_series, get_inventory_plan, train_or_load_model,
)
import app.services.forecasting as forecasting_module

api = Blueprint("api", __name__, url_prefix="/api")


def _error(message: str, status: int = 400):
    return jsonify({"error": str(message)}), status


@api.get("/health")
def health():
    return jsonify({"status": "ok", "service": "ShelfSignal API"})


@api.get("/overview")
def overview():
    frame = records_to_frame()
    if frame.empty:
        return _error("No sales data is available.", 404)
    latest_date = pd.to_datetime(frame["date"]).max()
    recent = frame[frame["date"] >= latest_date - pd.Timedelta(days=29)]
    previous = frame[(frame["date"] < latest_date - pd.Timedelta(days=29)) &
                     (frame["date"] >= latest_date - pd.Timedelta(days=59))]
    total_units = int(recent["sales_units"].sum())
    prev_units = int(previous["sales_units"].sum())
    change = ((total_units - prev_units) / prev_units * 100) if prev_units else 0.0
    daily = recent.groupby("date", as_index=False)["sales_units"].sum().sort_values("date")
    category = recent.groupby("category", as_index=False)["sales_units"].sum().sort_values("sales_units", ascending=False)
    top = recent.groupby(["product_id", "product_name"], as_index=False)["sales_units"].sum().sort_values("sales_units", ascending=False).head(6)
    bundle = train_or_load_model()
    inventory = get_inventory_plan()
    return jsonify({
        "kpis": {
            "units_30d": total_units,
            "sales_change_pct": round(float(change), 1),
            "active_products": int(frame["product_id"].nunique()),
            "stores": int(frame["store_id"].nunique()),
            "records": int(len(frame)),
            "at_risk_items": sum(1 for row in inventory if row["status"] == "At risk"),
        },
        "daily_sales": [{"date": pd.to_datetime(row.date).date().isoformat(), "units": int(row.sales_units)}
                        for row in daily.itertuples()],
        "category_mix": [{"category": str(row.category), "units": int(row.sales_units)}
                         for row in category.itertuples()],
        "top_products": [{"product_id": str(row.product_id), "product_name": str(row.product_name),
                          "units": int(row.sales_units)} for row in top.itertuples()],
        "model": {"name": bundle["model_name"], "trained_at": bundle["trained_at"],
                  "metrics": bundle["metrics"], "feature_importance": bundle["feature_importance"],
                  "training_rows": bundle["training_rows"], "validation_wape": bundle["validation_wape"],
                  "backtest_note": bundle["backtest_note"]},
        "last_data_date": latest_date.date().isoformat(),
    })


@api.get("/products")
def products():
    items = Product.query.order_by(Product.product_name).all()
    stores = [row[0] for row in db.session.query(SalesRecord.store_id).distinct().order_by(SalesRecord.store_id).all()]
    latest_prices = {}
    for row in db.session.query(SalesRecord.product_id, SalesRecord.store_id, SalesRecord.unit_price).order_by(SalesRecord.sale_date.desc()).all():
        latest_prices.setdefault((row[0], row[1]), float(row[2]))
    return jsonify({
        "products": [{"product_id": item.product_id, "product_name": item.product_name,
                      "category": item.category, "default_price": item.default_price}
                     for item in items],
        "stores": stores,
        "latest_prices": [{"product_id": key[0], "store_id": key[1], "unit_price": value}
                          for key, value in latest_prices.items()],
    })


@api.get("/forecast")
def forecast():
    product_id = request.args.get("product_id", "").strip()
    store_id = request.args.get("store_id", "").strip()
    try:
        horizon = int(request.args.get("horizon", 7))
        if not product_id or not store_id:
            return _error("Choose a product and store.")
        return jsonify(forecast_series(product_id, store_id, horizon))
    except ValueError as exc:
        return _error(str(exc))
    except Exception as exc:
        current_app.logger.exception("Forecast request failed")
        return _error(f"Forecast could not be generated: {exc}", 500)


@api.get("/inventory")
def inventory():
    try:
        return jsonify({"items": get_inventory_plan()})
    except Exception as exc:
        current_app.logger.exception("Inventory plan failed")
        return _error(f"Inventory analysis failed: {exc}", 500)


@api.patch("/inventory/<int:item_id>")
def update_inventory(item_id: int):
    item = db.session.get(Inventory, item_id)
    if item is None:
        return _error("Inventory record not found.", 404)
    payload = request.get_json(silent=True) or {}
    try:
        if "current_stock" in payload:
            value = int(payload["current_stock"])
            if value < 0:
                return _error("Current stock cannot be negative.")
            item.current_stock = value
        if "lead_time_days" in payload:
            value = int(payload["lead_time_days"])
            if not 1 <= value <= 90:
                return _error("Lead time must be between 1 and 90 days.")
            item.lead_time_days = value
        if "safety_stock_days" in payload:
            value = int(payload["safety_stock_days"])
            if not 0 <= value <= 90:
                return _error("Safety stock days must be between 0 and 90.")
            item.safety_stock_days = value
        db.session.commit()
        return jsonify({"message": "Inventory settings updated."})
    except (TypeError, ValueError):
        db.session.rollback()
        return _error("Please provide valid whole-number inventory values.")


@api.post("/upload")
def upload():
    if "file" not in request.files:
        return _error("Choose a CSV file to upload.")
    file = request.files["file"]
    if not file.filename or not file.filename.lower().endswith(".csv"):
        return _error("Only .csv files are supported.")
    try:
        result = import_sales_csv(file.stream)
        forecasting_module.MODEL_CACHE = None
        return jsonify({"message": "Sales data imported successfully. Retrain the model to refresh forecasts.", **result})
    except Exception as exc:
        db.session.rollback()
        return _error(str(exc))


@api.post("/retrain")
def retrain():
    try:
        forecasting_module.MODEL_CACHE = None
        bundle = train_or_load_model(force=True)
        return jsonify({"message": "Model training completed.", "name": bundle["model_name"],
                        "metrics": bundle["metrics"], "training_rows": bundle["training_rows"],
                        "trained_at": bundle["trained_at"]})
    except Exception as exc:
        current_app.logger.exception("Model retraining failed")
        return _error(f"Model training failed: {exc}", 500)
