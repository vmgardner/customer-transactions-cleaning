import pandas as pd
import os
import json

from src.utilities import StrictModeError
import src.config_manager as config_manager


# ---------------------------------------------------
#  read the schema.for the incoming data file 
# ---------------------------------------------------
def load_schema(file_cfg):

    path = file_cfg["schema_paths"]["schema_path"]
    name = file_cfg["schema_paths"]["schema_name"]
   
    full_path = os.path.join(path,name)
    schema_path = os.path.abspath(full_path)
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # Basic validation
    if "schema" not in schema:
        raise StrictModeError("schema.json missing required 'schema' section")

    if "columns" not in schema["schema"]:
        raise StrictModeError("schema.json missing required key: schema.columns")

    return schema
 
# ------------------------------------------------------------
#  read the pathing configuration file: hold all paths
#   strict failure if not found or errors occur
#  ------------------------------------------------------------
def load_file_config():
    
    config_path = "../config/file_config.json"
    config_path = os.path.abspath(config_path)

    if not os.path.exists(config_path):
        raise StrictModeError(f"Missing file_config.json at: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    
    required_keys = ["audit_paths", "data_paths", "schema_paths", "config_paths" ]
    
    validate_required_keys(cfg, required_keys)

    return cfg

#------------------------------------------------------------------------------
#  use the file_cfg paths to load the cleaner confi
#------------------------------------------------------------------------------
def load_cleaner_config(file_cfg):

    path = file_cfg["config_paths"]["cleaner_config_path"]
    name = file_cfg["config_paths"]["cleaner_config_name"]
    config_path = os.path.join(path, name)
    config_path = os.path.abspath(config_path)
    
    if not os.path.exists(config_path):
        raise StrictModeError(f"Missing cleaner_config.json at: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        cleaner_cfg = json.load(f)

    # Basic validation
    if "cleaner" not in cleaner_cfg:
        raise StrictModeError("cleaner_config.json missing required 'cleaner' section")

    required_keys = [
        "strict_mode"
    ]

    for key in required_keys:
        if key not in cleaner_cfg["cleaner"]:
            raise KeyError(f"cleaner_config.json missing required key: cleaner.{key}")

    return cleaner_cfg

# ---------------------------------------------------
# validate keys in config
# ----------------------------------------------------
def validate_required_keys(cfg: dict, required: list[str]):
    missing = [k for k in required if k not in cfg]
    
    if missing:
        raise StrictModeError(f"Missing required config keys: {missing}")
    return
