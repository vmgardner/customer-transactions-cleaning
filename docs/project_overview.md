# Customer Transactions Cleaning Pipeline  
# Project Overview

Notebook: Cleaning Pipeline Demo  
Author: Veronica Gardner  
Project: customer-transaction-cleaning  

**Purpose:**    
The customer‑transaction‑cleaning project provides a production‑grade, schema‑driven data‑cleaning engine designed for real‑world retail and commerce datasets. It demonstrates practical expertise in:

- data‑quality engineering

- declarative schema validation

- preprocessing automation

- statistical and ML‑based enrichment

- full auditability of all transformations

The system prepares raw transaction data for reliable exploratory analysis, dashboarding, and machine‑learning workflows.

## System Architecture  
***Cleaner***  

A configurable, schema‑driven engine that validates, cleans, enriches, and verifies customer‑transaction datasets. It supports strict and permissive modes for production or exploratory workflows.

***Audit Trail***  
A structured audit subsystem that records every validation, transformation, imputation, and record‑level action. It produces:

- audit_report.json — full event log
- audit_report_pretty.json - user friendly json

- audit_report.md — human‑readable narrative

- process_summary.md — concise counts of key actions

***File Manager***  
Handles all I/O operations, including saving cleaned datasets and audit artifacts. Strict mode produces a dedicated strict‑failure audit file.

***Configuration System***  
Behavior is controlled through declarative JSON configuration files:

- schema.json — column definitions, types, ranges, business rules, imputation settings

- file_configuration.json — input/output paths and audit file locations

- cleaner_config.json — strict/permissive mode toggle

This makes the pipeline plug‑and‑play for any CSV dataset.

## Key Features  
- Declarative schema validation

- Strict vs permissive processing modes

- IQR‑based winsorization for numeric outliers

- Median (configurable) imputation for numeric fields

- RandomForest‑based imputation for categorical fields

- Full audit trail with event categories and phases

- Process summary with before/after record counts

 - Single‑responsibility functional components

- Configurable file paths and dataset definitions

## Inputs and Outputs  
***Input***
- Raw CSV transaction dataset

- Schema configuration

- Cleaner configuration

- File path configuration

***Output from Cleaner.clean()***  

- Cleaned Dataframe
- AuditHandle containing paths to:

    -   audit_report.json
    -   audit_report_pretty.json

    -   audit_report.md

    -   process_summary.md


## Configuration Files 
***schema Configuration - schema.json***
Defines:

- column types

- ranges and constraints

- business rules

- nullability actions

- imputation strategies

- feature lists for ML models

- dataset unique identifier (unique_id)  

***File Configuration - file_config.json***
Defines:

- input/output directories

- audit report locations

- strict‑failure audit path

- schema and cleaner config paths

***Cleaner Configuration - cleaner_config.json***  
Controls strict/permissive behavior:
```
{
  "cleaner": {
    "strict_mode": false
    }
}
```  

## Demo Dataset Fields  
- transaction_id — unique transaction identifier

- customer_id — customer identifier

- amount — purchase amount

- product_category — product grouping

- region — retail region

- timestamp — transaction timestamp

## Cleaning Pipeline 
The pipeline follows a validate → clean → enrich → verify methodology.

***Validate***  
- required column checks

- type validation

- category validation

- numeric and range validation

- datetime validation

- nullability enforcement

***Clean***  
- column normalization

- duplicate removal

- categorical normalization

- timestamp conversion

- winsorization of numeric outliers

***Enrich***
- median imputation for numeric fields

- RandomForest imputation for:

- region

- product_category (using imputed region)

***Verify***
- re‑validatio nof critical fields

- generation of audit trail and process summary

## Record Removal Rules
Records are dropped when:

- both region and product_category are missing

- schema 'Required' is true and null value in data

- timestamp is null

- duplicate unique_id values exist

- schema specifies nullable_action = drop

## Strict vs Permissive Modes  
***strict Mode***  
- Fail‑fast behavior

- No cleaned dataset is produced

- If possible a strict‑failure audit file is produced

- Partial audit events are preserved up to the point of failure

- Critical schema violations raise exceptions immediately

***Permissive Mode***
- Warnings instead of exceptions
- Coerced to null for nullable_validation processing

- Non‑critical violations handled according to schema rules

- Partial results allowed

## Concise Summary
A production‑grade, schema‑driven cleaning pipeline for customer‑transaction data featuring:

- reliable preprocessing for analytics and ML

- full auditability of all transformations

- ML‑based enrichment for categorical fields

- robust validation and record‑removal rules

- configurable strict/permissive modes

 - plug‑and‑play configuration for any CSV dataset