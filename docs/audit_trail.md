# Audit Trail  
## Overview  

The audit trail system provides a structured, event‑driven logging mechanism that captures every significant action performed during the customer‑transaction cleaning process.
It ensures full traceability, reproducibility, and transparency across all validation, transformation, enrichment, and record‑level operations.

The audit trail is maintained as an in‑memory dictionary and exported as multiple artifact formats (JSON, pretty JSON, Markdown).

The audit trail provides:

- complete visibility into the cleaning pipeline
- structured, timestamped event logs
- row‑level and column‑level traceability
- ML imputation transparency
- reproducible artifact generation
- schema‑driven behavior

It is a core component of the pipeline’s reliability and professional polish

## Details of the Audit Trail Records
The audit trail acts as a centralized recorder for:

- initial dataset statistics
- per‑column validation events
- type coercion actions
- range violations
- nullability enforcement
- winsorization transformations
- numeric imputation operations
- ML‑based categorical imputation operations
- ML dependency drops
- record‑removal actions 
- final dataset statistics
- complete summary of all validation, transformation, and imputation counts

Every event is timestamped and structured for deterministic inspection

### Process Summary 
The summary is interfaced with the audit trail object and contains all the counts of 'bad data' and pertinant actions taken by the cleaner
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
```

## Event Logging Structure
Each audit event is column‑aware, row‑aware, and phase‑aware.
Events include the following fields:

- ***event*** — category of event (e.g., schema_validation, imputation, winsorization)
- ***phase*** — literal method name where the event occurred
- ***action_type*** — type of action (validate, drop, coerce, impute, write, etc.)
- ***column*** — column name (if applicable)
- ***row_indices*** — list of affected row indices
- ***unique_ids*** — list of unique identifiers for affected rows
- ***rows*** — full row data for inspection
- ***message*** — human‑readable explanation of the action
- ***details*** — structured metadata (e.g., bounds, thresholds, before/after values)
- ***dropped_rows*** — dictionary containing removed row indices, unique IDs, and row data
- This structure ensures that every event is self‑contained and interpretable

## Event Recording API

```
def record_event(
    self,
    event: str = None,
    phase: str = None,
    action_type: str = None,
    column: str = None,
    row_indices: list = None,
    unique_ids: list = None,
    rows: list = None,
    dropped_rows: dict = None,
    message: str = None,
    comparison: dict = None,
    details: dict = None
)
```
This API allows all pipeline components to emit structured audit events without duplicating logic

## Example Event
Below is a real event emitted when duplicate transaction_id values are detected and removed:
```
{
  "timestamp": "2026-10-26T13:18:50.592740",
  "event": "schema_validation",
  "phase": "_remove_unique_id_duplicates",
  "action_type": "drop",
  "column": "transaction_id",
  "row_indices": [72, 737],
  "unique_ids": ["T0073", "T0073"],
  "rows": [
    {
      "transaction_id": "T0073",
      "customer_id": "C2634",
      "amount": 272.63,
      "product_category": "Sports",
      "region": "South",
      "timestamp": "1/3/2024 12:29"
    },
    {
      "transaction_id": "T0073",
      "customer_id": "C9568",
      "amount": 27.34,
      "product_category": "Clothing",
      "region": "West",
      "timestamp": "1/3/2024 23:38"
    }
  ],
  "message": "Duplicate unique_id values detected in column 'transaction_id'. All duplicates shown in audit; only later occurrences removed.",
  "dropped_rows": {
    "removed_row_indices": [737],
    "removed_unique_ids": ["T0073"],
    "removed_rows": [
      {
        "transaction_id": "T0073",
        "customer_id": "C9568",
        "amount": 27.34,
        "product_category": "Clothing",
        "region": "West",
        "timestamp": "1/3/2024 23:38"
      }
    ]
  }
}
```
This illustrates:
- full row visibility
- clear explanation
- deterministic removal logic
- structured metadata for downstream inspection

## Artifact Outputs      
The audit trail produces multiple artifact formats for different audiences:

### Compact JSON  
Machine‑readable, minimal formatting.

### Pretty JSON  
Human‑readable, expanded formatting.

### Markdown Report  
Narrative summary of all events.

### Process Summary 
High‑level counts of:

## Purpose and Design Principles
The audit trail is designed to be:

***Reusable***  
Works across any schema and dataset.

***Transparent***  
Every action is logged with full context.

***Deterministic***  
Events are emitted in a stable, predictable order.

***Developer‑Friendly***  
Single recording API, structured events, clear semantics.

***Production‑Ready***  
Supports strict/permissive modes, ML imputation, and record‑level inspection.

