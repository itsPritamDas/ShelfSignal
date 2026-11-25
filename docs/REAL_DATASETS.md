# Moving from demo data to a real dataset

The default project includes deterministic synthetic data so the application runs immediately after installation. For a stronger academic submission, replace or supplement it with a documented public dataset.

## M5 Forecasting Accuracy (retail sales)

Source: https://www.kaggle.com/competitions/m5-forecasting-accuracy/data

The M5 competition provides `sales_train_validation.csv`, `calendar.csv` and `sell_prices.csv`. It contains daily unit sales for products sold by Walmart stores, with calendar and selling-price information.

### Convert a manageable subset

1. Download the three files from Kaggle (a Kaggle account may be required).
2. Place them in a folder such as `datasets/m5/`.
3. Convert one store and five products (about 9,565 daily rows, within the demo importer limit):

```powershell
python scripts/convert_m5.py `
  --sales datasets/m5/sales_train_validation.csv `
  --calendar datasets/m5/calendar.csv `
  --prices datasets/m5/sell_prices.csv `
  --store CA_1 `
  --products 5 `
  --output data/m5_sales.csv
```

4. Open ShelfSignal → Data & model → Import your own retail data, and upload `data/m5_sales.csv`.
5. Retrain the model and record the metrics before and after changing datasets.

The converter sets the direct promotion flag to zero because M5 does not provide a simple retailer promotion field; it does not incorrectly treat SNAP indicators as promotions. Event dates are mapped to the holiday/event flag. The converter labels product names with the source item identifier because the benchmark does not provide consumer-facing product names.

## Data quality checklist

- Explain the source, date range, geographical coverage and any filters used.
- Keep a copy of the original downloaded files and note their versions.
- Verify duplicates and missing selling prices.
- Check that each date-store-product key is unique after conversion.
- Compare the selected baseline against machine-learning models.
- Keep a chronological holdout and do not randomly shuffle a time series.
- State that M5 represents historical US Walmart data, not current Indian retail demand.
