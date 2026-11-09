# Using 00_quickstart.ipynb
The 00_quickstart.ipynb notebook provides a minimal, end‑to‑end demonstration of running the cleaning pipeline on a sample dataset and viewing the generated audit artifacts.

## Load the sample dataset
The notebook reads the default CSV:
```
../data/raw/synthetic_transactions.csv
```
This allows you to inspect the raw structure before cleaning.

## Run Notebook Cells in Order  
The 00_quickstart.ipynb notebook is designed to be executed top‑to‑bottom without skipping cells.
Each cell depends on the output of the previous one:

***cell 1 - Setup and Import***  
The first cell imports the necessary files for a successful pipeline execution. Also ensure paths and logiing is ready for use  

***cell 2 - Load the dataset***  
Creates the initial DataFrame (df) by populating it from the csv file stipulated in the file path. 

***cell 3 - Clean the pipeline***  
Produces df_clean and the populated audit trail object.
Displays memory usage and lengths of original and cleaned dataframes 

***cell 4 - Display audit artifacts***  
Uses paths generated during the cleaning step.

***cell 5 - (Optional) Save cleaned output*** 
Requires df_clean from the cleaning step.

Running cells out of order will result in missing variables or incomplete artifacts.

For a clean, reproducible run, always execute the notebook sequentially from the first cell to the last.

## The cleaning pipeline
The notebook initializes the DataCleaner and executes the full cleaning process:
```
cleaner = DataCleaner()
df_clean, audit = cleaner.clean(df)
```
This performs:
- schema validation
- type coercion
- winsorization
- numeric imputation
- ML categorical imputation
- record removal
- audit trail generation     

Memory usage and row counts are printed for quick comparison  

## View audit artifacts
After cleaning, the notebook will display links to all generated audit artifacts:

- Audit JSON
- Pretty JSON
- Markdown audit report
- Process summary

These links allow you to open the artifacts directly in JupyterLab or GitHub.

## (Optional) Save the cleaned dataset
The notebook includes an optional cell to write the cleaned output:
```
df_clean.to_csv('output.csv', index=False)
```

### Using Your Own Datafile (Plug-and-Play)
The pipeline is fully configuration‑driven execpt for the intial csv file provided by the user.  Two easy steps to clean a new datafile:  Update the schema and change the name of the output file.

To configure a new dataset for the cleaning process click the link below for step by step instructions

 **[Switching Datafiles](../README.md#using-your-own-datafile)** 

### Run the Pipeline Normally
Once the file path and schema are updated, follow the steps in the '_00_quickstart', to run the cleaner process and generate the audit artifacts

The pipeline will automatically:

- validate the new dataset
- apply the schema rules
- perform numeric and ML imputation
- generate audit artifacts
- produce a cleaned DataFrame

### View Audit Artifacts
The notebook displays links to:

- Audit JSON
- Pretty JSON
- Markdown audit report
- Process summary

These artifacts appear under:
```
audit_reports/
```
***Optional: Save Cleaned Output***
You may save the cleaned dataset to a directory of your choosing:
```
df_clean.to_csv('output.csv', index=False)
```
Update the path as needed


