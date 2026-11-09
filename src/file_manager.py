

import os
import json
import logging
from datetime import datetime

import pandas as pd

import src.audit_trail as audit_trail
from src.utilities import StrictModeError
import src.config_manager as config_manager

class AuditHandle:
    def __init__(self, json_path: str, json_pretty_path, md_path: str, summary_path: str):
        self.json_path = json_path
        self.json_pretty_path = json_pretty_path
        self.md_path = md_path
        self.process_summary_path = summary_path
        

    def read_json(self) -> str:
        return read_file(self.json_path)


    def read_markdown(self) -> str:
        return read_file(self.md_path)
    
    def read_summary(self) -> str:
        return read_file(self.summary_path)

# -----------------------------------------------------------
# Main loader: load the actual file
# -----------------------------------------------------------
def load_raw_data_file(audit_trail_obj, file_cfg):
    df = pd.DataFrame()
   
    full_path = os.path.join(file_cfg["data_paths"]["input_path"], file_cfg["data_paths"]["input_filename"])

    if os.path.exists(full_path):
        sep = _detect_delimiter(full_path)

        df = pd.read_csv(
            full_path,
            sep=sep,
            skipinitialspace=True,
            encoding="utf-8-sig"
            ) 
        
        audit_trail_obj.record_event(
            event="load_raw_data_file",
            phase="load_raw_data_file",
            action_type = "read",
            column=None,
            message="Read raw datafile into dataFrame successfully.",
            details={
                "path": file_cfg["data_paths"]["input_path"],
                "filename": file_cfg["data_paths"]["input_filename"],
                "full_path": full_path,
                "row_count": len(df),
                "column_count": len(df.columns)})
    else:
        raise StrictModeError(
            "File not found",
            details=f"File not found: {full_path}")
    
    return df

# ------------------------------------------------------------
# Save the cleaned dataset to disk
# ------------------------------------------------------------
def save_cleaned_dataset(df, audit_trail_obj, file_cfg):

    # 1. Get timestamp
    ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    # 2. Split base name and extension
    base, ext = os.path.splitext(file_cfg["data_paths"]["output_filename"])
    # 3. Build timestamped filename
    timestamped_name = f"{base}_{ts}{ext}"
    # 4. Join with directory path
    full_path = os.path.join(file_cfg["data_paths"]["output_path"], timestamped_name)
    try:
        df.to_csv(full_path, index=False, header=True)
    except StrictModeError as e:
        raise e

    audit_trail_obj.record_event(
        event = "file_manager",
        phase = "save_cleaned_dataset",
        action_type = "write",
        message = f"Successfully saved cleaned datafile.",
        details =  
        {
            "path": file_cfg["data_paths"]["output_path"],
            "filename": timestamped_name,
            "full_path": full_path,
            "row_count": len(df),
            "column_count": len(df.columns) } )

    return True

# ------------------------------------------------------------
# generate the audit files and summary 
# save the audit reports and process summary to disk
# return the audit_handle (full paths to the reports)
# ------------------------------------------------------------
def save_audit_reports(audit_trail_obj, file_cfg) -> AuditHandle:
    audit_handle = AuditHandle("", "", "", "")
    ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    audit_dir = file_cfg["audit_paths"]["audit_dir"]

    def build_path(base_filename: str) -> str:
        base, ext = os.path.splitext(base_filename)
        timestamped = f"{base}_{ts}{ext}"
        return os.path.join(audit_dir, timestamped)

    def safe_write(content: str, path: str, phase: str):
        try:
            write_report_file(content, path)
        except StrictModeError as exc:
            audit_trail_obj.report_event(
                event="save_audit_report",
                phase=phase,
                action_type="write",
                message= f"Error writting file: {path}",
                details={"error": str(exc), "path": path } )
            raise exc


    # JSON audit
    json_path = build_path(file_cfg["audit_paths"]["audit_json_filename"])
    audit_handle.json_path = json_path
    safe_write(audit_trail_obj.to_json(), json_path, phase="save_audit_json")

    pretty_json_path = json_path.replace(".json", "_pretty.json")
    audit_handle.json_pretty_path = pretty_json_path

    pretty_content = json.dumps(
        json.loads(audit_trail_obj.to_json()),
        indent=2
    )

    safe_write(pretty_content, pretty_json_path, phase="save_audit_json_pretty")


    # Markdown audit
    md_path = build_path(file_cfg["audit_paths"]["audit_md_filename"])
    audit_handle.md_path = md_path
    safe_write(audit_trail_obj.to_markdown(), md_path, phase="save_audit_md")

    # Summary markdown
    #summary_name = build_path(file_cfg["audit_paths"]["summary_filename"])
    summary_path = build_path(file_cfg["audit_paths"]["summary_filename"])
    audit_handle.process_summary_path = summary_path
    summary = audit_trail_obj.to_markdown_summary()
    safe_write(summary, summary_path, phase="save_audit_summary")
    #safe_write(audit_trail_obj.to_markdown_summary(), summary_path, phase="save_audit_summary")

    return audit_handle

# ----------------------------------------------------------
#   Write the file to file  
#   path=full_path including the file name
# ----------------------------------------------------------
def write_report_file(file, path):
    """ Write what is passed in """
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(file)
    except StrictModeError as e:
        raise e
    
    return True

#------------------------------------------------------
#   Read a report file from the given path.
# -----------------------------------------------------
def read_file(path):

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except StrictModeError as e:
        raise e
    return None

# -----------------------------------------------------------
# Helper: delimiter detection
# -----------------------------------------------------------
def _detect_delimiter(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        header = f.readline()

    common_delims = [",", ";", "\t", "|"]
    counts = {d: header.count(d) for d in common_delims}

    best = max(counts, key=counts.get)

    if counts[best] < 1:
        raise ValueError(f"Could not detect delimiter in file: {path}")

    return best

#---------------------------------------------------------------
#   WIP Get the most recent audit report of a specific format.
#    WIP
# ---------------------------------------------------------------
def get_most_recent_audit_report(file_format):
    # WIP future implementation WIP
    file_cfg = config_manager.load_file_config()
    audit_dir = file_cfg["audit_report_path"]

    files = [
            f for f in os.listdir(audit_dir)
            if os.path.isfile(os.path.join(audit_dir, f)) and f.endswith(file_format) ]

    if not files:
            return None

        # Sort by timestamp embedded in filename
    files.sort(reverse=True)

    latest = files[0]

    full_path = os.path.join(audit_dir, latest)

    return read_file(full_path)