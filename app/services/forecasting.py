from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import math

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.inspection import permutation_importance
from sklearn.ensemble import HistGradientBoostingRegressor

from ..models import Inventory, Product
from .data_service import records_to_frame


FEATURES = [
    "lag_1", "lag_7", "lag_14", "lag_28",
    "rolling_mean_7", "rolling_mean_28",
    "day_of_week", "month", "day_of_year", "is_weekend",
    "unit_price", "promotion", "holiday", "product_code", "store_code",
]
MODEL_CACHE = None


def engineer_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Create leakage-aware lag/rolling features for each product-store series."""
    if frame.empty:
        return frame.copy()
    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values(["product_id", "store_id", "date"]).reset_index(drop=True)
    grouped = data.groupby(["product_id", "store_id"], sort=False)["sales_units"]
    for lag in [1, 7, 14, 28]:
        data[f"lag_{lag}"] = grouped.shift(lag)
    data["rolling_mean_7"] = grouped.transform(lambda values: values.shift(1).rolling(7).mean())
    data["rolling_mean_28"] = grouped.transform(lambda values: values.shift(1).rolling(28).mean())
    data["day_of_week"] = data["date"].dt.dayofweek
    data["month"] = data["date"].dt.month
    data["day_of_year"] = data["date"].dt.dayofyear
    data["is_weekend"] = (data["day_of_week"] >= 5).astype(int)
    product_codes = {value: index for index, value in enumerate(sorted(data["product_id"].astype(str).unique()))}
    store_codes = {value: index for index, value in enumerate(sorted(data["store_id"].astype(str).unique()))}
    data["product_code"] = data["product_id"].astype(str).map(product_codes)
    data["store_code"] = data["store_id"].astype(str).map(store_codes)
    data["promotion"] = data["promotion"].fillna(0).astype(int)
    data["holiday"] = data["holiday"].fillna(0).astype(int)
    data["unit_price"] = data["unit_price"].fillna(0).astype(float)
    return data.dropna(subset=FEATURES + ["sales_units"]).reset_index(drop=True)


def _safe_metrics(actual, predicted) -> dict:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mae = float(mean_absolute_error(actual, predicted))
    rmse = float(np.sqrt(mean_squared_error(actual, predicted)))
    denominator = float(np.abs(actual).sum())
    wape = float(np.abs(actual - predicted).sum() / denominator * 100) if denominator else 0.0
    r2 = float(r2_score(actual, predicted)) if len(actual) > 1 else 0.0
    return {"mae": round(mae, 3), "rmse": round(rmse, 3), "wape": round(wape, 2), "r2": round(r2, 3)}


def train_or_load_model(frame: pd.DataFrame | None = None, force: bool = False) -> dict:
    global MODEL_CACHE
    if MODEL_CACHE is not None and not force and frame is None:
        return MODEL_CACHE

    raw = frame if frame is not None else records_to_frame()
    featured = engineer_features(raw)
    if featured.empty or len(featured) < 100:
        raise ValueError("At least 100 feature-ready sales rows are required. Add more historical sales data.")

    # Split by calendar date (not random rows) so observations from the future never
    # appear in the training window. The most recent 28 days are reserved for the
    # final test; the preceding 28 days are used only to select the model.
    unique_dates = sorted(pd.to_datetime(featured["date"]).dt.normalize().unique())
    if len(unique_dates) < 84:
        raise ValueError("At least 84 calendar days of feature-ready history are required for a chronological train/validation/test split.")
    test_start = pd.Timestamp(unique_dates[-28])
    validation_start = pd.Timestamp(unique_dates[-56])
    train = featured[featured["date"] < validation_start].copy()
    validation = featured[(featured["date"] >= validation_start) & (featured["date"] < test_start)].copy()
    train_validation = featured[featured["date"] < test_start].copy()
    test = featured[featured["date"] >= test_start].copy()
    if min(len(train), len(validation), len(test)) < 10:
        raise ValueError("Not enough observations in one of the chronological data splits. Add more history.")

    x_train, y_train = train[FEATURES], train["sales_units"]
    x_validation, y_validation = validation[FEATURES], validation["sales_units"]
    x_train_validation, y_train_validation = train_validation[FEATURES], train_validation["sales_units"]
    x_test, y_test = test[FEATURES], test["sales_units"]

    candidates = {
        "Random Forest": RandomForestRegressor(
            n_estimators=120, max_depth=14, min_samples_leaf=2,
            max_features=0.9, n_jobs=-1, random_state=42,
        ),
        "Histogram Gradient Boosting": HistGradientBoostingRegressor(
            max_iter=130, learning_rate=0.08, max_leaf_nodes=15,
            l2_regularization=0.5, random_state=42,
        ),
    }
    validation_scores = {}
    for name, model in candidates.items():
        model.fit(x_train, y_train)
        validation_prediction = np.maximum(0, model.predict(x_validation))
        validation_scores[name] = _safe_metrics(y_validation, validation_prediction)["wape"]

    best_name = min(validation_scores, key=validation_scores.get)

    # Refit each candidate on train + validation, then report final metrics on the
    # untouched test window. Model selection was already completed on validation.
    baseline_metrics = _safe_metrics(y_test, test["lag_7"])
    comparison = [{"model": "Seasonal Naive (7-day lag)", **baseline_metrics}]
    fitted_candidates = {}
    for name, model in candidates.items():
        model.fit(x_train_validation, y_train_validation)
        prediction = np.maximum(0, model.predict(x_test))
        comparison.append({"model": name, **_safe_metrics(y_test, prediction)})
        fitted_candidates[name] = model
    best_model = fitted_candidates[best_name]

    # Model-agnostic feature importance makes the explanation available even when
    # the selected estimator does not expose native feature_importances_. The
    # estimator has not been trained on the final test window.
    explain_rows = min(300, len(x_test))
    explain_x = x_test.sample(n=explain_rows, random_state=42) if explain_rows else x_test
    explain_y = y_test.loc[explain_x.index] if explain_rows else y_test
    permutation = permutation_importance(
        best_model, explain_x, explain_y, n_repeats=2, random_state=42,
        scoring="neg_mean_absolute_error", n_jobs=-1,
    )
    raw_importance = np.maximum(0, permutation.importances_mean)
    total_importance = float(raw_importance.sum()) or 1.0
    importance = [{"feature": FEATURES[index].replace("_", " ").title(),
                   "importance": round(float(value / total_importance), 4)}
                  for index, value in sorted(enumerate(raw_importance),
                                             key=lambda item: item[1], reverse=True)[:8]]

    product_codes = {value: index for index, value in enumerate(sorted(raw["product_id"].astype(str).unique()))}
    store_codes = {value: index for index, value in enumerate(sorted(raw["store_id"].astype(str).unique()))}
    result = {
        "model": best_model,
        "model_name": best_name,
        "metrics": comparison,
        "feature_importance": importance,
        "product_codes": product_codes,
        "store_codes": store_codes,
        "trained_at": pd.Timestamp.now().isoformat(timespec="seconds"),
        "training_rows": int(len(featured)),
        "train_start": str(pd.to_datetime(train["date"]).min().date()),
        "train_end": str(pd.to_datetime(train["date"]).max().date()),
        "validation_start": str(pd.to_datetime(validation["date"]).min().date()),
        "validation_end": str(pd.to_datetime(validation["date"]).max().date()),
        "test_start": str(pd.to_datetime(test["date"]).min().date()),
        "test_end": str(pd.to_datetime(test["date"]).max().date()),
        "validation_wape": {key: round(float(value), 2) for key, value in validation_scores.items()},
        "backtest_note": "Models are selected using the preceding 28-day validation window. Reported metrics use a final untouched chronological 28-day test window with observed prior-day lags (rolling one-step backtest). Multi-day recursive forecasts may have higher error.",
    }
    from flask import current_app
    artifact_dir = Path(current_app.config["MODEL_DIR"])
    artifact_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(result, artifact_dir / "shelfsignal_model.joblib")
    MODEL_CACHE = result
    return result


def _holiday_flag(future_date: date) -> int:
    # Small, transparent demo calendar. Replace/extend with a maintained holiday table for production.
    fixed_holidays = {"01-01", "01-26", "05-01", "08-15", "10-02", "12-25"}
    return int(future_date.strftime("%m-%d") in fixed_holidays)


def forecast_series(product_id: str, store_id: str, horizon: int = 7, raw_frame: pd.DataFrame | None = None) -> dict:
    if not 1 <= horizon <= 90:
        raise ValueError("Forecast horizon must be between 1 and 90 days.")
    model_bundle = train_or_load_model()
    records = raw_frame if raw_frame is not None else records_to_frame()
    series = records[(records["product_id"].astype(str) == str(product_id)) &
                     (records["store_id"].astype(str) == str(store_id))].sort_values("date")
    if len(series) < 35:
        raise ValueError("This product/store needs at least 35 days of history for forecasting.")

    history = [int(value) for value in series["sales_units"].tolist()]
    latest = series.iloc[-1]
    future = []
    next_date = pd.to_datetime(series["date"].max()).date() + timedelta(days=1)
    product_code = model_bundle["product_codes"].get(str(product_id))
    store_code = model_bundle["store_codes"].get(str(store_id))
    if product_code is None or store_code is None:
        raise ValueError("The selected product or store is not represented in the trained data.")

    for offset in range(horizon):
        target_date = next_date + timedelta(days=offset)
        row = {
            "lag_1": history[-1],
            "lag_7": history[-7],
            "lag_14": history[-14],
            "lag_28": history[-28],
            "rolling_mean_7": float(np.mean(history[-7:])),
            "rolling_mean_28": float(np.mean(history[-28:])),
            "day_of_week": target_date.weekday(),
            "month": target_date.month,
            "day_of_year": target_date.timetuple().tm_yday,
            "is_weekend": int(target_date.weekday() >= 5),
            "unit_price": float(latest["unit_price"]),
            "promotion": 0,
            "holiday": _holiday_flag(target_date),
            "product_code": product_code,
            "store_code": store_code,
        }
        predicted = max(0.0, float(model_bundle["model"].predict(pd.DataFrame([row], columns=FEATURES))[0]))
        value = int(round(predicted))
        history.append(value)
        future.append({"date": target_date.isoformat(), "forecast": value})

    history_rows = [{"date": pd.to_datetime(row.date).date().isoformat(), "actual": int(row.sales_units)}
                    for row in series.tail(42).itertuples()]
    return {
        "product_id": str(product_id),
        "store_id": str(store_id),
        "product_name": str(latest.get("product_name", product_id)),
        "category": str(latest.get("category", "Uncategorised")),
        "horizon": horizon,
        "history": history_rows,
        "forecast": future,
        "forecast_total": int(sum(item["forecast"] for item in future)),
        "daily_average": round(float(np.mean([item["forecast"] for item in future])), 2),
        "model_name": model_bundle["model_name"],
        "last_actual_date": pd.to_datetime(series["date"].max()).date().isoformat(),
    }


def get_inventory_plan() -> list[dict]:
    """Build a fast inventory plan from pre-aggregated recent demand.

    Inventory planning uses a transparent weighted moving-demand estimate rather
    than launching a separate recursive ML forecast for every SKU. The forecasting
    lab remains the place for full ML predictions. This avoids N model-inference
    loops when the planner contains many product/store combinations.
    """
    rows = Inventory.query.join(Product).order_by(Product.product_name, Inventory.store_id).all()
    if not rows:
        return []

    history = records_to_frame()
    if history.empty:
        return []
    history = history.copy()
    history["date"] = pd.to_datetime(history["date"])
    latest = history["date"].max()
    recent = history[history["date"] >= latest - pd.Timedelta(days=27)]
    grouped = {}
    for (product_id, store_id), subset in recent.groupby(["product_id", "store_id"]):
        subset = subset.sort_values("date")
        last7 = subset.tail(7)["sales_units"]
        last28 = subset.tail(28)["sales_units"]
        avg7 = float(last7.mean()) if not last7.empty else 0.0
        avg28 = float(last28.mean()) if not last28.empty else 0.0
        # A weighted short/long window reacts to recent changes without overreacting.
        grouped[(str(product_id), str(store_id))] = 0.65 * avg7 + 0.35 * avg28

    output = []
    for item in rows:
        average_daily = max(0.0, grouped.get((str(item.product_id), str(item.store_id)), 0.0))
        lead_demand = average_daily * item.lead_time_days
        safety_stock = average_daily * item.safety_stock_days
        reorder_point = lead_demand + safety_stock
        suggested = max(0, int(math.ceil(reorder_point - item.current_stock)))
        coverage_days = round(item.current_stock / average_daily, 1) if average_daily > 0 else None
        if item.current_stock < lead_demand:
            status = "At risk"
        elif item.current_stock < reorder_point:
            status = "Reorder soon"
        else:
            status = "Healthy"
        output.append({
            "id": item.id, "product_id": item.product_id,
            "product_name": item.product.product_name, "category": item.product.category,
            "store_id": item.store_id, "current_stock": item.current_stock,
            "lead_time_days": item.lead_time_days, "safety_stock_days": item.safety_stock_days,
            "average_daily_demand": round(average_daily, 2),
            "lead_time_demand": round(lead_demand, 1),
            "reorder_point": round(reorder_point, 1),
            "suggested_order": suggested, "coverage_days": coverage_days,
            "status": status,
        })
    order = {"At risk": 0, "Reorder soon": 1, "Healthy": 2}
    return sorted(output, key=lambda item: (order[item["status"]], -item["suggested_order"]))
