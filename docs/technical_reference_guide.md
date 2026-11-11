# Customer Transactions Cleaning Pipeline  
# Technical Reference Guide  

This document provides operational and development guidance for engineers working on the Customer Transaction Cleaning Pipeline. It supplements the Project Overview by focusing exclusively on development workflow, environment behavior, extension patterns, testing, and reproducibility.

## Development Workflow  
***Environment Setup***

The project uses a reproducible Conda environment defined in environment.yml.

Create and activate the environment:  
```
conda env create -f environment.yml
conda activate customer-cleaning
```
Start Jupyter:
```
jupyter lab
```
The environment includes:

- Python 3.11
- Pandas, NumPy, scikit‑learn
- PyArrow
- JupyterLab + ipykernel
- •	Category Encoders (installed via pip)

All versions are pinned for deterministic behavior.
***Kernel Registration***
If Jupyter does not show the customer-cleaning kernel:
```
python -m ipykernel install --user --name customer-cleaning
```

## Using Your Own Datafile (Plug‑and‑Play)
The pipeline is fully configuration‑driven execpt for the intial csv file provided by the user   

### Ensure the schema matches the new dataset

- modify the schema to reflect the data structure of the new csv file  
  
- add all your business rules, constraints, ranges, types... to each column 
 
  - See schema column details **[Schema Reference](/docs/schema_reference.md#3-column-specification)** for more information  

-  Change the configured output path/filename 
    - See the section **[Name the output file](#name-the-output-file)** for details on configuring the output filename  

-  Change the pd.read_csv() in the notebook to add path/name to the incoming file

Schema path:
```
  /config/schema.json
```

### Name the output file
The user must provide an output file name and directory path for the cleaned dataset. If the name is not provided the output will be saved with the name currently in the field. If the field is null then the file will be saved as an underscore and timestamp and no extension.

```
  /config/file_config.json
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

### Run the pipeline normally
```
    00_quikstart.ipynb 
```
  or
```
     01_cleaning_pipeline_demo.ipynb
```

The pipeline allows you to:
- loads the new CSV (df)
- apply the updated schema
- call the cleaner() passing in the new df file
    - cleaner.clean(df)
- new audit artifacts will be automatically generated
- timestamps everything to avoid overwriting previous runs

***Strict Failurs***
A strict failure will cause the program to stop executing immediately. If the run-time process reached a point of audit creation and population the audit_report will be saved to the audit_reports/strict_failure/ directory. The partial audit_report supplements troubleshooting and help to identify the point of failure.
```
  ../audit_reports/strick_failure/
```


### Inspect new audit artifacts
The pipeline produces four audit artifacts per run:

- audit_report_\<timestamp>\.json - compact machine‑readable
- audit_report_\<timestamp>\_pretty.json  - human‑readable
- audit_report_\<timestamp>\.md  - Markdown audit summary
- process_summary_\<timestamp>\.md  -high‑level overview  

Artifacts are written to: 
```
audit_reports/
```

## Python Kernel State Behavior  
VS Code and Jupyter maintain interpreter state across runs. This affects development:  
***Cached State***
- Imported modules remain cached
- Old DataFrames persist
- Schema objects may not refresh
- File paths may remain bound to earlier working directories

***Symptoms***
- Pipeline appears to use “old data”
- Schema changes do not apply
- CSV edits are not reflected
- Audit artifacts appear stale

***Resolution***  
Restart the Python kernel before running to help ensure a clean execution environment. 

- full pipeline demos
- schema modifications
- audit trail debugging
- imputation logic changes

## File Path Behavior  
The pipeline uses relative paths throughout:

- ensures portability
- works on GitHub and local environments
- avoids absolute path failures
- supports timestamped audit artifacts  

When generating Markdown links in notebooks:
```
path.replace("\\", "/")
```
Is required for cross‑platform compatibility

***Compact JSON***  
Some editors may not render compact JSON cleanly.
The pretty‑printed version is provided for inspection

***Safe Writes***  
All artifact writes use safe_write():

- logs write failures
- respects strict mode
- ensures reproducible timestamped filenames

## Notebook Execution Workflow  
***Quickstart Notebook***  
- 00_quickstart.ipynb  
Minimal demonstration for GitHub users.

***Developer Pipeline Notebook***
-   01_cleaning_pipeline_demo.ipynb  

Full walkthrough including:

- file loading
- pipeline execution
- audit inspection
- artifact linking

***Execution Rules***

- Restart kernel before running full demos
- Ensure environment is activated
- Ensure working directory is project root
- Avoid running notebooks from nested directories

## Extending the Pipeline  
### Adding New Fields  
- Update schema file
- Add normalization rules if needed
- Add imputation strategy
- Add validation logic if custom
- Update cleaner module if new directive is required

### Adding New Imputation Strategies  
Extend imputation handler:

- add strategy name
- implement logic
- emit audit events
- update schema reference documentation

### Adding New Audit Event Types
- update AuditTrail class  
- add event category
- add structured metadata
- update Markdown summary generator
- update JSON schema if applicable

### Adding New Pipeline Stages
Follow existing stage patterns:
- validate
- clean
- enrich
- verify  

Each stage must:
- emit audit events
- maintain deterministic ordering
- preserve strict/permissive semantics

## Testing Guidelines
### Unit Tests
Recommended areas:
- schema validation
- type coercion
- normalization
- winsorization
- imputation
- audit event emission
- file writing behavior

### Regression Tests
Use sample datasets under data/raw/ to validate:
- deterministic outputs
- stable audit artifacts
- consistent imputation behavior
- strict/permissive mode correctness

## Reproducibility and Versioning
### Environment Pinning
All dependencies are version‑pinned in environment.yml.
Developers should avoid upgrading packages without validating:

- ML model behavior
- winsorization thresholds
- Pandas type coercion semantics
- audit event ordering

### Artifact Stability  
Audit artifacts include timestamps to ensure reproducibility and prevent overwriting.

***Notebook Determinism***
Notebooks assume:

- clean kernel
- consistent environment
- stable schema definitions

## Developer Responsibilities
Contributors should:

- maintain schema integrity
- preserve audit trail completeness
- ensure deterministic behavior across runs
- document new directives or event types
- update technical docs when extending pipeline logic

## License
MIT License.

