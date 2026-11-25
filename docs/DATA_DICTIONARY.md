# ShelfSignal data dictionary

## `demo_sales.csv`

The bundled dataset is **synthetic demonstration data**, generated deterministically for this project. It is not a real retailer's sales history and must not be represented as such.

| Column | Type | Meaning |
|---|---|---|
| `date` | YYYY-MM-DD | Sales observation date |
| `store_id` | string | Store identifier |
| `product_id` | string | Product identifier |
| `product_name` | string | Human-readable product name |
| `category` | string | Product category |
| `unit_price` | decimal | Observed unit price |
| `promotion` | 0/1 | Whether a promotion flag is active |
| `holiday` | 0/1 | Whether the date is marked as a holiday |
| `sales_units` | integer | Units sold that day |

The file contains 15,120 daily product-store observations: 12 products, 3 stores and 420 dates.

## `demo_inventory.csv`

| Column | Type | Meaning |
|---|---|---|
| `product_id` | string | Product identifier |
| `store_id` | string | Store identifier |
| `current_stock` | integer | Demonstration on-hand stock |
| `lead_time_days` | integer | Assumed supplier replenishment lead time |
| `safety_stock_days` | integer | Additional days of average demand held as safety stock |

Inventory values are synthetic assumptions. Replace them with an actual inventory snapshot for operational use.

## User-upload CSV

Required columns: `date`, `store_id`, `product_id`, `sales_units`.

Optional columns: `unit_price`, `promotion`, `holiday`, `product_name`, `category`.

A `(date, store_id, product_id)` combination should appear at most once. If a duplicate is present in an upload, the last row in that file is kept. Matching existing database rows are updated.
