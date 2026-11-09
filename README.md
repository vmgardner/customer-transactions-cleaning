# Customer Transaction Cleaning Pipeline  
## Interactive Demo  
The project demonstrates a production-oriented, schema-driven retail transaction cleaning pipeline  

The cleaning workflow is completely configurable and validates schema and data values, performs outlier handling, implements configurable imputation and produces analysis-ready datasets with comprehensive audit trail reports

Author: Veronica Gardner  
Project: customer-transaction-cleaning

## Overview
Reusable pipeline for cleaning transactional customer data.  

***Features***
- Schema driven validation
- Missing value handling
- Range value assurance 
- ML based imputation
- Numeric imputation
- Audit trail logging
- Data quality reporting
- Technologies
  - Python
  - Pandas
  - NumPy
  - Scikit-learn

Raw CSV ↓ Schema Validation ↓ Cleaning ↓ Imputation ↓ Audit Log ↓ Clean Dataset

## Purpose
This project demonstrates production‑grade data‑quality engineering patterns suitable for real-world retail analytics

Demonstrates practical expertise in:

- Data‑quality engineering

- Declarative schema validation

- Automated preprocessing pipelines

- ML‑based enrichment

- Event‑driven audit‑trail design

- Reproducible environment setup

## Project Summary
The cleaning pipeline performs:

- Full analytical workflow from raw data → validated → cleaned → enriched

- Robust audit trail capturing every transformation, count, and action

- Strict schema enforcement using declarative field attributes

- Record‑level control for validation, coercion, and normalization  
- Winsorization for numeric outlier stabilization  
- Schema‑driven numeric imputation (median, mean, mode, etc.)  
- ML‑based imputation for missing categorical fields (RandomForest)  

Phase 2 (EDA + Feature Engineering) and Phase 3 (Modeling) will follow


## Project Status
This repository currently includes the Phase 1 Data Cleaning Pipeline, consisting of:

- a modular, schema‑driven cleaning engine

- a structured audit trail system

- configuration‑driven file and schema management

- Quickstart notebook demonstrating cleaner usage
- Cleaning_pipeline_demo notebook to show the end‑to‑end usage

This project demonstrates production‑grade data‑quality engineering patterns suitable for real retail analytics pipelines and provides the complete workflow for transforming raw retail transactions into clean, analysis‑ready datasets.

## Repository Layout  
- ***data/raw/*** - sample input transactions
- ***data/clean/*** - cleaned dataset output
- ***config/*** - schema definitions, file and cleaner configuration files
- ***audit_reports/*** - generated audit artifacts (JSON + Markdown)
- ***src/*** - core pipeline python modules 
- ***docs/*** - full technical documentation  
- ***notebooks/*** - directory with the 00_quickstart.ipynb and 01_cleaning_pipeline_demo.ipynb

## Switching strict/permissive mode
Edit the config/cleaner.config.json file to switch between the strick and permissive modes.
```
"strict_mode": true   // strict validation - fail immediately
```
or
```
"strict_mode": false  // permissive validation - schema directive actions
```

## Modify the Raw Data 

You can edit the sample dataset directly on GitHub to see how the cleaning
pipeline responds to different values.

1. Open `data/raw/sample_transactions.csv`
2. Click "Edit this file"
3. Modify any values (e.g., region, product category, amount)
4. Commit your changes
5. Run the Quickstart Notebook  
The audit trail and cleaned output will reflect your changes.

## Installation  
All pipeline execution is performed through the 00_quickstart.ipynb and 01_cleaning_pipeline_demo.ipynb notebooks. These notebooks orchestrate file loading, audit‑trail creation, cleaning, validation, and output generation. No standalone script or CLI entry point is required.

**Create the environment**  
```
conda env create -f environment.yml
conda activate customer-cleaning
```

**Start Jupyter**  
```
jupyter lab
```

## Quickstart Demo (GitHub users)
Open and run:
- notebooks/00_quickstart.ipynb

## Developer Demo (full pipeline walkthrough)
Open and run:
- notebooks/01_cleaning_pipeline_demo.ipynb

## Using Your Own Datafile

The pipeline is fully configuration‑driven execpt for the intial csv file provided by the user   

### Ensure the schema matches the new dataset
Update:
```
  /config/schema.json  
```  

- modify the schema to reflect the data structure of the new csv file  
  
- add all your business rules, constraints, ranges, types... to each column 
  - See schema column details **[Schema Reference](/docs/schema_reference.md#3-column-specification)** for more information  

-  Change the configured output path/filename 
    - See the section **[Name the output file](#name-the-output-file)** for details on configuring the output filename  
-  Change the pd.read_csv() in the notebook to add path/name to the incoming file


Your schema should reflect the following:
- unique_id:  Unique Identifier column of the dataset - mandatory 
- new column names
- new types
- new ranges
- new categorical values
- new imputation strategies
- any imputation and feature changes
- If the dataset has different fields, the schema must be updated accordingly.  

### Name the output file   
The user must provide an output file name and directory path for the cleaned dataset. If the name is not provided the output will either be saved under the current attribute value or be saved with an underscore timestamp and no extension if missing.

```
config/file_config.json
```
Replace the 'output_filename' and 'output_path' with your own values.
```
{
  "paths": {
    "data_paths": {
        "output_path": "../data/clean/",
        "output_filename": "synthetic_transactions.csv" } 
        } 
}
```
 Your file must match the schema defined in the config/schema.json file
- Strict mode enforces exact schema matching
- Permissive mode will drop any column not listed in the schema columns

## Features
**Schema‑Driven Validation**
- Enforces column types, ranges, categories, and nullability
- Declarative configuration for easy extension  
- Directive data attributes for runtime processing decisions  

**Robust Preprocessing**
- Duplicate removal

- Categorical normalization

- Type coercion

- Range checks

**Numeric Outlier Handling**  
- IQR‑based winsorization

- Stabilizes downstream modeling and EDA

**Simple and ML‑Based Imputation**  
- Numeric imputation (median, mean, mode, zero, min, max) 
- RandomForest inference for missing categorical fields

- Supports region, product category, and similar attributes

**Audit‑Trail System**  
- Event‑driven logging

- Before/after values and counts

- Row‑level transformations

- Summary object for reporting

**Reproducible Environment**  
- Conda environment file

- Deterministic setup for all notebooks and scripts

**Demonstration Notebooks**
- End‑to‑end cleaning pipeline

**Outputs***
- Cleaned dataset (data/clean/)
- audit_report_\<timestamp>\.json (compact machine‑readable)
- audit_report_\<timestamp>\_pretty.json (human‑readable)
- audit_report_\<timestamp>\.md (Markdown audit summary)
- process_summary_\<timestamp>\.md (high‑level overview)  


## Documentation  
***Audit Artifacts***  
- [Audit Artifacts](audit_reports/) - audit reports and summary


***Project Documentation***

- [Project Overview](docs/project_overview.md) - global layout of the project

- [Project Structure](docs/project_structure.md) — repository architecture

- [Schema Reference](docs/schema_reference.md) - schema usage and integration

- [Audit Trail System](docs/audit_trail.md) — tracks all actions and row transformations

- [Imputation Strategy](docs/imputation_strategy.md) — numeric and ML‑based imputation logic

- [Technical Reference Guide](docs/technical_reference_guide.md) - developers guide

- [Quidkstart Notebook](docs/quickstart.md) - Quick start to running the pipeline

**Use Cases**  
- Retail transaction cleaning

- Data‑quality enforcement

- ML preprocessing pipelines

- Demonstrating engineering maturity for hiring evaluation

## License
This project is licensed under the MIT ***[LICENSE](/LICENSE)***

