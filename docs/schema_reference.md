# Schema Reference  
Version aligned with current cleaner architecture
# 1. Overview  
This schema defines the data structure all rules the cleaner uses to validate, normalize, impute, and audit a dataset.
The cleaner is fully schema‑driven: every column’s behavior is determined by its schema entry.

The schema controls:

- Column types
- Required vs optional fields
- Null handling rules
- Simple numeric imputation
- ML‑based categorical imputation
- Allowed values
- Range constraints
- Winsorization
- Audit trail behavior
- Summary output

 Strict vs permissive mode affects how nulls and validation failures are handled.

# 2. Schema Structure
```json
{
  "schema": {
    "unique_id": "transaction_id",
    "columns": {
      "<column_name>": { ... }
    }
  }
}
```
### unique_id:
 A customer driven column whose values uniquely identify each row.

The unique_id is used extensively throughout the process:
- audit trail
- row‑level tracking
- ML dependency dropping
- summary reporting

# 3. Column Specification  

Each column has a block describing its type and rules.  

``` 
"transaction_id": {
  "type": "string",
  "required": true,
  "nullable": false,
  "nullable_action": "drop",
  "description": "Unique transaction identifier"
}
```
## Common attributes
```
| Attribute        | Type      | Description                               |
|------------------|-----------|-------------------------------------------|
| type             | string    | Column data type                          |
| required         | boolean   | Column must exist                         |
| nullable         | boolean   | Whether nulls are allowed                 |
| nullable_action  | string    | `"drop"` or `"keep"`                      |
| allowed          | list      | values allowed in the field               |
| min              | number    | minimum value the field can be            |
| max              | number    | maximum value the field can be            |
| impute_ml        | object    | flag column for imputation                |
| -- enabled       | boolean   | true - field is active for imputation     |
| -- model         | string    | type of imputation model used             |
| -- features      | list      | column used in imputation                 |
| normalize        | string    | true: normalize original for df comparison|
| description      | string    | Human‑readable description                |
-------------------|-----------|-------------------------------------------|
```
# 4. Simple Numeric Imputation
Used for numeric columns such as amount.

Schema Format

``` 
"impute_simple": {
  "enabled": true,
  "strategy": "median"
}
```
## Supported Strategies

 ```
| Strategy         | Description                               |
|------------------|-------------------------------------------|
| median           | midpoint value in list                    |
| mean             | average value of the list                 |
| mode             | most frequent value                       |
| zero             | Column must exist                         |
| min              | minimum value of list                     |
| required         | naximum value of list                     |
|------------------|-------------------------------------------|
```
## Behavior
Permissive mode
- Nulls are replaced using the strategy
- Audit event: impute_simple_permissive_<col>
- Summary key: <col>_imputed

Strict mode
- Any null triggers a fatal error
- Audit event: impute_simple_strict_failure_<col>
- Cleaner stops

# 5. ML Imputation (Categorical)
Used for categorical columns such as region and product_category.

## Schema format
```
"impute_ml": {
  "enabled": true,
  "model": "RandomForestClassifier",
  "features": ["amount", "timestamp", "product_category"]
}
```
## Attributes
 ```
|------------------|-----------|-----------------------------------------------------|
| enabled          | boolean   | Turns ML imputation on/off                          |
| model            | string    | ML model name (currently RandomForestClassifier)    |
| features         | boolean   | Columns used as predictors                          |
|------------------|-----------|-----------------------------------------------------|
```
## Behavior
Permissive mode
- Nulls are imputed using ML predictions
- Audit event: impute_ml_permissive_<col>
- Summary key: <col>_imputed

Strict mode
- Nulls trigger fatal error
- Audit event: impute_ml_strict_failure_<col>
- Cleaner stops

# 6. ML Dependency Dropping
If two ML‑imputed columns depend on each other and both are null, the row cannot be recovered.

Example:

- region depends on product_category
- product_category depends on region

If both are null → drop row.

 ## Audit event
``` 
event: "schema_validation"
phase: "drop_unrecoverable_ml_pairs"
details:
  ml_dependency_pairs: [("region", "product_category"), ...]
  row_indices: [...]
  rows: [...]

```
## Summary
```
 "rows_dropped": <count>
```
# 7. Winsorization
Used for numeric columns to cap extreme values.

