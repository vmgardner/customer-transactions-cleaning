
import os
import logging
from datetime import datetime

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

from src.utilities import StrictModeError
import src.config_manager as config_manager
import src.file_manager as file_manager
import src.audit_trail as audit_trail

#####################################################################################
#   This module demonstrate the full cleaning pipeline with schema and data validation,
#   winsorization, categorical normalization, and ML-based imputation
#####################################################################################

# ---------------------------------------------------------------------------------------------------
# Logging Configuration signal versions.  most data logging has been repalced with autit_trail object 
# StrictModeError id still implemented thoughtout the cleaning process 
# ----------------------------------------------------------------------------------------------------
import logging

logger = logging.getLogger(__name__)

CLEANER_VERSION = "1.0"
__version__ = CLEANER_VERSION

def log_startup():
    logger.info(f"CLEANER VERSION {CLEANER_VERSION} LOADED")

class DataCleaner():
    # ------------------------------------------------------------
    #   Constructor with schema, and summary definition
    # ------------------------------------------------------------
    def __init__(self, schema=None):
            self.schema = schema

    def _init_process_summary(self):
            return {
            "validation": {
                "original_nulls": 0,
                "rows_dropped": 0,
                "invalid_numerics":0,
                "invalid_booleans":0,
                "invalid_strings":0,
                "invalid_categories": 0,
                "invalid_datetime": 0,
                "invalid_datetime_range": 0,
                "invalid_numeric_range": 0,
                "values_nulled": 0,
                "duplicate_records": 0
            },
            "transformation": {
                "winsorized_columns": 0,
                "winsorized_values": 0,
            },
            "imputation": {} }

    # -----------------------------------------------------------------
    #   cleaner Demo  Entry point to the cleaner
    #   public facing method - Start of the clener process
    # -----------------------------------------------------------------
    def clean(self, df: pd.DataFrame) -> tuple[pd.DataFrame, file_manager.AuditHandle]:

        # copy made for df comparison 
        copy_df = df.copy()

        # read pathing info for all file i/o
        file_cfg = config_manager.load_file_config()

        # get the cleaner config information  attributes strict_mode
        cleaner_cfg = config_manager.load_cleaner_config(file_cfg)

        # schema: must match incomring data structure - drives cleaning process
        schema = config_manager.load_schema(file_cfg)

        # create the audit_trail object to hold all cleaning artifacts and events
        audit_trail_obj = audit_trail.AuditTrail(schema)

        # sets unique_id column for the incoming dataset
        audit_trail_obj.unique_id = self._set_unique_id(schema, audit_trail_obj)

        # read the strict or permissive toggle
        strict = cleaner_cfg["cleaner"]["strict_mode"] 

        try:
            df_clean = self.clean_dataframe(df,
                                       schema,
                                       strict, 
                                       audit_trail_obj)
        except StrictModeError as e:
            raise e

        # prepare the datetimes for the df comparison
        original_df = self.normalize_datetime_columns(copy_df, schema)

        #  stores both dataframe references as instance attributes.
        self.set_dataframes(original_df, df_clean)  
        # compare original df against clean dg - add comparison artifact to the audit_trail_obj
        self.compute_comparison(audit_trail_obj, schema)
        
        #  Save the cleaned dataset
        file_manager.save_cleaned_dataset(df_clean, audit_trail_obj, file_cfg)

        # generates the output autidt reports and save to i/o 
        # audit_hande holds the full paths to the saved audit files
        audit_handle = file_manager.save_audit_reports(audit_trail_obj, file_cfg)

        return df_clean, audit_handle

    # -------------------------------------------------------------------
    #   clean_dataframe: main driver of normalize, validate, inpute
    # -------------------------------------------------------------------
    def clean_dataframe(self, df, schema, strict, audit_trail_obj):
        # Phase 1: Validate & clean all columns
        # Phase 2: Impute after all columns are fully cleaned  

        summary = self._init_process_summary()
        audit_trail_obj.record_initial_stats(df)

        # Validate Column existence- throw fatal error if required col missing
        self._verify_required_column_exists(df, schema, strict, audit_trail_obj)
        # Remove non-required fields from the cleaning process
        df = self._remove_non_required_columns(df, schema, strict, audit_trail_obj)
        # remove rows with duplicated unique_ids
        df = self._remove_unique_id_duplicates( df, audit_trail_obj, summary)
        # strip, lower, standardize 
        df = self._normalize_cols(df)
        # strip and lower
        df = self._normalize_string_values(df, schema)
        # start of the main validation process
        df = self._validate_columns(df, schema, strict, audit_trail_obj, summary)
        # pairwise dependency rule, drop if rull dependent values
        df = self._drop_unrecoverable_ml_pairs(df, schema, audit_trail_obj, summary)
        # orchastrates the imputation processes
        df = self._impute_columns(df,schema,strict,audit_trail_obj, summary)
        # i don't know
        #self._finalize(df)

        audit_trail_obj.record_final_stats(df)
        audit_trail_obj.record_summary(summary)  # add summary to audit object
        
        return df

    # ---------------------------------------------------------
    #   Set the audit_trail_obj.Unique_id = unique_id specified in the schema 
    #   always strict mode - Cleaner dependency on the set unique_id
    # ---------------------------------------------------------
    def _set_unique_id(self, schema, audit_trail_obj):

        audit_trail_obj.record_step("_set_unique_id")

        # always strict mode only 
        unique_id = schema["schema"].get("unique_id")

        if unique_id is None:
            audit_trail_obj.record_event (
                event = "business_key_validation",
                phase = "_set_unique_id",
                action_type = "validate",
                message = f"No unique_id found in schema - fatal error due to cleaner dependency " )
            
            self._handle_strict_failure(audit_trail_obj)
            raise StrictModeError (f"No unique_id is set for incoming dataset - fatal error" )

        columns = schema.get("schema", {}).get("columns", {})
        if unique_id not in columns:
            audit_trail_obj.record_event (
                event = "business_key_validation",
                phase = "_set_unique_id",
                action_type = "validate",
                message=f"No column matches the name of the unique_id - fatal error" )
            
            self._handle_strict_failure(audit_trail_obj)
            raise StrictModeError (f"No column matches the name of the unique_id, {unique_id}, - fatal error")
    
        return unique_id

    # -------------------------------------------------------------------
    #   Phase 1 - _validate_columns is driver of all _validate methods and is
    #       the entirety of the validate phase
    # -------------------------------------------------------------------
    def _validate_columns(self, df, schema, strict, audit_trail_obj, summary):

        audit_trail_obj.record_step("begin_validation_phase")

        columns = schema["schema"]["columns"]
        for col, rules in columns.items():            
            audit_trail_obj.record_column_start(col)

            #  Type validation; if invalid types then null the values    
            df = self._validate_type(df, col, rules, strict, audit_trail_obj, summary)
            # ensure category values allowed, drop records that do not apply
            df = self._validate_category_values(df, col, rules, strict, audit_trail_obj, summary)
            # ensure datetime ranges are within acceptable limits
            df = self._validate_datetime_range(df, col, rules, strict, audit_trail_obj, summary)
            # ensure numeric types are within acceptable Numeric ranges
            df = self._validate_numeric_range(df, col, rules, strict, audit_trail_obj, summary)
            # Nullability:  check the nullale_action - drop or keep nulss
            df = self._validate_nullable_values(df, col, rules, strict, audit_trail_obj, summary)
            # Winsorization (numeric only)
            df = self._winsorize(df, col, rules, strict, audit_trail_obj, summary)

            audit_trail_obj.record_column_end(col)

        audit_trail_obj.record_step("end_validation_phase")

        return df

    # ---------------------------------------------------------
    # PHASE 2 — IMPUTE (after all columns are clean) 
    #   executioner for the entirety of the impute phase 
    # ---------------------------------------------------------
    def _impute_columns(self, df, schema, strict, audit_trail_obj, summary):

        audit_trail_obj.record_step("begin_imputation_phase")

        columns = schema["schema"]["columns"]

        # Select columns that have ANY imputation enabled
        impute_cols = {
            name: spec
            for name, spec in columns.items()
            if (
                spec.get("impute_simple", {}).get("enabled")
                or spec.get("impute_ml", {}).get("enabled")
            )
        }

        for col, rules in impute_cols.items():

            audit_trail_obj.record_column_start(col)

            # Simple numeric imputation
            if rules.get("impute_simple", {}).get("enabled"):
                df = self._impute_numeric(df, col, rules, strict, audit_trail_obj, summary)

            # ML imputation
            elif rules.get("impute_ml", {}).get("enabled"):
                df = self._impute_ml(df, col, rules, strict, audit_trail_obj, summary)

            audit_trail_obj.record_column_end(col)

        audit_trail_obj.record_step("end_imputation_phase")

        return df

    # ----------------------------------------------------------------------
    #   Ensure Required Columns  - if not hard exist
    # ----------------------------------------------------------------------
    def _verify_required_column_exists(self, df, schema, strict, audit_trail_obj):
        # always strict 

        audit_trail_obj.record_step("_verify_required_column_exists")

        columns = schema["schema"]["columns"]

        for col, rules in columns.items():
            if df.columns.isin([col]).any():
                continue

            # check if column required if not error out
            required = rules.get("required", False)
            if required:
                message = f"Required column missing in strict mode: '{col}'"
                audit_trail_obj.record_event(
                    event = "required_column_validation",
                    phase = "verify_required_column_exists",
                    action_type = "validate",
                    column = col,
                    message= message,
                    details={
                        "column count": len(df.columns),
                        "columns:" : col } )

                # handle the fatal error and raise to dall
                self._handle_strict_failure(audit_trail_obj)
                raise StrictModeError(message, details={"required": required})

        return True

    #---------------------------------------------------------------------- 
    #   Remove non-required columns from the dataframe,
    # ----------------------------------------------------------------------
    def _remove_non_required_columns(self, df, schema, strict, audit_trail_obj):

        audit_trail_obj.record_step("_remove_non_required_columns")

        columns = schema["schema"]["columns"]
        required_cols = [col for col, rules in columns.items() if rules.get("required", False)]
        non_required_cols = [col for col in df.columns if col not in required_cols]

        if non_required_cols:
            if strict:
                strict_msg = (
                    f"Non-required column(s) exists in data: {non_required_cols}, strict mode " )
            
                audit_trail_obj.record_event(
                    event = "remove_nonrequired_columns",
                    phase = "remove_non_required_columns",
                    action_type = "drop",
                    message = strict_msg,
                    details={"column count": len(non_required_cols) } )
                
                # handle the fatal error and raise to dall
                self._handle_strict_failure(audit_trail_obj)
                raise StrictModeError (strict_msg)

            # Permissive mode
            audit_trail_obj.record_event(
                event = "schema_validation",
                phase = "_remove_non_required_columns",
                action_type = "drop",
                message = f"Non-required columns will be dropped - permissive mode:",
                details = {"column count": len(non_required_cols),
                        "non-required-columns:" : non_required_cols } )
            # Permissive mode → drop non-required columns
            df.drop(columns=non_required_cols, inplace=True)

        return df
    
    # -----------------------------------------------------------------------------------
    #   Individual Type validation:  All types will return df with invalid values 
    #  - coerced to null in permissive mode
    #  - strict mode will throw the StrictModeError
    # -----------------------------------------------------------------------------------
    def _validate_individual_type(self, df, col, expected_type, strict, summary, audit_trail_obj):

        series = df[col]

        # ---------------------------------------------------------
        # Shared pre‑coercion tracking
        # ---------------------------------------------------------
        original = series
        original_nulls = original.isna()
        original_nulls_count = original_nulls.sum()

        if original_nulls_count > 0:
            summary["validation"]["original_nulls"] += original_nulls_count
        
        strict_label = "unknown"
        # ---------------------------------------------------------
        # Type‑specific coercion
        # ---------------------------------------------------------
        if expected_type == "string":
            coerced = series.astype("string")
            event = "validate_type_string"
            invalid_summary_key = "invalid_strings"
            strict_label = "string"

        elif expected_type == "number":
            coerced = pd.to_numeric(series, errors="coerce")
            event = "validate_type_numeric"
            invalid_summary_key = "invalid_numerics"
            strict_label = "number"

        elif expected_type == "datetime":
            coerced = pd.to_datetime(series, errors="coerce")
            event = "validate_type_datetime"
            invalid_summary_key = "invalid_datetime"
            strict_label = "datetime"

        elif expected_type == "category":
            coerced = series.astype("string").astype("category")
            event = "validate_type_category"
            invalid_summary_key = "invalid_categories"
            strict_label = "category"

        elif expected_type == "boolean":
            affirmative = {"true", "t", "yes", "y", "1"}
            negatory   = {"false", "f", "no", "n", "0"}

            def _normalize_bool_value(v):
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    return pd.NA
                if isinstance(v, bool):
                    return v
                if isinstance(v, int):
                    return True if v == 1 else False if v == 0 else pd.NA
                if isinstance(v, str):
                    s = v.strip().lower()
                    if s in affirmative: return True
                    if s in negatory: return False
                    return pd.NA
                return pd.NA

            coerced = series.map(_normalize_bool_value).astype("boolean")
            event = "validate_type_boolean"
            invalid_summary_key = "invalid_booleans"
            strict_label = "boolean"
        # no know type
        else:
            message=f"Type validation failed for column '{col}'. Expected {strict_label} - strict mode"

            audit_trail_obj.record_event(
                event = event,
                phase = "_validate_individual_type",
                action = "validate",
                column=col,
                message = message)
            
            self._handle_strict_failure(audit_trail_obj)
            raise StrictModeError(f"Unknown expected_type: {expected_type} ")

        # ---------------------------------------------------------
        # Shared post‑coercion tracking
        # ---------------------------------------------------------
        coerced_nulls = coerced.isna()
        coerced_to_null_mask = coerced_nulls & ~original_nulls
        coerced_to_null_count = coerced_to_null_mask.sum()

        invalid_mask = coerced_nulls

        if invalid_mask.any():
            summary["validation"][invalid_summary_key] += invalid_mask.sum()

            unique_ids = df.loc[invalid_mask, audit_trail_obj.unique_id].tolist()
            row_indices = df.loc[invalid_mask].index.tolist()
            rows = df.loc[invalid_mask].to_dict(orient="records")

            # ---------------------------------------------------------
            # Strict mode branch
            # ---------------------------------------------------------
            if strict:
                strict_msg = (
                    f"Type validation found null values in column '{col}'. "
                    f"Expected {strict_label} - strict mode"
                )

                audit_trail_obj.record_event(
                    event = event,
                    phase ="_validate_individual_type",
                    action_type = "coerce",
                    column=col,
                    row_indices=row_indices,
                    unique_ids=unique_ids,
                    rows=rows,
                    details={
                        "coerced_to_null_count": coerced_to_null_count,
                        "original_nulls_count": original_nulls_count
                    },
                    message=strict_msg
                )

                self._handle_strict_failure(audit_trail_obj)
                
                raise StrictModeError(
                    strict_msg,
                    details={"invalid_row_indices": row_indices}
                )

            # ---------------------------------------------------------
            # Permissive mode branch
            # ---------------------------------------------------------
            permissive_msg = (
                f"Type validation found null values in column '{col}'. "
                f"Expected {strict_label} - permissive mode"
            )

            audit_trail_obj.record_event(
                event= event,
                phase= "_validate_individual_type",
                action_type = "coerce",
                column=col,
                row_indices=row_indices,
                unique_ids=unique_ids,
                rows=rows,
                details={
                    "coerced_to_null_count": coerced_to_null_count,
                    "original_nulls_count": original_nulls_count
                },
                message=permissive_msg
            )

        summary["validation"]["values_nulled"] += coerced_to_null_count

        df[col] = coerced
        return df

    # -----------------------------------------------------------------------------------
    #  Type validation:  ensure valid type from schema 
    #   call the _validate_individual_type
    # -----------------------------------------------------------------------------------
    def _validate_type(self, df, col, rules, strict, audit_trail_obj, summary):
        # compare column type to schema type for each column:
        #  strict mode - throw error 
        #  permissive mode - coerce to string 

        audit_trail_obj.record_step("_validate_type")

        series = df[col]

        expected_type = rules.get("type")
        if expected_type is None:

            if strict:    
                strict_msg = (
                    f"Column Type is Unknown for '{col}',  strict mode - application fail" )
                
                audit_trail_obj.record_event( 
                    event = "type_validation",
                    phase = "_validate_type", 
                    action_type="validate",
                    column = col, 
                    message = strict_msg  )

                # Strict failure handling
                self._handle_strict_failure(audit_trail_obj)
                raise StrictModeError(strict_msg)

            else:
                coerced = series.astype("string")
                example_values = coerced.sample(
                    n=min(3, len(coerced)),
                    replace=False
                    ).tolist()

                # Permissive mode message
                audit_trail_obj.record_event ( 
                    event = "type_validation",
                    phase = "_validate_type",
                    action_type = "coerce",
                    column = col, 
                    message = f"examples data from unknown type after coersion to string, '{example_values}' ",
                    details = { f"Column Type is Unknown for '{col}',  permissive mode - coerce '{col}' to string "} )
                
                df[col] = coerced
                expected_type = "string" 

        df = self._validate_individual_type(df, col, expected_type, strict, summary, audit_trail_obj)

        return df

    # ----------------------------------------------------------------------
    #   Nullability validation checks 'nullable' rule - executes  nullable_action: 
    #       action = drop then drop row, action = keep leave the null value
    # ----------------------------------------------------------------------
    def _validate_nullable_values(self, df, col, rules, strict, audit_trail_obj, summary):

        # Identify null rows - if 0 null rows early return
        null_mask = df[col].isna()
        if not null_mask.any():
            return df

        audit_trail_obj.record_step("_validate_nullable_values")

        # check nullable flag 
        nullable = rules.get("nullable")
        if nullable:   # keep the null values for later processing
            return df

       
        # Extract audit fields
        unique_ids = df.loc[null_mask, audit_trail_obj.unique_id].tolist()
        row_indices = df.loc[null_mask].index.tolist()
        rows = df.loc[null_mask].to_dict(orient="records")
        invalid_count = len(row_indices)

        # STRICT MODE → fatal
        if strict:
            strict_msg = (
                f"Nulls found in non-nullable column '{col}' - strict mode")


            audit_trail_obj.record_event(
                event="null_validation",
                phase="_validate_nullable_values",
                action_type = "validate",
                column=col,
                row_indices=row_indices,
                unique_ids=unique_ids,
                rows=rows,
                details={"invalid_count": invalid_count},
                message=strict_msg )

            self._handle_strict_failure(audit_trail_obj)

            raise StrictModeError(
               strict_msg,
                details={"invalid_row_indices": row_indices} )

        # PERMISSIVE MODE
        # nullable_action determines what to do if a null value for that column
        nullable_action = rules.get("nullable_action")
        if nullable_action == "drop":
            permissive_msg = (
                f"Records will be dropped due to null values found in '{col}' and nullable_action = '{nullable_action}' - permissive mode" )

            # Identify rows that WILL be removed
            removed_mask = null_mask
            removed_rows = df.loc[removed_mask]

            audit_trail_obj.record_event(
                event="null_validation",
                phase="_validate_nullable_values",
                action_type = "drop",
                column=col,
                row_indices=row_indices,
                unique_ids=unique_ids,
                rows=rows,
                details={"invalid_count": invalid_count},
                message=permissive_msg,
                dropped_rows = {
                    "removed_row_indices": row_indices,
                    "removed_unique_ids": unique_ids,
                    "removed_rows": removed_rows } )

            dropped_count = null_mask.sum()
            summary["validation"]["rows_dropped"] += dropped_count

            df = df.loc[~null_mask]
            return df

        # nullable_action != "drop" → leave nulls for future processing
        permissive_msg = (
            f"Null values found in '{col}' - permissive mode: left for future processing" )


        audit_trail_obj.record_event(
            event="null_validation",
            phase="validate_nullable_values_permissive",
            action_type = "validate",
            column=col,
            row_indices=row_indices,
            unique_ids=unique_ids,
            rows=rows,
            details={"invalid_count": invalid_count},
            message=permissive_msg )

        return df
        
    # ----------------------------------------------------------------------
    #   validate category values against schema allowed list
    #       if not in list update df with null value 
    # ----------------------------------------------------------------------
    def _validate_category_values(self, df, col, rules, strict, audit_trail_obj, summary):

        if rules.get("type") != "category":
            return df

        audit_trail_obj.record_step("_validate_category_values")

        # Count original nulls
        original_null_count = df[col].isna().sum()

        # Identify invalid category values
        allowed = set(rules.get("allowed", []))
        invalid_mask = df[col].notna() & ~df[col].isin(allowed)
        invalid_count = invalid_mask.sum()

        # No violations → done
        if invalid_count == 0:
            return df

        # Update summary
        summary["validation"]["invalid_categories"] += invalid_count

        unique_ids = df.loc[invalid_mask, audit_trail_obj.unique_id].tolist()
        row_indices = df.loc[invalid_mask].index.tolist()
        rows = df.loc[invalid_mask].to_dict(orient="records")

        # STRICT MODE → fatal
        if strict:
            strict_msg = f"Invalid category in '{col}' - strict mode"

            audit_trail_obj.record_event(
                event="category_validation",
                phase="_validate_category_values",
                action_type = "validate",
                column=col,
                row_indices=row_indices,
                unique_ids=unique_ids,
                rows=rows,
                details={"invalid_count": invalid_count},
                message=strict_msg
            )

            self._handle_strict_failure(audit_trail_obj)

            raise StrictModeError(
                strict_msg,
                details={"column": col, "invalid_row_indices": row_indices}
            )

        # PERMISSIVE MODE → null invalid values
        permissive_msg = (
            f"Null the values that have invalid category in '{col}' - permissive mode"
        )

        audit_trail_obj.record_event(
            event="validate_category_values",
            phase="_validate_category_values",
            action_type = "coerce",
            column=col,
            row_indices=row_indices,
            unique_ids=unique_ids,
            rows=rows,
            details={"invalid_count": invalid_count},
            message=permissive_msg
        )

        # Null the invalid values
        df.loc[invalid_mask, col] = None

        # Count values intentionally nulled
        final_nulls = df[col].isna().sum()
        intentional_nulled = final_nulls - original_null_count
        summary["validation"]["values_nulled"] += intentional_nulled

        return df

    # ----------------------------------------------------------------------
    # 7. Numeric min/max
    # ----------------------------------------------------------------------
    def _validate_numeric_range(self, df, col, rules, strict, audit_trail_obj, summary):
    # - Strict mode: fatal if any value is outside [min, max]
    # - Permissive mode: log and drop invalid rows

        # Only apply to numeric columns
        if rules.get("type") != "number":
            return df

        audit_trail_obj.record_step("_validate_numeric_range")

        min_val = rules.get("min")
        max_val = rules.get("max")

        # If no range constraints, nothing to do
        if min_val is None and max_val is None:
            return df

        series = df[col]

        # Build mask of invalid values
        invalid_mask = pd.Series(False, index=df.index)

        if min_val is not None:
            invalid_mask |= series < min_val

        if max_val is not None:
            invalid_mask |= series > max_val

        invalid_rows = df.loc[invalid_mask]
        invalid_count = len(invalid_rows)

        # No violations → done
        if invalid_count == 0:
            return df

        # Update summary
        summary["validation"]["invalid_numeric_range"] += invalid_count

        unique_ids = df.loc[invalid_mask, audit_trail_obj.unique_id].tolist()    
        row_indices = invalid_rows.index.tolist()
        rows = invalid_rows.to_dict(orient="records")

        # STRICT MODE → fatal
        if strict:
            strict_msg = (
                f"Numeric out of range in '{col}'. strict mode - application fail"
            )

            audit_trail_obj.record_event(
                event="range_validation",
                phase="_validate_numeric_range",
                action_type = "validate",
                column=col,
                row_indices=row_indices,
                unique_ids=unique_ids,
                rows=rows,
                details={
                    "invalid_count": invalid_count,
                    "min": min_val,
                    "max": max_val
                },
                message=strict_msg
            )

            self._handle_strict_failure(audit_trail_obj)
            raise StrictModeError(
               strict_msg,
                details={
                    "invalid_count": invalid_count,
                    "min": min_val,
                    "max": max_val,
                    "indices": row_indices
                }
            )

        # PERMISSIVE MODE → drop rows
        permissive_msg = (
            f"Drop rows with out of range values in '{col}' - permissive mode:")

        audit_trail_obj.record_event(
            event="range_validation",
            phase="_validate_numeric_range",
            action_type = "drop",
            column=col,
            row_indices=row_indices,
            unique_ids=unique_ids,
            rows=rows,
             message=permissive_msg,
            details={
                "invalid_count": invalid_count,
                "min": min_val,
                "max": max_val
            },
            dropped_rows = {
                "removed_row_indices": row_indices,
                "removed_unique_ids": unique_ids,
                "removed_rows": rows } )
    

        # Drop invalid rows
        df = df[~invalid_mask]
        dropped_count = invalid_mask.sum()
        summary["validation"]["rows_dropped"] += dropped_count

        return df

    # ----------------------------------------------------------------------
    # 8. Datetime min/max
    # ----------------------------------------------------------------------
    def _validate_datetime_range(self, df, col, rules, strict, audit_trail_obj, summary):

        if rules.get("type") != "datetime":
            return df

        audit_trail_obj.record_step("_validate_datetime")
            
        min_date = rules.get("min_date")
        max_date = rules.get("max_date")

        if min_date is None and max_date is None:
            return df

        temp = df[col] 
        invalid_mask = pd.Series(False, index=df.index)

        if min_date is not None:
            min_dt = pd.to_datetime(min_date)
            invalid_mask |= temp < min_dt

        if max_date is not None:
            max_dt = pd.to_datetime(max_date)
            invalid_mask |= temp > max_dt

        invalid_rows = df[invalid_mask]
        if invalid_rows.empty:
            return df

        invalid_count = len(invalid_rows)
        if invalid_count > 0:
            summary["validation"]["invalid_datetime_range"] += invalid_mask.sum()

            unique_ids = df.loc[invalid_mask, audit_trail_obj.unique_id].tolist()
            row_indices = df.loc[invalid_mask].index.tolist(),
            rows = df.loc[invalid_mask].to_dict(orient="records"), 

            if strict:
                message = f"Datetime range violation in column '{col}', strict mode - application fail" 

                audit_trail_obj.record_event(
                    event = "datetime_validation",
                    phase ="_validate_datetime_range",
                    action_type = "validate",
                    column = col,
                    row_indices = row_indices,
                    unique_ids = unique_ids,
                    rows = rows,
                    message = message,
                    details ={"invalid_count": invalid_count,
                            "min_date": min_date,
                            "max_date": max_date,
                            "row_indices": row_indices})
                
                self._handle_strict_failure(audit_trail_obj)
                raise StrictModeError( message,
                    details={f"invalid_count: {invalid_count}, invalid_indices: {row_indices}"})

            # permissive → drop invalid rows
            message = f"Drop rows due to datetime range violations in '{col}' - permissive mode)"

            audit_trail_obj.record_event(
                event = "datetime validation",
                phase="_validate_datetime_range",
                action_type = "drop",
                column=col,
                row_indices = row_indices,
                unique_ids = unique_ids,
                rows = rows,
                message = message,
                details={"invalid_count": invalid_count,
                        "min_date": min_date,
                        "max_date": max_date,
                        "rows": row_indices },
                dropped_rows = {
                    "removed_row_indices": row_indices,
                    "removed_unique_ids": unique_ids,
                    "removed_rows": rows })
            
            dropped_count = invalid_mask.sum()
            summary["validation"]["rows_dropped"] += dropped_count
            df = df[~invalid_mask]
            
        # ALWAYS assign back
        df[col] = temp

        return df
  
    # -------------------------------------------------------
    # Winsorize numeric outliers
    # -------------------------------------------------------
    def _winsorize(self, df, col, rules, strict, audit_trail_obj, summary):
        # Winsorize numeric columns based on schema rules.
        # Always permissive: clip values to computed bounds.
        # Hard failures (strict + permissive): invalid schema (missing bounds, non-numeric, inverted quantiles).
        
        # Only apply to numeric columns with winsorization enabled
        if rules.get("type") != "number":
            return df

        audit_trail_obj.record_step("_winsorize")

        wins = rules.get("winsorize")
        if not wins:
            return df

        series = df[col]

        # ---------------------------------------------------------
        # Determine quantile bounds (schema-driven)
        # ---------------------------------------------------------
        if isinstance(wins, dict):
            lower_q = wins.get("lower", 0.05)
            upper_q = wins.get("upper", 0.95)
        else:
            lower_q, upper_q = 0.05, 0.95

        # ---------------------------------------------------------
        # Hard-fail schema validation (strict + permissive)
        # ---------------------------------------------------------
        if lower_q is None or upper_q is None:
            strict_msg = f"Winsorization quantiles missing for '{col}'"
            audit_trail_obj.record_event(
                event="winsorization",
                phase="_winsorize",
                action_type  = "transform",
                column=col,
                message=strict_msg,
                details={"lower_q": lower_q, "upper_q": upper_q}
            )
            self._handle_strict_failure(audit_trail_obj)
            raise StrictModeError(strict_msg)

        if not isinstance(lower_q, (int, float)) or not isinstance(upper_q, (int, float)):
            strict_msg = f"Winsorization quantiles must be numeric for '{col}'"
            audit_trail_obj.record_event(
                event="winsorization",
                phase="_winsorize",
                action_type = "transform",
                column=col,
                message=strict_msg,
                details={"lower_q": lower_q, "upper_q": upper_q})
            
            self._handle_strict_failure(audit_trail_obj)
            raise StrictModeError(strict_msg)

        if lower_q < 0 or upper_q > 1:
            strict_msg = f"Winsorization quantiles out of range for '{col}'"
            audit_trail_obj.record_event(
                event="winsorization",
                phase="_winsorize",
                action_type = "transform",
                column=col,
                message=strict_msg,
                details={"lower_q": lower_q, "upper_q": upper_q})
            
            self._handle_strict_failure(audit_trail_obj)
            raise StrictModeError(strict_msg)

        if lower_q >= upper_q:
            strict_msg = f"Winsorization quantiles invalid (lower >= upper) for '{col}'"
            audit_trail_obj.record_event(
                event="winsorization",
                phase="_winsorize",
                action_type = "transform",
                column=col,
                message=strict_msg,
                details={"lower_q": lower_q, "upper_q": upper_q}
            )
            self._handle_strict_failure(audit_trail_obj)
            raise StrictModeError(strict_msg)

        # ---------------------------------------------------------
        # Compute numeric bounds
        # ---------------------------------------------------------
        lower_bound = series.quantile(lower_q)
        upper_bound = series.quantile(upper_q)

        if pd.isna(lower_bound) or pd.isna(upper_bound):
            strict_msg = f"Winsorization bounds could not be computed for '{col}'"
            audit_trail_obj.record_event(
                event="winsorization",
                phase="_winsorize",
                action_type = "transform",
                column=col,
                message=strict_msg,
                details={"lower_bound": lower_bound, "upper_bound": upper_bound}
            )
            self._handle_strict_failure(audit_trail_obj)
            raise StrictModeError(strict_msg)

        # ---------------------------------------------------------
        # Identify rows outside bounds
        # ---------------------------------------------------------
        out_of_bounds_mask = (series < lower_bound) | (series > upper_bound)
        out_of_bounds_rows = df[out_of_bounds_mask]

        # No winsorization needed
        if out_of_bounds_rows.empty:
            return df

        out_count = len(out_of_bounds_rows)

        summary["transformation"]["winsorized_columns"] += 1
        summary["transformation"]["winsorized_values"] += out_count

        # ---------------------------------------------------------
        # Shared audit variables
        # ---------------------------------------------------------
        unique_ids = df.loc[out_of_bounds_mask, audit_trail_obj.unique_id].tolist() 
        row_indices = df.loc[out_of_bounds_mask].index.tolist()
        rows = df.loc[out_of_bounds_mask].to_dict(orient="records")
        old_values = series[out_of_bounds_mask].tolist()

        # ---------------------------------------------------------
        # Permissive message
        # ---------------------------------------------------------
        permissive_msg = f"Winsorizing column '{col}' - permissive mode "

        # ---------------------------------------------------------
        # Audit event
        # ---------------------------------------------------------
        audit_trail_obj.record_event(
            event="winsorization",
            phase="_winsorize",
            action_type = "transform",
            column=col,
            row_indices=row_indices,
            unique_ids=unique_ids,
            rows=rows,
            message=permissive_msg,
            details={
                "old_values": old_values,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "winsorized_count": out_count } )

        # ---------------------------------------------------------
        # Perform winsorization
        # ---------------------------------------------------------
        df.loc[out_of_bounds_mask, col] = series.clip(lower_bound, upper_bound)

        return df

    # -----------------------------------------------------------------
    #   If required columns are missing in the ml features list then the row will be dropped. 
    #  ------------------------------------------------------------- 
    def _drop_unrecoverable_ml_pairs(self, df, schema, audit_trail_obj, summary):

        audit_trail_obj.record_step("_drop_unrecoverable_ml_pairs")

        columns = schema["schema"]["columns"]

        # Identify ML-imputed columns using the new schema format
        ml_columns = [
            col for col, rules in columns.items()
            if rules.get("impute_ml", {}).get("enabled") ]

        rows_to_drop = set()      # dedupe automatically
        dependency_pairs = []     # track which ML pairs triggered the drop

        # ---------------------------------------------------------
        # Identify ML dependency pairs where BOTH columns are null
        # ---------------------------------------------------------
        for col in ml_columns:
            rules = columns[col]
            features = rules.get("impute_ml", {}).get("features", [])

            # ML dependencies = features that are ALSO ML-imputed columns
            ml_dependencies = [f for f in features if f in ml_columns]

            for dep in ml_dependencies:
                mask = df[col].isna() & df[dep].isna()

                if mask.any():
                    indices = df.index[mask].tolist()
                    rows_to_drop.update(indices)
                    dependency_pairs.append((col, dep))

        # ---------------------------------------------------------
        # If no rows need to be dropped, exit early
        # ---------------------------------------------------------
        if not rows_to_drop:
            return df

        # ---------------------------------------------------------
        # Build shared audit variables
        # ---------------------------------------------------------
        drop_indices = list(rows_to_drop)
        dropped_rows = df.loc[drop_indices].to_dict(orient="records")
        unique_ids = df.loc[drop_indices, audit_trail_obj.unique_id].tolist() 

        # ---------------------------------------------------------
        # Audit event (schema_validation)
        # ---------------------------------------------------------
        audit_trail_obj.record_event(
            event="ml_dependency_violation",
            phase="__drop_unrecoverable_ml_pairs",
            action_type = "drop",
            column=None,   # not tied to a single column
            row_indices=drop_indices,
            unique_ids=unique_ids,
            rows=dropped_rows,
            message="Dropping rows with unrecoverable ML dependency pairs",
            details={
                "row_indices": drop_indices,
                "ml_dependency_pairs": dependency_pairs},
            dropped_rows = {
                "removed_row_indices": drop_indices,
                "removed_unique_ids": unique_ids,
                "removed_rows": dropped_rows })

        # ---------------------------------------------------------
        # Drop rows
        # ---------------------------------------------------------
        df.drop(drop_indices, inplace=True)

        # ---------------------------------------------------------
        # Update summary
        # ---------------------------------------------------------
        summary["validation"]["rows_dropped"] += len(drop_indices)

        return df

    #----------------------------------------------------------------------------------
    #   _impute_ml()  new generic method to replace hard-coded methods
    # ------------------------------------------------------------------------------
    def _impute_ml(self, df, col, rules, strict, audit_trail_obj, summary):
        # Generic ML imputer for any column using RandomForestClassifier (or other models later).
        # see schema

        impute_ml_cfg = rules.get("impute_ml")
        if not impute_ml_cfg or not impute_ml_cfg.get("enabled"):
            return df

        audit_trail_obj.record_step("_impute_ml")

        # Identify null rows
        null_mask = df[col].isna()
        if not null_mask.any():
            return df

        null_count = null_mask.sum()

        # Shared audit variables
        unique_ids = df.loc[null_mask, audit_trail_obj.unique_id].tolist()
        row_indices = df.loc[null_mask].index.tolist()
        rows = df.loc[null_mask].to_dict(orient="records")

        # ---------------------------------------------------------
        # STRICT MODE → fatal if any nulls exist
        # ---------------------------------------------------------
        if strict:
            strict_msg = f"Null values found in '{col}' — strict mode prohibits ML imputation"

            audit_trail_obj.record_event(
                event="imputation",
                phase=f"_impute_ml",
                action_type = "ml_imputation",
                column=col,
                row_indices=row_indices,
                unique_ids=unique_ids,
                rows=rows,
                message=strict_msg,
                details={"null_count": null_count}
            )

            self._handle_strict_failure(audit_trail_obj)
            raise StrictModeError(strict_msg)

        # ---------------------------------------------------------
        # PERMISSIVE MODE → ML imputation
        # ---------------------------------------------------------
        features = impute_ml_cfg.get("features", [])
        model_name = impute_ml_cfg.get("model", "RandomForestClassifier")

        # Training data (non-null target)
        X_train = df.loc[~null_mask, features]
        y_train = df.loc[~null_mask, col]

        # Missing data (null target)
        X_missing = df.loc[null_mask, features]

        # Guard: no training data → cannot impute
        if X_train.empty:
            strict_msg = f"Imputation failed: no training data available for '{col}'"

            audit_trail_obj.record_event(
                event="ml_imputation",
                phase=f"_impute_ml",
                action_type = "impute",
                column=col,
                row_indices=row_indices,
                unique_ids=unique_ids,
                rows=rows,
                message=strict_msg,
                details={"null_count": null_count}
            )

            self._handle_strict_failure(audit_trail_obj)
            raise StrictModeError(strict_msg)

        # Guard: no missing rows → nothing to impute
        if X_missing.empty:
            return df

        # ---------------------------------------------------------
        # ENCODING BLOCK
        # ---------------------------------------------------------
        X_train_encoded = X_train.copy()
        X_missing_encoded = X_missing.copy()

        for feature in features:

            # 1. Datetime → numeric
            if pd.api.types.is_datetime64_any_dtype(X_train[feature]):
                X_train_encoded[feature] = X_train[feature].astype("int64")
                X_missing_encoded[feature] = X_missing[feature].astype("int64")
                continue

            # 2. Numeric → leave as-is
            if pd.api.types.is_numeric_dtype(X_train[feature]):
                continue

            # 3. Encode non-numeric (string/category)
            le_feat = LabelEncoder()

            # Convert categorical columns to object before fillna.
            # Categorical dtypes may preserve pd.NA values that cause
            # LabelEncoder to fail with mixed NAType/string inputs.
            temp = X_train[feature].astype(object)
            temp = temp.fillna("__MISSING__") 
            temp = temp.astype(str)

            X_train_encoded[feature] = le_feat.fit_transform(temp)

            # Transform missing
            missing_vals = (X_missing[feature].astype(object).fillna("__MISSING__").astype(str))
                
            # missing_vals = X_missing[feature].astype(str)
            unseen_mask = ~missing_vals.isin(le_feat.classes_)

            if unseen_mask.any():
                le_feat.classes_ = np.append(le_feat.classes_, missing_vals[unseen_mask].unique())

            X_missing_encoded[feature] = le_feat.transform(missing_vals)

        # Encode target
        target_encoder = LabelEncoder()
        y_encoded = target_encoder.fit_transform(y_train.astype(str))

        # ---------------------------------------------------------
        # Model selection (currently only RF, but extensible)
        # ---------------------------------------------------------
        if model_name == "RandomForestClassifier":
            model = RandomForestClassifier(
                n_estimators=200,
                random_state=42,
                n_jobs=-1
            )
        else:
            raise ValueError(f"Unsupported ML model '{model_name}' for column '{col}'")

        model.fit(X_train_encoded, y_encoded)

        # Predict
        y_pred_encoded = model.predict(X_missing_encoded)
        y_pred = target_encoder.inverse_transform(y_pred_encoded)

        # ---------------------------------------------------------
        # Audit permissive imputation
        # ---------------------------------------------------------
        permissive_msg = f"Imputed null values in '{col}' using {model_name}"

        audit_trail_obj.record_event(
            event="ml_imputation",
            phase=f"_impute_ml",
            action_type = "impute",
            column=col,
            row_indices=row_indices,
            unique_ids=unique_ids,
            rows=rows,
            message=permissive_msg,
            details={
                "null_count": null_count,
                "predicted_values": y_pred.tolist(),
                "model": model_name,
                "features": features
            }
        )

        # Write back
        df.loc[null_mask, col] = y_pred
        summary["imputation"].setdefault(f"{col}_imputed", 0)
        summary["imputation"][f"{col}_imputed"] += null_count

        return df

    # -------------------------------------------------------
    # Impute numeric nulls (median)
    # -------------------------------------------------------
    def _impute_numeric(self, df, col, rules, strict, audit_trail_obj, summary):

        # Only apply to numeric columns
        if rules.get("type") != "number":
            return df

        simple_cfg = rules.get("impute_simple")
        if not simple_cfg or not simple_cfg.get("enabled"):
            return df

        audit_trail_obj.record_step("_impute_numeric")

        # Identify null rows
        series = df[col]
        null_mask = series.isna()

        # early out - No nulls → nothing to do
        if not null_mask.any():
            return df

        null_count = null_mask.sum()

        # Shared audit variables
        unique_ids = df.loc[null_mask, audit_trail_obj.unique_id].tolist()
        row_indices = df.loc[null_mask].index.tolist()
        rows = df.loc[null_mask].to_dict(orient="records")

        # ---------------------------------------------------------
        # STRICT MODE → fatal if any nulls exist
        # ---------------------------------------------------------
        if strict:
            strict_msg = f"Null values found in '{col}' — strict mode prohibits simple imputation"

            audit_trail_obj.record_event(
                event="simple_imputation",
                phase=f"_impute_numeric",
                action_type = "impute",
                column=col,
                row_indices=row_indices,
                unique_ids=unique_ids,
                rows=rows,
                message=strict_msg,
                details={"null_count": null_count}
            )

            self._handle_strict_failure(audit_trail_obj)
            raise StrictModeError(strict_msg)

        # ---------------------------------------------------------
        # PERMISSIVE MODE → compute replacement value
        # ---------------------------------------------------------
        strategy = simple_cfg.get("strategy", "median")

        if strategy == "median":
            replacement = series.median()
        elif strategy == "mean":
            replacement = series.mean()
        elif strategy == "mode":
            replacement = series.mode().iloc[0] if not series.mode().empty else None
        elif strategy == "zero":
            replacement = 0
        elif strategy == "min":
            replacement = series.min()
        elif strategy == "max":
            replacement = series.max()
        else:
            self._handle_strict_failure(audit_trail_obj)
            raise StrictModeError(f"Unsupported imputation strategy '{strategy}' for column '{col}'")

        # ---------------------------------------------------------
        # Audit permissive imputation
        # ---------------------------------------------------------
        permissive_msg = (
            f"Simple imputation applied to '{col}' using strategy '{strategy}' "
            f"with replacement value {replacement}"
        )

        audit_trail_obj.record_event(
            event="simple_imputation",
            phase=f"_impute_numeric",
            action_type = "impute",
            column=col,
            row_indices=row_indices,
            unique_ids=unique_ids,
            rows=rows,
            message=permissive_msg,
            details={
                "null_count": null_count,
                "strategy": strategy,
                "replacement_value": replacement
            }
        )

        # Perform imputation
        df.loc[null_mask, col] = replacement

        # Dynamic summary key
        summary["imputation"].setdefault(f"{col}_imputed", 0)
        summary["imputation"][f"{col}_imputed"] += null_count

        return df

    # -----------------------------------------------------------
    #   remove duplicated unique ids : 
    #       strict throw err, permissive drop row
    # ------------------------------------------------------------- 
    def _remove_unique_id_duplicates(self, df, audit_trail_obj, summary):

        audit_trail_obj.record_step("_remove_unique_id_duplicates")

        uid = audit_trail_obj.unique_id

        # Step 1: only non-null IDs
        non_null_uids = df.loc[df[uid].notna(), uid]

        # Step 2: duplicates among non-null IDs
        duplicate_ids = non_null_uids[non_null_uids.duplicated(keep=False)]

        # Step 3: mask rows whose UID is in the duplicate set (correct)
        dup_mask = df[uid].isin(duplicate_ids)
        dup_rows = df.loc[dup_mask]

        # No duplicates → nothing to do
        if dup_rows.empty:
            return df

        # Step 4: rows that WILL ACTUALLY BE REMOVED
        # IMPORTANT: use the SAME duplicate_ids set, not duplicated()
        removed_mask = df[uid].isin(duplicate_ids) & df[uid].duplicated(keep="first")
        removed_rows = df.loc[removed_mask]

        # Shared audit variables - ensure JSON-safe values
        unique_ids = df.loc[dup_mask, audit_trail_obj.unique_id].tolist()
        row_indices = dup_rows.index.tolist()
        rows = dup_rows.to_dict(orient="records")

        removed_unique_ids = df.loc[removed_mask, audit_trail_obj.unique_id].tolist()
        removed_indices = removed_rows.index.tolist()
        removed_rows_dict = removed_rows.to_dict(orient="records")

        # Message
        message = (
            f"Duplicate unique_id values detected in column '{uid}'. "
            f"All duplicates shown in audit; only later occurrences removed."
        )

        # Audit event
        audit_trail_obj.record_event(
            event="schema_validation",
            phase="_remove_unique_id_duplicates",
            action_type = "drop",
            column=uid,
            row_indices=row_indices, 
            unique_ids=unique_ids, 
            rows=rows,           
            message=message,
            dropped_rows = {
                "removed_row_indices": removed_indices,
                "removed_unique_ids": removed_unique_ids,
                "removed_rows": removed_rows_dict } )

        # Drop duplicates (keep first occurrence)
        df = df.drop(index=removed_indices)

        # Update summary
        summary["validation"]["duplicate_records"] += len(removed_indices)
        summary["validation"]["rows_dropped"] += len(removed_indices)

        return df

    # ------------------------------------------------------------------
    #   Centralized strict-mode failure handler.
    #   - Saves the audit trail to a dedicated strict-failure audit file
    # -----------------------------------------------------------------
    def _handle_strict_failure(self, audit_trail_obj):

        # Load config
        cfg = config_manager.load_file_config()
        failure_dir = cfg["audit_paths"]["strict_failure_audit_path"]

        # Ensure directory exists
        os.makedirs(failure_dir, exist_ok=True)

        # Split filename into base + extension add Timestamp for uniqueness
        ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

        base, ext = os.path.splitext(cfg["audit_paths"]["strict_failure_audit_filename"])

        # Build final filename with timestamp inserted
        timestamped_name = f"{base}_{ts}{ext}"

        # Full path
        full_path = os.path.join(failure_dir, timestamped_name)

        # Save audit trail
        save_file = audit_trail_obj.to_json()
        file_manager.write_report_file(save_file, full_path)

    # ---------------------------------------------------------------------------
    #  Store the original and cleaned dataframe references as instance attributes
    # ----------------------------------------------------------------------------
    def set_dataframes(self, original_df, cleaned_df):
        self.original_df = original_df
        self.cleaned_df = cleaned_df

    # -------------------------------------------------
    #  Produce 'data quality comparison artifact
    #  - add artifact to the audit_trail_obj
    # --------------------------------------------------
    def compute_comparison(self, audit_trail_obj, schema):
        if self.original_df is None or self.cleaned_df is None:
            return
    
        comparison =  audit_trail_obj.compare_dataframes(self.original_df, self.cleaned_df, schema)

        audit_trail_obj.record_event( 
            event = "compare_dataframes",
            phase = "compare_dataframes",
            action_type = "report",
            comparison = comparison )

    # ------------------------------------------------------------------------------------
    #  Normalize datetime columns based on schema definitions to ensure type for df comparisone
    #  - Coerce all columns defined as datetime in the schema into proper datetime dtype.
    # ------------------------------------------------------------------------------------
    def normalize_datetime_columns(self, df: pd.DataFrame, schema: dict) -> pd.DataFrame:

        # Navigate into the nested schema
        columns = schema.get("schema", {}).get("columns", {})

        for col_name, col_rules in columns.items():
            col_type = str(col_rules.get("type", "")).lower()
            if col_type in ("datetime", "timestamp", "date") and col_name in df.columns:
                df[col_name] = pd.to_datetime(df[col_name].astype(str), errors="coerce")

        return df

    # ----------------------------------------------------------------------
    # 1. CNormalize column names
    # ----------------------------------------------------------------------
    def _normalize_cols(self, df):
        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace("-", "_")
        )
        return df
    
    # ----------------------------------------------------------------------
    # 1. CNormalize categorical values
    # ----------------------------------------------------------------------
    def _normalize_string_values(self, df, schema):

        columns = schema["schema"]["columns"]
        for col, rules in columns.items():

            # Only process columns that exist in the dataframe
            if col not in df.columns:
                continue

            # Only normalize string columns
            if rules.get("type") not in ("string", "category"):
                continue

            # Only normalize if schema says normalize=true
            if not rules.get("normalize", False):
                continue

            # Perform normalization
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .str.lower()
            )

        return df

    # ensure null 
    def clean_value(v):
        if v is pd.NA:
            return None
        return v
