# Imputation_strategy.md

### Overview:

This document describes the imputation strategies used to fill missing values in the customer‑transaction dataset. The goal is to ensure data completeness while preserving behavioral, temporal, and categorical patterns essential for downstream analytics and machine‑learning workflows.

The pipeline supports two classes of imputation:

- Simple Imputation — deterministic, rule‑based filling (median for numeric field)

- ML Imputation — predictive, model‑based filling using RandomForestClassifier for categorical fields

Both strategies are controlled through the declarative schema (schema.json)

## Simple Imputation (Numeric Fields)
Simple imputation is used for numeric columns such as amount. The type of numeric imputation is schema configurable. 
```
     "impute_simple": {
        "enabled": true,
        "strategy": "median" },
```

***Strategy***
- Median is used as the default numeric imputation method.
- Median is robust to outliers and works well with skewed retail transaction distributions.
- Current programming will support the following stategies:
    - median
    - mode
    - mean
    - zero
    - min
    - max

- Numeric winsorization (IQR‑based) is applied before imputation to stabilize extreme values.

***Behavior***
- Missing numeric values are replaced with the median of the non‑missing values.
- This ensures deterministic, reproducible results across runs.
- The audit trail records:
- number of missing values
- median used
- row indices affected

## ML Imputation (Categorical Fields)
ML imputation is used for categorical fields where simple strategies (mode, constant fill) would lose behavioral meaning. This pipeline uses RandomForestClassifier to predict missing categories based on correlated features.

***Why RandomForest***
RandomForest is chosen because it:

- handles nonlinear relationships
- works well with mixed data types
- is robust to noise
- requires no scaling
- provides stable predictions
- supports feature importance (optional future enhancement)

***Workflow***
ML imputation follows a supervised‑learning pattern:

1. Split rows
    -   Rows with known values → training set
    -   Rows with missing values → prediction set

2. Encode categorical features
    - All categorical predictors are encoded using LabelEncoder
    - Timestamp is converted to integer (int64) for model compatibility

3.  Train model
    - RandomForestClassifier is trained on the encoded training set
    - Features typically include:
        - amount
        - timestamp
        - product_category (for region imputation)
        - region (for product_category imputation)

4.  Predict missing values
    - The model predicts the missing category
    - Predictions are inverse‑transformed back to original labels

5.  Audit trail
    - Records:
        - row indices
        - unique IDs
        - predicted values
        - features used
        - model type
        - null count

***Supported Fields***  
ML imputation is currently used for: 
- region
- product_category (after region imputation)  

Imputation column names and rules are schema configurable and can change as long as the names and rules match the structure of the incoming dataset.

## Imputation Order
Imputation order matters because categorical fields may depend on each other

***Numeric imputation (median)***

***ML imputation: region***

***ML imputation: product_category***

-   Uses imputed region as a feature

This ensures consistent, context‑aware predictions

## Schema Configuration
Imputation strategies are defined in schema.json:
```
"amount": {
    "type": "number",
    "impute_simple": {
        "enabled": true,
         "strategy": "median" }},
"region": {
    "type": "category",
    "impute_ml": {
        "enabled": true,
        "model": "RandomForestClassifier",
    "features": ["amount", "timestamp", "product_category"] }}
```
Supported values:
- "median"
- "mode"
- "zero"
- min"
- "max"
- "ml"

## Audit Trail Integration
Every imputation event is logged with:

- event type: imputation
- phase: method name
- action: impute or drop
- column name
- row indices
- predicted or filled values
- strategy used
- model details (for ML)
- feature list
- null counts

This ensures full transparency and reproducibility

## Summary
The pipeline uses:
- Median imputation for numeric fields
- RandomForestClassifier‑based ML imputation for categorical fields

This combination provides:

- deterministic numeric filling
- context‑aware categorical predictions
- robust handling of missing data
- full auditability
- schema‑driven configuration
- reproducible behavior across datasets
