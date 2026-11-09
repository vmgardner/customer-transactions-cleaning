# src/audit_trail.py

import numpy as np
import pandas as pd
import json
import os
from datetime import datetime

class AuditTrail:

    # ----------------------------------------------------------
    #   Constructor
    # ----------------------------------------------------------
    def __init__(self, schema=None):
        self.schema = schema
        self.events = []
        self.initial_stats = {}
        self.final_stats = {}
        self.summary = {}
        self.original_df = None
        self.cleaned_df = None
        self.comparison = {}
        self.unique_id = None

        if self.original_df is not None and self.cleaned_df is not None:
            self.comparison = self.compare_dataframes(self.original_df, self.cleaned_df)
    
    
    def to_dict(self):

        def sanitize(obj):

            # ---------------------------------------------------
            # Dict -> sanitize values recursively
            # ---------------------------------------------------
            if isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}

            # ---------------------------------------------------
            # List -> sanitize items recursively
            # ---------------------------------------------------
            if isinstance(obj, list):
                return [sanitize(x) for x in obj]

            # ---------------------------------------------------
            # Pandas Series -> list
            # ---------------------------------------------------
            if isinstance(obj, pd.Series):
                return [sanitize(x) for x in obj.tolist()]

            # ---------------------------------------------------
            # Pandas DataFrame -> list of dicts
            # ---------------------------------------------------
            if isinstance(obj, pd.DataFrame):
                return [
                    sanitize(row)
                    for row in obj.to_dict(orient="records")
                ]

            # ---------------------------------------------------
            # NumPy array -> list
            # ---------------------------------------------------
            if isinstance(obj, np.ndarray):
                return [sanitize(x) for x in obj.tolist()]

            # ---------------------------------------------------
            # NumPy scalar -> Python scalar
            # ---------------------------------------------------
            if isinstance(obj, np.generic):
                obj = obj.item()

            try:
                if pd.isna(obj):
                    return None
            except Exception:
                pass

            # ---------------------------------------------------
            # Pandas Timestamp -> ISO string
            # ---------------------------------------------------
            if isinstance(obj, pd.Timestamp):
                return obj.isoformat()

            # ---------------------------------------------------
            # Python datetime -> ISO string
            # ---------------------------------------------------
            if isinstance(obj, datetime):
                return obj.isoformat()

            # ---------------------------------------------------
            # Leave everything else untouched
            # ---------------------------------------------------
            return obj

        audit_dict = {
            "initial_stats": self.initial_stats,
            "events": self.events,
            "final_stats": self.final_stats,
            "summary": self.summary
        }

        return sanitize(audit_dict)

    # ----------------------------------------------------------
    #   Add summary to the audit trak
    # ----------------------------------------------------------
    def record_summary(self, summary_dict):
        self.summary = summary_dict
 
    # ----------------------------------------------------------
    #   AUDIT HELPERS (now fully encapsulated)
    # ----------------------------------------------------------
    def record_initial_stats(self, df):
        self.initial_stats = {
            "row_count": len(df),
            "null_counts": df.isna().sum().to_dict(),
            "timestamp": pd.Timestamp.now().isoformat()
        }

    # ----------------------------------------------------------
    #   record the final gathering of the statistics
    # ----------------------------------------------------------
    def record_final_stats(self, df):
        self.final_stats = {
            "row_count": len(df),
            "null_counts": df.isna().sum().to_dict(),
            "timestamp": pd.Timestamp.now().isoformat()
        }

    # ----------------------------------------------------------
    #   records the steps of the process
    # ----------------------------------------------------------
    def record_step(self, step_name: str):
        self.events.append({
            "event": "step",
            "step": step_name,
            "timestamp": pd.Timestamp.now().isoformat()
        })
    
    # ----------------------------------------------------------
    #   records the events along with the current phase
    # ----------------------------------------------------------
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
        details: dict = None,
    ):
        entry = {
            "timestamp": pd.Timestamp.now().isoformat()
        }

        # Only add fields that were provided
        if event:
            entry["event"] = event
        
        if phase:
            entry["phase"] = phase

        if event:
            entry["action_type"] = action_type

        if column:
            entry["column"] = column

        if row_indices:
            entry["row_indices"] = row_indices

        if unique_ids:
            entry["unique_ids"] = unique_ids or []

        if rows:
            entry["rows"] = rows

        if message:
            entry["message"] = message

        if details:
            entry["details"] = details

        if dropped_rows:
            entry["dropped_rows"] = dropped_rows
            
        if comparison:
            entry["comparison"] = comparison

        self.events.append(entry)

    # ------------------------------------------------------------------------------------
    #   Compare two DataFrames and generate a structured diff report for audit purposes.   
    #   assumes consistant column names and types across the datasets
    # ------------------------------------------------------------------------------------
    def compare_dataframes(self, original: pd.DataFrame, cleaned: pd.DataFrame, schema: dict) -> dict:
        
        report = {}

        # -------------------------------------------------------
        # Schema-driven category normalization
        # Prevents false positives caused by:
        # " South " vs "south"
        # -------------------------------------------------------
        schema_cols = schema["schema"]["columns"]

        for col, rules in schema_cols.items():
            if rules.get("normalize", False):
                if col in original.columns:
                    original[col] = (
                        original[col]
                        .astype("string")
                        .str.strip()
                        .str.lower() )

        # -------------------------------------------------------
        # Column-level comparison
        # -------------------------------------------------------
        original_cols = set(original.columns)
        cleaned_cols = set(cleaned.columns)

        report["dropped_columns"] = sorted(original_cols - cleaned_cols)
        report["added_columns"] = sorted(cleaned_cols - original_cols)

        # -------------------------------------------------------
        # Row-count comparison
        # -------------------------------------------------------
        report["row_count_original"] = len(original)
        report["row_count_cleaned"] = len(cleaned)
        report["rows_dropped"] = len(original) - len(cleaned)

        # -------------------------------------------------------
        # Value-level comparison
        # -------------------------------------------------------
        common_cols = sorted(original_cols & cleaned_cols)

        changed_cells = {}

        cleaned_aligned = cleaned.reindex(original.index)

        for col in common_cols:

            orig_col = original[col]
            clean_col = cleaned_aligned[col]

            col_mask = None

            # ---------------------------------------------------
            # Numeric comparison
            # Handles:
            # "123.45" == 123.45
            # ---------------------------------------------------
            try:
                orig_num = pd.to_numeric(orig_col, errors="coerce")
                clean_num = pd.to_numeric(clean_col, errors="coerce")

                if orig_num.notna().any() or clean_num.notna().any():
                    col_mask = orig_num.ne(clean_num)

            except Exception:
                col_mask = None

            # ---------------------------------------------------
            # Direct comparison
            # ---------------------------------------------------
            if col_mask is None:
                col_mask = orig_col.ne(clean_col)

            # ---------------------------------------------------
            # Record changes
            # ---------------------------------------------------
            if col_mask.any():

                changed_rows = col_mask[col_mask].index.tolist()

                changed_cells[col] = {
                    "changed_row_indices": changed_rows,
                    "original_values": orig_col.loc[changed_rows].tolist(),
                    "cleaned_values": clean_col.loc[changed_rows].tolist(),
                    "count_changed": len(changed_rows),
                }

        report["changed_values"] = changed_cells

        return report

    # ----------------------------------------------------------
    #   record each start of a column
    # ----------------------------------------------------------
    def record_column_start(self, column: str):
        self.events.append({
            "event": "column_start",
            "column": column,
            "timestamp": pd.Timestamp.now().isoformat()
        })

    # ----------------------------------------------------------
    #   record each end of a column
    # ----------------------------------------------------------
    def record_column_end(self, column: str):
        self.events.append({
            "event": "column_end",
            "column": column,
            "timestamp": pd.Timestamp.now().isoformat()
        })

    # ----------------------------------------------------------
    #   report generator to json
    # ----------------------------------------------------------
    def to_json(self, indent: int = 2) -> str:       
        return json.dumps(self.to_dict(), indent=indent, default=str)
        
    # ----------------------------------------------------------
    #   Markdown audit report generator
    # ----------------------------------------------------------
    # def to_markdown_summary(self, summary):
    def to_markdown_summary(self):
        summary = self.summary
        
        lines = ["# Data Cleaning Summary", ""]
        
        lines.append("## Validation")
        for key, value in summary["validation"].items():
            lines.append(f"- {key.replace('_', ' ').title()}: {value}")

        lines.append("")
        lines.append("## Transformation")
        for key, value in summary["transformation"].items():
            lines.append(f"- {key.replace('_', ' ').title()}: {value}")

        lines.append("")
        lines.append("## Imputation")
        for key, value in summary["imputation"].items():
            lines.append(f"- {key.replace('_', ' ').title()}: {value}")

        return "\n".join(lines)

    # ----------------------------------------------------------
    #   Markdown audit report generator
    #   Format is suitable for documentation, notebooks, or BI notes
    # ----------------------------------------------------------
    def to_markdown(self) -> str:
       
        lines = []

        # Header
        lines.append("# Data Cleaning Audit Report")
        lines.append("")

        # Initial stats
        lines.append("## Initial dataset statistics")
        if self.initial_stats:
            lines.append(f"- **Row count:** {self.initial_stats.get('row_count')}")
            lines.append(f"- **Timestamp:** {self.initial_stats.get('timestamp')}")
            lines.append("")
            lines.append("### Initial null counts by column")          
            # # lines.append("")
            #lines.append(f"**Initial null counts by column**") 
            for col, count in self.initial_stats.get("null_counts", {}).items():
                lines.append(f"- **{col}:** {count}")
        else:
            lines.append("- No initial statistics recorded.")
        lines.append("")

        # Final stats
        lines.append("## Final dataset statistics")
        if self.final_stats:
            lines.append(f"- **Row count:** {self.final_stats.get('row_count')}")
            lines.append(f"- **Timestamp:** {self.final_stats.get('timestamp')}")
            lines.append("")
            lines.append("### Final null counts by column")
            #lines.append("")
            for col, count in self.final_stats.get("null_counts", {}).items():
                lines.append(f"- **{col}:** {count}")
        else:
            lines.append("- No final statistics recorded.")
        lines.append("")

        # Phase Summary
        lines.append("## Phase Summary")
        lines.append("")
        lines.append(self.to_markdown_summary())
        lines.append("")

        # Events
        lines.append("## Event log")
        if not self.events:
            lines.append("")
            lines.append("No events recorded.")
        else:
            lines.append("")
            for evt in self.events:
                etype = evt.get("event")
                ts = evt.get("timestamp")
                if etype == "step":
                    lines.append(f"- **Step:** `{evt.get('step')}`  — _{ts}_")
                elif etype == "column_start":
                    lines.append(f"- **Column start:** `{evt.get('column')}`  — _{ts}_")
                elif etype == "column_end":
                    lines.append(f"- **Column end:** `{evt.get('column')}`  — _{ts}_")
                elif etype == "validation":
                    col = evt.get("column")
                    msg = evt.get("message")
                    details = evt.get("details")
                    lines.append(f"- **Validation:** `{col}` — {msg}  — _{ts}_")
                    if details:
                        lines.append(f"  - **Details:** `{details}`")
                elif etype == "imputation":
                    col = evt.get("column")
                    method = evt.get("method")
                    count = evt.get("count")
                    lines.append(
                        f"- **Imputation:** `{col}` — method `{method}`, "
                        f"imputed `{count}` values  — _{ts}_"
                    )
                elif etype == "winsorization":
                    col = evt.get("column")
                    lower = evt.get("lower_bound")
                    upper = evt.get("upper_bound")
                    lines.append(
                        f"- **Winsorization:** `{col}` — "
                        f"lower `{lower}`, upper `{upper}`  — _{ts}_"
                    )
                else:
                    lines.append(f"- **Event:** `{etype}` — {evt}  — _{ts}_")

        lines.append("")
        return "\n".join(lines)

    