# ShelfSignal — final-year report outline

## Abstract
Summarise the retail demand-planning problem, data source, forecasting methods, evaluation approach, inventory decision logic and key measured results. Do not report expected or illustrative metrics as achieved results.

## 1. Introduction
- Retail demand uncertainty and inventory planning.
- Why accurate SKU/store-level forecasting matters.
- Scope of the prototype.

## 2. Problem statement
Design a data-driven system that analyses historical product-store sales, forecasts short-term demand and provides transparent reorder recommendations using configurable stock and lead-time inputs.

## 3. Objectives
- Build a repeatable sales-data ingestion and preprocessing pipeline.
- Explore temporal and product-level sales patterns.
- Engineer lag, rolling and calendar features.
- Compare statistical/baseline and machine-learning approaches.
- Evaluate forecasts using chronological validation.
- Translate demand estimates into an explainable inventory policy.
- Deliver an interactive web dashboard.

## 4. Literature review
Review retail time-series forecasting, global versus local models, tree-based regression, seasonal baselines, forecast accuracy metrics and reorder-point policies. Cite original papers, benchmark documentation and dataset sources.

## 5. Dataset and preprocessing
Document source, geographic coverage, date range, number of products/stores/rows, data types, missing values, duplicate handling, price joins and known limitations. Label synthetic data as synthetic.

## 6. Exploratory data analysis
Include sales distribution, weekday patterns, category mix, product/store differences, price trends, holiday/event comparisons and demand outliers.

## 7. Methodology
Explain train/test chronology, lag features, rolling means, categorical encodings, baselines, Random Forest, Histogram Gradient Boosting, recursive forecasting and permutation importance.

## 8. Evaluation and results
Report MAE, RMSE, WAPE and R² on held-out dates. Compare all models fairly. Include per-category or per-store results where sample size permits. Discuss where the model fails.

## 9. Inventory decision-support logic
Explain lead-time demand, safety stock, reorder point and suggested order. State what inventory fields are observed inputs versus synthetic assumptions.

## 10. System design and implementation
Include architecture diagram, database schema, API endpoints, user interface screenshots, CSV workflow and deployment environment.

## 11. Limitations and future scope
Discuss recursively compounding forecast errors, promotions not planned in the future, incomplete stock movement data, simplistic safety stock, event calendar coverage and generalisation to new products/stores.

## 12. Conclusion
Summarise validated outcomes and the project contribution without claiming business impact that has not been measured.

## References and appendices
Include dataset citations, libraries, relevant research, data dictionary, API details and experiment configurations.
