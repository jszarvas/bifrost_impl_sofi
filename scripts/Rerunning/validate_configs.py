#!/usr/bin/env python3
import argparse
import sys
from typing import List
import yaml

# -----------------------------
# Load config
# -----------------------------
def load_config(path: str):
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load '{path}': {e}")


# -----------------------------
# Validation helpers
# -----------------------------
REQUIRED_TOP_LEVEL_KEYS = [
    "component_names",
    "conda_envs",
    "institution",
    "year",
    "runname",
    "sample_names",
    "resources",
]

def validate_required_keys(config, path):
    missing = [k for k in REQUIRED_TOP_LEVEL_KEYS if k not in config]
    if missing:
        raise ValueError(f"{path}: missing required keys: {missing}")

def validate_list(name, value, path):
    if not isinstance(value, list):
        raise TypeError(f"{path}: '{name}' must be a list, got {type(value).__name__}")
    return value

def validate_resources(resources, path):
    required = ["nodes", "ppn", "memory", "walltime"]
    missing = [k for k in required if k not in resources]
    if missing:
        raise ValueError(f"{path}: resources missing keys: {missing}")

    if not isinstance(resources["nodes"], int) or resources["nodes"] <= 0:
        raise ValueError(f"{path}: resources.nodes must be a positive integer")
    if not isinstance(resources["ppn"], int) or resources["ppn"] <= 0:
        raise ValueError(f"{path}: resources.ppn must be a positive integer")
    if not isinstance(resources["memory"], str):
        raise ValueError(f"{path}: resources.memory must be a string")
    if not isinstance(resources["walltime"], str):
        raise ValueError(f"{path}: resources.walltime must be a string")

def validate_lengths(config, path):
    samples = config["sample_names"]
    institutions = config["institution"]
    years = config["year"]
    runnames = config["runname"]

    n = len(samples)

    if len(institutions) != n:
        raise ValueError(f"{path}: 'institution' must have {n} entries, got {len(institutions)}")
    if len(years) != n:
        raise ValueError(f"{path}: 'year' must have {n} entries, got {len(years)}")
    if len(runnames) != n:
        raise ValueError(f"{path}: 'runname' must have {n} entries, got {len(runnames)}")

def validate_components(config, path):
    comps = config["component_names"]
    envs = config["conda_envs"]

    if len(comps) != len(envs):
        raise ValueError(
            f"{path}: component_names and conda_envs must have equal length "
            f"(got {len(comps)} vs {len(envs)})"
        )

    for c in comps:
        if not isinstance(c, str):
            raise TypeError(f"{path}: component '{c}' must be a string")

    for e in envs:
        if not isinstance(e, str):
            raise TypeError(f"{path}: conda env '{e}' must be a string")


# -----------------------------
# Full schema validation
# -----------------------------
def validate_schema(config, path):
    validate_required_keys(config, path)

    config["component_names"] = validate_list("component_names", config["component_names"], path)
    config["conda_envs"] = validate_list("conda_envs", config["conda_envs"], path)
    config["institution"] = validate_list("institution", config["institution"], path)
    config["year"] = validate_list("year", config["year"], path)
    config["runname"] = validate_list("runname", config["runname"], path)
    config["sample_names"] = validate_list("sample_names", config["sample_names"], path)

    validate_resources(config["resources"], path)
    validate_lengths(config, path)
    validate_components(config, path)


# -----------------------------
# CLI
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Validate one or more Bifrost config files.")
    parser.add_argument("configs", nargs="+", help="Path(s) to config YAML file(s).")
    args = parser.parse_args()

    any_errors = False

    for cfg in args.configs:
        try:
            config = load_config(cfg)
            validate_schema(config, cfg)
            print(f"[OK]     {cfg}")
        except Exception as e:
            print(f"[FAILED] {cfg} — {e}")
            any_errors = True

    if any_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()

