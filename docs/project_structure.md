# project_structure.md

**Project Structure — Technical Synopsis:**  
The project is organized into modular, production‑oriented components that separate core cleaning logic, documentation, data assets, notebooks, and model artifacts. This structure supports maintainability, reproducibility, and clear workflow boundaries across data engineering, EDA, and modeling phases..

**Directory Layout:**
```
Code project/
│
├── src/
│   ├── __init__.py
│   ├── customer_transaction_cleaner.py
│   ├── config_manager.py
│   ├── audit_trail.py
│   ├── file_manager.py
│   └── utilities.py
│
├── notebooks/
│   ├── 00_quickstart.ipynb
│   └── 01_cleaning_pipeline_demo.ipynb
│
├── data/
│   ├── raw/
│   └── clean/
|
├── config/
│   ├── cleaner_config.json
│   └── file_config.json
│   └── schema.json
│
├── docs/
│   ├── Index.md
│   ├── quickstart.md
│   ├── project_overview.md
│   ├── project_structure.md
│   ├── schema_reference.md
│   ├── audit_trail.md
│   ├── imputation_strategy.md
│   └── technical_reference_guide.md
|
├── environment.yml
└── LICENSE
└── README.md
└── .gitignore
```

### src/  

The src/ directory holds all executable Python modules that implement the cleaning engine, populates audit-trail and process summary objects, manages file and config access and support for informative error handling

**- customer_transaction_cleaner.py** — main schema‑driven cleaning pipeline; orchestrates validation, normalization, winsorization, imputation, and audit logging.

**-  audit_trail.py** — structured audit‑logging framework capturing before/after values and transformation metadata.

**- file_manager.py** — standardized I/O for loading raw data and writing cleaned output and audit reports.  

**- config_manager.py** - maintains all access to configuration files and data schema  

**- utilities.py** — shared helper functions and error handling support

### notebooks/
Interactive Jupyter notebooks demonstrating the full workflow from raw data to modeling

**00_quickstart** - an intuitive and easy to use tool to run the pipeline demo  

**01_cleaning_pipeline_demo.ipynb** — deeper dive demonstration of the cleaning engine

**02_eda_feature_engineering.ipynb** — exploratory analysis and feature construction using cleaned data. (future implementation)

**03_modeling.ipynb** — downstream ML modeling using engineered features (future implementation)

### data/
Structured data directories supporting reproducible experiments

**raw/** — unmodified input datasets

**cleaned/** — outputs from the cleaning pipeline

**features/** — engineered features for future modeling

### docs/
Project documentation describing architecture, schema definitions, audit design, and workflow behavior

***Project Documentation***  

- [Quick Start](quickstart.md) — repository architecture

- [Index](index.md) — repository architecture

- [Project Overview](project_overview.md) - global layout of the project

- [Schema Reference](schema_reference.md) - schema usage and integration

- [Audit Trail System](audit_trail.md) — tracks all actions and row transformations

- [Imputation Strategy](imputation_strategy.md) — numeric and ML‑based imputation logic

- [Technical Reference Guide](technical_reference_guide.md) - discusses separation of concerns
