# ShelfSignal

**Explainable Retail Demand Forecasting & Inventory Intelligence Platform**

ShelfSignal is a final-year B.Tech CSE Data Science project. It analyses historical product sales, compares forecasting models, predicts future demand and translates forecasts into transparent inventory replenishment suggestions.

> **Demo-data notice:** The bundled CSV files are synthetic demonstration data generated specifically for this project. They are not actual sales or stock records from a retailer. The application supports CSV import and includes an optional converter for a subset of the public M5 retail forecasting dataset.

## 1. What the application includes

- Executive dashboard with recent sales, product, store and inventory-risk KPIs.
- Product/store demand forecast for 7, 14 or 28 days.
- Lag and rolling-window feature engineering.
- Model comparison: 7-day seasonal-naive baseline, Random Forest and Histogram Gradient Boosting.
- Chronological holdout evaluation using MAE, RMSE, WAPE and R².
- Model-agnostic permutation feature importance for an interpretable signal view.
- Inventory decision support using forecasted lead-time demand and safety-stock assumptions.
- Editable on-hand stock values and supplier lead-time settings.
- CSV import with validation and upsert behaviour.
- SQLite database for an easy local start, with MySQL support through one environment setting.
- Responsive HTML/CSS/JavaScript dashboard with lightweight SVG charts (no charting CDN required).

## 2. Technology stack

| Layer | Technology |
|---|---|
| Programming | Python 3.10+ |
| Data manipulation | Pandas, NumPy |
| Machine learning | Scikit-learn |
| Backend | Flask, Flask-SQLAlchemy |
| Database | SQLite by default; MySQL supported |
| MySQL driver | PyMySQL |
| Frontend | HTML5, CSS3, vanilla JavaScript |
| Visualisation | SVG charts rendered with JavaScript |
| Model evaluation | MAE, RMSE, WAPE, R²; chronological holdout |

## 3. Quick start (Windows PowerShell)

Open PowerShell in the extracted `ShelfSignal` folder.

### Step 1 — Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation for this terminal session, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Step 2 — Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3 — Configure the environment

```powershell
Copy-Item .env.example .env
```

The default `.env.example` uses SQLite. No database server is required for the first run.

### Step 4 — Start ShelfSignal

```powershell
python run.py
```

Open this address in a browser:

```text
http://127.0.0.1:5000
```

On first launch the application creates its tables and seeds the bundled synthetic dataset automatically. The first dashboard load trains and benchmarks the forecasting models, so it can take a little longer than subsequent requests.

## 4. MySQL configuration (optional)

SQLite is the easiest way to start. To use MySQL instead:

1. Start the MySQL server.
2. Create a database:

```sql
CREATE DATABASE shelfsignal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

3. Edit `.env` and set `DATABASE_URL` (replace the placeholders):

```env
DATABASE_URL=mysql+pymysql://USERNAME:PASSWORD@localhost:3306/shelfsignal?charset=utf8mb4
SECRET_KEY=replace-with-a-long-random-secret
FLASK_DEBUG=1
```

If the password contains URL-reserved characters (such as `@`, `#`, `/` or `:`), URL-encode the password portion. The application creates the tables automatically through SQLAlchemy. `schema_mysql.sql` is included as a reference schema.

To initialise a fresh MySQL database, make sure it contains no existing ShelfSignal sales data. On first run, the bundled demo data is seeded if the `sales_records` table is empty.

## 5. How to use the application

### Overview

Review total units sold in the latest 30 days, product/store counts, inventory risk, daily sales activity, category contribution and top-selling products.

### Demand forecast

1. Choose a product and store.
2. Select 7, 14 or 28 days.
3. Generate a forecast.
4. Review expected units, daily average and the actual-versus-forecast chart.

The forecast assumes no future promotions and carries forward the latest observed unit price. The bundled calendar applies a small fixed-date holiday list for demonstration; extend it with a reliable local calendar before making any real business claim.

### Inventory planner

The inventory recommendation uses:

```text
Lead-time demand = sum of forecast demand during supplier lead time
Safety stock = recent average daily demand × safety-stock days
Reorder point = lead-time demand + safety stock
Suggested order = max(0, reorder point − current stock)
```

Edit current stock in the table and save it to recalculate the recommendation. The sample stock, lead-time and safety-stock inputs are synthetic. A production replenishment engine would also need supplier minimum order quantities, pack sizes, inbound purchase orders, backorders, shelf capacity, expiry and service-level targets.

### Data & model

Review the model benchmark and permutation feature importance, retrain the model after importing data, and download the sample CSV template.

## 6. Import your own CSV

In the application, go to **Data & model → Import your own retail data**.

Required columns:

