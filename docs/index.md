# Project Documentation Index
Welcome to the documentation hub for the Customer Transactions Cleaning Pipeline.
This index provides a structured entry point for all project materials, including architecture, workflow, schema definitions, audit trail behavior, and developer guides

Use this page as your navigation center
Each section below should link to its corresponding document

## 1. QuickStart Notebook
The 00_quickstart.ipynb notebook provides a minimal, end‑to‑end demonstration of running the cleaning pipeline on a sample dataset and viewing the generated audit artifacts.

- [Quick Start Notebook](quickstart.md) - start the end-to-end demo

## 1. Project Overview
The customer‑transaction‑cleaning project provides a production‑grade, schema‑driven data‑cleaning engine designed for real‑world retail and commerce datasets

- [Project Overview](project_overview.md) - global layout of the project

## 2. Technical Reference Guide
This document provides operational and development guidance for engineers working on the Customer Transaction Cleaning Pipeline. It supplements the Project Overview by focusing exclusively on development workflow, environment behavior, extension patterns, testing, and reproducibility

- [Technical Reference Guide](technical_reference_guide.md) - key: separation of concerns

## 3. Schema Reference
Definitions for all schema directives, column types, constraints, nullability rules, imputation strategies, and business logic.

- [Schema Reference](schema_reference.md) - schema usage and integration

## 4. Audit Trail
Structured event logging system capturing validation, transformation, imputation, and record‑level actions with full traceability.

- [Audit Trail System](audit_trail.md) — tracks all actions and row transformations

## 5. Imputation Strategy
Detailed explanation of numeric and ML‑based categorical imputation, including RandomForest workflow, ordering, and schema configuration.

- [Imputation Strategy](imputation_strategy.md) — numeric and ML‑based imputation logic

## 6. Project Structure
Description of the repository layout, directories, configuration files, notebooks, and artifact locations.

- [Project Structure](project_structure.md) — repository architecture

## 7. Quickstart & Usage
Instructions for running the pipeline, switching datasets, updating schemas, and generating audit artifacts.

- [Quidkstart Notebook](quickstart.md) - Quick start to running the pipeline

## 8. Contributing
Guidelines for extending the pipeline, adding new schema directives, implementing new audit events, or enhancing imputation logic.

(Add link to contributing.md if you create one)

## 9. License 
- [MIT License](../LICENSE) - full use license