## Schema format
``` 
"winsorize": true
```
## Behavior
- Caps values at percentile thresholds (implementation‑specific)
- Audit event: winsorize_<col>

# 8. Validators
Used to enforce numeric or datetime constraints.

Examples
``` 
"min": 0,
"max": 10000
```
```
"min_date": "2000-01-01",
"max_date": "2030-01-01"
```
## Behavior
- Violations → strict failure or permissive correction
- Audit event: validation_<col>

# 9. Allowed Values (Categories)
Used for categorical columns.
``` 
"allowed": ["north", "south", "east", "west"]
```
## Behavior
- Unknown values are nulled 
- Audit event: validate category_values_(col)
# 10. Audit Trail Structure
Every transformation produces an audit event.

## Event fields
 ```
| Field            | Description                                                     |
|------------------|-----------------------------------------------------------------|
| event            |  Type of event (imputation, validation, schema_validation, etc.) |
| column           |  Column affected (or null for multi‑column events)               |
| row_indices      |  List of row indices involved                                    |
| action_type      |  Type of action taken: drop, impute, validate...                 |
| unique_ids       |  Values of the unique ID column                                  |
| rows             |  full row snapshot                                               |
| message          |  human readable description                                      |
| phase            |  method name                                                     |
| dropped_rows     |  dictionary of dropped row info                                  |
| details          |  dictionary holding detail info from logging transformarion      |
| comparison       |  dictionary that holds the dataframe comparison info             |
|------------------|------------------------------------------------------------------|
```
Audit trail is chronological and complete

    event: str = None,
    phase: str = None,
    action_type: str = None,
    column: str = None,
    row_indices: list = None,
    unique_ids: list = None,
    rows: list = None,
    message: str = None,
    dropped_rows: dict = None,
    comparison: dict = None,
    details: dict = None,


# 11. Summary Structure
The summary is dynamically populated throughout the cleaning process

Example output
``` 
 "summary": {
    "validation": {
      "original_nulls": 10,
      "rows_dropped": 5,
      "invalid_numerics": 3,
      "invalid_booleans": 0,
      "invalid_strings": 4,
      "invalid_categories": 5,
      "invalid_datetime": 0,
      "invalid_datetime_range": 0,
      "invalid_numeric_range": 0,
      "values_nulled": 2,
      "duplicate_records": 1
    },
    "transformation": {
      "winsorized_columns": 1,
      "winsorized_values": 100
    },
    "imputation": {
      "amount_imputed": 3,
      "region_imputed": 3,
      "product_category_imputed": 2
    }
  }
```

# 12. Full Example of Demo Schema (Current Version)
```
{
    "schema": {
        "unique_id": "transaction_id",
        "columns": {
            "transaction_id": {
                "type": "string",
                "required": true,
                "nullable": false,
                "nullable_action": "drop",
                "description": "Unique transaction identifier"
            },
            "customer_id":{
                "type": "string",
                "required": true,
                "nullable": false,
                "nullable_action": "drop",
                "description": "Unique customer identifier"
            },
            "amount": {
                "type": "number",
                "required": true,
                "min": 0,
                "max": 10000,
                "nullable": true,
                "nullable_action": "keep",
                 "impute_simple": {
                    "enabled": true,
                    "strategy": "median" },
                "winsorize": true,
                "description": "Transaction amount in USD"
            },
            "region": {
                "type": "category",
                "required": true,
                "allowed": ["north", "south", "east", "west"],
                "nullable": true,
                "nullable_action": "keep",
                 "impute_ml": {
                    "enabled": true,
                    "model": "RandomForestClassifier",
                    "features": ["amount", "timestamp", "product_category"] }, 
                "normalize": true,
                "description": "Geographic region"
            },
            "product_category": {
                "type": "category",
                "required": true,
                "allowed": ["grocery", "home", "electronics", "clothing", "sports", "beauty"],
                "nullable": true,
                "nullable_action": "keep",
                "impute_ml": {
                    "enabled": true,
                    "model": "RandomForestClassifier",
                    "features": ["amount", "timestamp", "region"] },
                "normalize": true,
                "description": "category of the sales item"
            },
            "timestamp": {  
                "type": "datetime",
                "required": true,
                "min_date": "2000-01-01",
                "max_date": "2030-01-01",
                "nullable": false,
                "nullable_action": "drop",
                "description": "Transaction timestamp"
            }
        }
    }
}
```