```csv
date,store_id,product_id,sales_units
2025-01-01,STORE_01,P001,38
```

Optional columns:

```text
unit_price, promotion, holiday, product_name, category
```

Date format should be `YYYY-MM-DD`. The importer accepts up to 10,000 rows per upload and a maximum file size of 12 MB. It updates an existing row when the `(date, store_id, product_id)` key already exists. Uploading rows for a previously unseen product or store creates the necessary product and inventory records. New inventory rows start with zero current stock and default 3-day lead/safety settings; edit them in the Inventory Planner.

The importer does not delete history that is absent from an uploaded file. For a clean experiment, use a fresh database or remove the local SQLite file after stopping the app, then restart and re-seed.

## 7. Use a public real-world retail dataset (recommended for the final submission)

The default dataset is included only to make the project runnable immediately. For stronger academic evidence, the project includes `scripts/convert_m5.py` and instructions in [`docs/REAL_DATASETS.md`](docs/REAL_DATASETS.md) for importing a subset of the Kaggle M5 Forecasting Accuracy data.

M5 represents historical US Walmart sales from 2011–2016. It is a public benchmark, not current Indian retail data. Explain the geography, time period, filters and limitations in the project report.

## 8. Model methodology

### Feature engineering

Per product-store time series, the pipeline generates:

- Lagged demand: 1, 7, 14 and 28 days.
- Rolling mean demand: 7 and 28 days, shifted by one day to prevent current-target leakage.
- Calendar variables: weekday, month, day of year and weekend flag.
- Price, promotion and holiday/event flags.
- Encoded product and store identifiers.

### Benchmark and validation

The pipeline compares a seasonal-naive benchmark (7-day lag), Random Forest and Histogram Gradient Boosting. It uses an earlier 28-day validation window to select the machine-learning estimator, then reports the final benchmark metrics on a separate, later 28-day test window. The selected estimator is fitted on the combined training and validation windows for the final test.

The split is chronological: training, validation and final test are separated by date, with at least 84 feature-ready calendar dates required. Metrics are based on a **rolling one-step backtest**: the lag features for each test date use the actual earlier observations. The 7/14/28-day app forecast is **recursive**: predictions are fed back into future lag features. Recursive multi-day error can be higher than the displayed one-step holdout metrics. This distinction should be explained in the viva.

Metrics:

- **MAE:** average absolute units of prediction error.
- **RMSE:** error metric that penalises larger misses more heavily.
- **WAPE:** total absolute error divided by total actual demand, expressed as a percentage.
- **R²:** coefficient of determination; it can be negative when a model performs worse than the mean baseline.

Permutation importance estimates how much holdout MAE worsens when a feature is shuffled. It is a diagnostic signal, not proof of causation.

## 9. Project structure

```text
ShelfSignal/
├── app/
│   ├── __init__.py                 # Flask application factory and database setup
│   ├── config.py                   # Environment configuration
│   ├── extensions.py               # SQLAlchemy extension
│   ├── models.py                   # Product, inventory and sales tables
│   ├── routes/
│   │   ├── api.py                  # JSON API endpoints
│   │   └── pages.py                # Dashboard page route
│   ├── services/
│   │   ├── data_service.py         # Demo seeding, CSV validation/import
│   │   └── forecasting.py         # Feature engineering, training and forecasts
│   ├── static/
│   │   ├── css/styles.css         # Responsive dashboard styling
│   │   └── js/app.js               # UI rendering and API integration
│   └── templates/index.html        # Dashboard UI
├── data/
│   ├── demo_sales.csv              # Synthetic retail history
│   └── demo_inventory.csv          # Synthetic inventory inputs
├── docs/
│   ├── DATA_DICTIONARY.md
│   └── REAL_DATASETS.md
├── scripts/convert_m5.py           # Optional M5 subset converter
├── tests/                           # Feature engineering tests
├── .env.example
├── requirements.txt
├── schema_mysql.sql
└── run.py
```

## 10. Run the tests

```powershell
python -m unittest discover -s tests -v
```

## 11. JSON API reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/overview` | Dashboard metrics and sales activity |
| GET | `/api/products` | Products, stores and latest prices |
| GET | `/api/forecast?product_id=P001&store_id=STORE_01&horizon=7` | Demand forecast |
| GET | `/api/inventory` | Replenishment plan |
| PATCH | `/api/inventory/<id>` | Update stock/lead/safety inputs |
| POST | `/api/upload` | Import sales CSV (`multipart/form-data`, key `file`) |
| POST | `/api/retrain` | Retrain and compare models |

## 12. Important limitations and next steps

This is a strong academic prototype, not a production inventory platform. Before any live business use:

- Integrate verified point-of-sale and stock-on-hand data.
- Add authentication, authorisation, audit logs and CSRF protection.
- Add robust date/holiday calendars and promotion plans.
- Include stock movements, inbound orders, returns and stockouts.
- Add time-series cross-validation and compare forecasts at multiple horizons.
- Evaluate prediction intervals and service-level outcomes.
- Add automated tests for the API, database and data import flows.
- Use a production WSGI server, HTTPS, secrets management and database backups.

The Flask development server is for local development only. Do not expose it directly to the public internet.

## 13. Suggested final-year report title

**“ShelfSignal: An Explainable Machine Learning-Based Retail Demand Forecasting and Intelligent Inventory Decision-Support System.”**

Suggested report sections: Abstract, Introduction, Problem Statement, Literature Review, Objectives, Dataset and Data Dictionary, Methodology, Feature Engineering, Model Experiments, Results and Discussion, Application Architecture, Inventory Decision Logic, Limitations, Future Scope, Conclusion and References.

## Interface and inventory planner update

The current interface uses a larger typography scale, stronger visual hierarchy, clearer inventory summary metrics, product/store search, status filtering, larger editable stock inputs, and explicit update timestamps. The inventory endpoint calculates its planning estimate from a grouped weighted moving average (65% trailing 7-day average + 35% trailing 28-day average). This avoids launching a separate recursive ML forecast for every inventory row and makes the planner responsive as the catalogue grows. The dedicated Demand Forecast page continues to use the trained machine-learning forecasting models.

The main page is `app/templates/index.html` (a Flask/Jinja template, not a standalone static file). Styling is in `app/static/css/styles.css`; dashboard interactions are in `app/static/js/app.js`; inventory calculations are in `app/services/forecasting.py`.

### Interactive chart tooltips

The dashboard's sales trend, category doughnut and demand forecast charts support pointer hover and keyboard focus. Hover over a plotted point or doughnut segment to see the date/category, unit count and percentage where applicable. The tooltip follows the pointer like a market-data chart.


## Deploy to Vercel (Flask + MySQL)

This repository includes `index.py`, `vercel.json`, and `public/static/` for Vercel.
The Flask application is exposed as a Python function. Static CSS/JavaScript/CSV
assets are served from `public/static/`; model cache files are written to `/tmp`
because the deployed application filesystem is read-only.

### 1. Create a managed MySQL database
Create a database named `shelfsignal` using a MySQL provider. Allow connections
from Vercel (or use the provider's documented network access settings). Keep the
hostname, port, database, username, and password private.

### 2. Push this local project to GitHub
In PowerShell, open this project folder and run:

```powershell
git init
git add .
git commit -m "Prepare ShelfSignal for Vercel deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ShelfSignal.git
git push -u origin main
```

If this folder is already a Git repository, do not run `git init` or add a second
remote. Use `git remote -v`, then commit and push the changes to the existing repo.

### 3. Import the GitHub repository into Vercel
In Vercel, choose **Add New -> Project**, import the ShelfSignal repository, and
keep the Root Directory as `./`. The included `vercel.json` routes requests to
the Flask entry point. Do not set a custom build command or output directory.

### 4. Add Vercel environment variables
Under **Project -> Settings -> Environment Variables**, add:

- `DATABASE_URL` = `mysql+pymysql://USERNAME:PASSWORD@MYSQL_HOST:3306/shelfsignal?charset=utf8mb4`
- `SECRET_KEY` = a long random secret (not the example value)
- `FLASK_DEBUG` = `0`
- `SHELFSIGNAL_SEED_DEMO` = `1` for the first deployment if you want the bundled
  sample data inserted into an empty database; otherwise set `0` and import a CSV.

URL-encode reserved characters in the database username/password. Set variables for
Production (and Preview too, if you intend to test preview deployments). Redeploy
after changing environment variables.

### 5. Verify
Open `/api/health` and confirm it returns `{"status":"ok","service":"ShelfSignal API"}`.
Then open `/`, check the dashboard, upload a CSV, update inventory, and run a forecast.

### Important deployment notes
- MySQL is the persistent source of truth. Do not use SQLite for the deployed site.
- Vercel `/tmp` is temporary and may be cleared between function instances. The app's
  trained model artifact is therefore a cache only; it can be rebuilt from MySQL data.
- Uploaded CSV contents are imported directly into MySQL; the app does not rely on
  saving uploaded files to the deployment filesystem.
- Initial model training can be compute-intensive. If a forecast times out or exceeds
  function limits, move model training to a background worker or train offline and
  store model artifacts in durable object storage.
- `db.create_all()` creates tables for a new database. For a larger production system,
  use database migrations and a one-time controlled seed/import process.
