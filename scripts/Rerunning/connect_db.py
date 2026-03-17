#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
from typing import Any, Dict, List, Optional, Tuple
import re
import datetime
from pathlib import Path, PurePosixPath

import yaml
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson import ObjectId
from collections import Counter

# -----------------------------
# Connection + Utility Functions
# -----------------------------

def ping_database(client: MongoClient) -> bool:
    try:
        client.admin.command("ping")
        return True
    except ConnectionFailure:
        return False


def parse_query_string(query_str: str) -> Dict[str, Any]:
    """
    Parse a Python dict-like string into a dict, with no builtins.
    Supports Mongo-style operators, including regex:
      --query "{'name': {'$regex': 'testrun_ec', '$options': 'i'}}"
    """
    try:
        return eval(query_str, {"__builtins__": {}})
    except Exception as exc:
        raise ValueError(f"Invalid query string: {exc}")


def list_databases(client: MongoClient) -> List[str]:
    return client.list_database_names()


def list_collections(client: MongoClient, dbname: str) -> List[str]:
    return client[dbname].list_collection_names()


def run_find_many(
    client: MongoClient,
    dbname: str,
    collection: str,
    query: Dict[str, Any]
) -> List[Dict[str, Any]]:
    return list(client[dbname][collection].find(query))


def convert_objectid(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_objectid(v) for v in obj]
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    return obj


def save_json(data: Any, path: str) -> None:
    with open(path, "w") as f:
        json.dump(convert_objectid(data), f, indent=4)


# -----------------------------
# Path-based inference helpers
# -----------------------------

def get_primary_data_path(doc: Dict[str, Any]) -> Optional[str]:
    """
    Return the first data path from:
      1. categories.paired_reads.summary.data[0]
      2. categories.contigs.summary.data[0]

    Returns None if neither exists.
    """
    categories = doc.get("categories", {})

    paired_reads = categories.get("paired_reads", {})
    paired_summary = paired_reads.get("summary", {})
    paired_data = paired_summary.get("data", [])
    if isinstance(paired_data, list) and paired_data:
        first = paired_data[0]
        if first:
            return str(first)

    contigs = categories.get("contigs", {})
    contigs_summary = contigs.get("summary", {})
    contigs_data = contigs_summary.get("data", [])
    if isinstance(contigs_data, list) and contigs_data:
        first = contigs_data[0]
        if first:
            return str(first)

    return None


def extract_institution_and_year_from_path(path_str: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract institution and year from a path like:
      /home/projects/fvst_ssi_dtu/prod_data/output/ssi/2025/...

    Using PurePosixPath(path).parts this becomes:
      ('/', 'home', 'projects', 'fvst_ssi_dtu', 'prod_data', 'output', 'ssi', '2025', ...)

    So:
      institution = parts[6]
      year        = parts[7]
    """
    parts = PurePosixPath(path_str).parts

    institution = None
    year = None

    if len(parts) > 6:
        institution = str(parts[6]).strip().lower() or None

    if len(parts) > 7:
        y = str(parts[7]).strip()
        if y.isdigit():
            year = y

    return institution, year


# -----------------------------
# Component helpers
# -----------------------------

def extract_year(value, min_year=1990, max_year=None):
    if max_year is None:
        max_year = datetime.datetime.now().year + 1

    s = "" if value is None else str(value)

    # try first 4
    if len(s) >= 4:
        y = s[:4]
        if y.isdigit() and min_year <= int(y) <= max_year:
            return y

    # try last 4
    if len(s) >= 4:
        y = s[-4:]
        if y.isdigit() and min_year <= int(y) <= max_year:
            return y

    return str(datetime.datetime.now().year)


def infer_doc_year(doc: Dict[str, Any]) -> str:
    """
    Infer year from the first available data path:
      1. categories.paired_reads.summary.data[0]
      2. categories.contigs.summary.data[0]

    If path-based inference fails, fall back to current year.
    """
    path_str = get_primary_data_path(doc)
    if path_str:
        _, year = extract_institution_and_year_from_path(path_str)
        if year:
            return year

    return str(datetime.datetime.now().year)


def infer_doc_institution(doc: Dict[str, Any]) -> Optional[str]:
    """
    Infer institution from the first available data path:
      1. categories.paired_reads.summary.data[0]
      2. categories.contigs.summary.data[0]

    Returns None if missing.
    """
    path_str = get_primary_data_path(doc)
    if path_str:
        institution, _ = extract_institution_and_year_from_path(path_str)
        return institution

    return None


def print_institution_counts(docs: List[Dict[str, Any]]) -> None:
    counts = Counter()
    for doc in docs:
        inst = infer_doc_institution(doc)
        counts[inst if inst is not None else "<missing>"] += 1

    print("Institutions in current result set:")
    for inst, n in sorted(counts.items()):
        print(f"  {inst}: {n}")

# ---------------------------------------------- #
# Creating conda environment and component names
# ---------------------------------------------- #

def normalize_component_version(value: str) -> str:
    """
    Keep only the semantic version part from strings like:
      v2.2.11
      v2.2.11__5e385d4
      2.2.11
    Returns a normalized version string with leading 'v'.
    """
    m = re.search(r'(?:^|__)(v?\d+(?:\.\d+){0,2})(?:$|__)', value)
    if not m:
        return "v1.0.0"

    version = m.group(1)
    if not version.startswith("v"):
        version = f"v{version}"
    return version


def parse_component_full_name(full_name: str) -> Tuple[str, str]:
    """
    From a component name like:
      "min_read_check__v2.2.8"
      "cge_mlst__v2.2.11__5e385d4"

    extract:
      short:   "min_read_check"
      version: "v2.2.8" / "v2.2.11"

    If no version is present, default to "v1.0.0".
    """
    if "__" in full_name:
        short, rest = full_name.split("__", 1)
    else:
        short = full_name
        rest = ""

    version = normalize_component_version(rest)
    return short, version

def version_to_tuple(version: str) -> Tuple[int, int, int]:
    """
    Convert a version string like:
      v2.10.0
      2.10.0
      v2.10.0__abcdef

    into (2, 10, 0).
    """
    normalized = normalize_component_version(version)
    m = re.search(r'v(\d+)(?:\.(\d+))?(?:\.(\d+))?', normalized)
    if not m:
        return (0, 0, 0)

    major = int(m.group(1)) if m.group(1) else 0
    minor = int(m.group(2)) if m.group(2) else 0
    patch = int(m.group(3)) if m.group(3) else 0
    return (major, minor, patch)

def collect_components_from_docs(
    docs: List[Dict[str, Any]]
) -> Dict[str, List[str]]:
    """
    From all documents, collect:
      short_name -> list of normalized versions seen
    """
    comp_map: Dict[str, List[str]] = {}

    for doc in docs:
        components = doc.get("components", [])
        for comp in components:
            full_name = comp.get("name")
            if not full_name:
                continue

            short, version = parse_component_full_name(full_name)
            comp_map.setdefault(short, [])

            if version not in comp_map[short]:
                comp_map[short].append(version)

    return comp_map

def collect_components_from_env() -> Dict[str, List[str]]:
    """
    Read component/version information from $BIFROST_COMPONENTS.

    Example:
      bifrost_min_read_check_v2.2.8
      bifrost_whats_my_species_v2.2.11
      bifrost_salmonella_subspecies_dtartrate_v1.1.3

    Returns:
      short_name -> list of normalized versions seen

    If the variable is missing, empty, or contains no valid entries, returns {}.
    """
    raw = os.environ.get("BIFROST_COMPONENTS", "").strip()
    if not raw:
        return {}

    comp_map: Dict[str, List[str]] = {}

    for token in raw.split():
        token = token.strip()
        print(f"the existing tokens {token}")

        if not token:
            continue

        m = re.fullmatch(r"bifrost_(.+)_(v?\d+(?:\.\d+){0,2})", token)
        if not m:
            print(f"Warning: could not parse entry in BIFROST_COMPONENTS: {token}")
            continue

        #print(f"m match {m}")
        short = m.group(1)
        #print(f"short match {short}")
        
        version = normalize_component_version(m.group(2))
        #print(f"version {version}")
        
        comp_map.setdefault(short, [])
        if version not in comp_map[short]:
            comp_map[short].append(version)

    return comp_map

def select_components(
    comp_map: Dict[str, List[str]],
    include_components: Optional[List[str]],
    exclude_components: Optional[List[str]],
    stage: str,
) -> Tuple[List[str], List[str]]:
    """
    Apply component selection rules:

    1. No --components and no --exclude:
         -> include all components.
    2. --components A,B only:
         -> include only A,B.
    3. --exclude X,Y only:
         -> include all except X,Y.
    4. --components and --exclude together:
         -> invalid (handled earlier in main).

    Both include_components and exclude_components are short names.
    Returns:
      component_names: ["bifrost_<short>", ...]
      conda_envs:      ["bifrost_<stage>_<short>_<version>", ...]
    where <version> is the newest version per short (numeric comparison).
    """

    all_shorts = set(comp_map.keys())

    if include_components and exclude_components:
        raise ValueError("Cannot use --components and --exclude together. Choose one mode.")

    if include_components:
        selected_shorts = set(include_components)
    elif exclude_components:
        selected_shorts = all_shorts - set(exclude_components)
    else:
        selected_shorts = all_shorts

    component_names: List[str] = []
    conda_envs: List[str] = []

    for short in sorted(selected_shorts):
        versions = comp_map.get(short, [])
        if not versions:
            continue

        newest = max(versions, key=version_to_tuple)
        bifrost_name = f"bifrost_{short}"
        env = f"bifrost_{stage}_{short}_{newest}"

        if bifrost_name not in component_names:
            component_names.append(bifrost_name)
        if env not in conda_envs:
            conda_envs.append(env)

    return component_names, conda_envs


def check_conda_env(config: Dict[str, Any]) -> None:
    """
    Check whether generated conda environments exist in:
        $BIFROST_CONDA_PATH/envs/

    Missing environments are removed from:
      - config["conda_envs"]
      - config["component_names"]

    This function does NOT stop execution.
    It only prints warnings and updates the config in place.
    """
    conda_base = os.environ.get("BIFROST_CONDA_PATH")
    if not conda_base:
        print("Warning: BIFROST_CONDA_PATH is not set. Skipping conda environment check.")
        return

    env_root = Path(conda_base) / "envs"
    if not env_root.exists():
        print(f"Warning: conda env directory does not exist: {env_root}")
        print("Skipping conda environment check.")
        return

    component_names = config.get("component_names", [])
    conda_envs = config.get("conda_envs", [])

    if len(component_names) != len(conda_envs):
        print(
            "Warning: component_names and conda_envs have different lengths. "
            "Skipping conda environment filtering."
        )
        return

    kept_components: List[str] = []
    kept_envs: List[str] = []
    missing_envs: List[str] = []

    for component_name, env_name in zip(component_names, conda_envs):
        env_path = env_root / env_name
        if env_path.is_dir():
            kept_components.append(component_name)
            kept_envs.append(env_name)
        else:
            missing_envs.append(env_name)

    config["component_names"] = kept_components
    config["conda_envs"] = kept_envs

    if missing_envs:
        print("Warning: the following conda environment(s) were not found and were removed from the YAML:")
        for env in missing_envs:
            print(f"  - {env}")
    else:
        print(f"All inferred conda environments were found in: {env_root}")

# -----------------------------
# Config creation helpers
# -----------------------------

def build_config_from_docs(
    docs: List[Dict[str, Any]],
    nodes: int,
    ppn: int,
    memory: str,
    walltime: str,
    selected_components: Optional[List[str]],
    excluded_components: Optional[List[str]],
) -> Dict[str, Any]:
    """
    Build a multi-sample config from a list of documents.
    - Automatically collects components + versions from all docs.
    - Applies include/exclude logic on short names.
    - Picks newest version per component (numeric comparison).
    - Collects per-sample institution/year/runname/sample_names.
    """
    if not docs:
        raise RuntimeError("No documents provided to build_config_from_docs.")

    stage = os.environ.get("BIFROST_STAGE", "dev")

    # try to infer the component and environments from first the variable enxt from the mongoDB collections
    comp_map = collect_components_from_env()
    if comp_map:
        print("Using components from BIFROST_COMPONENTS.")
    else:
        print("BIFROST_COMPONENTS not set or empty. Falling back to components inferred from Mongo documents.")
        comp_map = collect_components_from_docs(docs)

    component_names, conda_envs = select_components(
        comp_map,
        include_components=selected_components,
        exclude_components=excluded_components,
        stage=stage,
    )

    institutions: List[str] = []
    years: List[str] = []
    runnames: List[str] = []
    sample_names: List[str] = []

    for doc in docs:
        inst = infer_doc_institution(doc)
        institutions.append(inst if inst is not None else "")

        year_val = infer_doc_year(doc)
        years.append(year_val)

        db_name_field = doc.get("name", "")
        runname_field = db_name_field.split("___", 1)[0]

        runnames.append(runname_field)
        sample_names.append(db_name_field)

    resources = {
        "nodes": nodes,
        "ppn": ppn,
        "memory": memory,
        "walltime": walltime,
    }

    config = {
        "component_names": component_names,
        "conda_envs": conda_envs,
        "institution": institutions,
        "year": years,
        "runname": runnames,
        "sample_names": sample_names,
        "resources": resources,
    }

    return config


def save_config_yaml(config: Dict[str, Any], path: str) -> None:
    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    print(f"Config file '{path}' created successfully.")


# -----------------------------
# Main CLI Logic
# -----------------------------

def main() -> None:
    default_dbkey = os.environ.get("BIFROST_DB_KEY")

    parser = argparse.ArgumentParser(description="MongoDB exploration, query, and multi-sample config tool.")

    parser.add_argument(
        "--dbkey",
        default=default_dbkey,
        help="MongoDB URI (default: value of BIFROST_DB_KEY)."
    )

    parser.add_argument(
        "--dbname",
        nargs="?",
        const="__LIST__",
        help="Database name. If provided without value, lists all DBs."
    )

    parser.add_argument(
        "--collectionname",
        nargs="?",
        const="__LIST__",
        help="Collection name. If provided without value, lists collections in DB."
    )

    parser.add_argument(
        "--query",
        help="MongoDB query as a Python dict string. "
             "Example: \"{'name': {'$regex': 'testrun_ec', '$options': 'i'}}\""
    )

    parser.add_argument(
        "--json",
        help="Output JSON file to store results."
    )

    parser.add_argument(
        "--create_config",
        action="store_true",
        help="If set, create a YAML config from the queried documents."
    )

    parser.add_argument(
        "--components",
        type=lambda s: [x.strip() for x in s.split(",")],
        help="Comma-separated list of short component names to include "
             "(e.g. min_read_check,assemblatron). "
             "If omitted (and --exclude not used), all components are included."
    )

    parser.add_argument(
        "--exclude",
        type=lambda s: [x.strip() for x in s.split(",")],
        help="Comma-separated list of short component names to exclude "
             "(e.g. min_read_check,assemblatron). "
             "Cannot be used together with --components."
    )

    parser.add_argument(
        "--institution",
        type=lambda s: [x.strip().lower() for x in s.split(",")],
        help="Comma-separated institution filter based on inferred institution "
             "(e.g. ssi or ssi,fvst). If omitted, all institutions are included."
    )

    parser.add_argument(
        "--year",
        type=lambda s: [x.strip() for x in s.split(",")],
        help="Comma-separated year filter (e.g. 2024 or 2024,2025). "
             "If omitted, all inferred years are included."
    )

    parser.add_argument(
        "--nodes",
        type=int,
        default=1,
        help="Nodes for resources (default: 1)."
    )

    parser.add_argument(
        "--ppn",
        type=int,
        default=4,
        help="Processors per node (default: 4)."
    )

    parser.add_argument(
        "--memory",
        default="2gb",
        help="Memory for resources (default: 2gb)."
    )

    parser.add_argument(
        "--walltime",
        default="01:00:00",
        help="Walltime for resources (default: 01:00:00)."
    )

    parser.add_argument(
        "--output",
        default="config.yaml",
        help="Output YAML config filename (default: config.yaml)."
    )

    args = parser.parse_args()

    if args.components and args.exclude:
        raise ValueError("You cannot use --components and --exclude together. Choose one mode.")

    if not args.dbkey:
        raise RuntimeError("No MongoDB key provided and BIFROST_DB_KEY is not set.")

    client = MongoClient(args.dbkey)

    if not ping_database(client):
        raise RuntimeError("Failed to connect to MongoDB.")
    else:
        print("Successfully connected to MongoDB.")

    if args.dbname == "__LIST__":
        dbs = list_databases(client)
        print("Available databases:")
        for d in dbs:
            print(f"- {d}")

        if args.json:
            save_json(dbs, args.json)
            print(f"Saved database list to {args.json}")
        return

    if args.dbname and args.collectionname == "__LIST__":
        collections = list_collections(client, args.dbname)
        print(f"Available collections in {args.dbname}:")
        for c in collections:
            print(f"- {c}")

        if args.json:
            save_json(collections, args.json)
            print(f"Saved collection list to {args.json}")
        return

    if args.dbname and args.collectionname and args.query:
        query_dict = parse_query_string(args.query)
        results = run_find_many(client, args.dbname, args.collectionname, query_dict)

        print(f"Query matched {len(results)} document(s).")

        if args.year:
            allowed_years = set(args.year)
            results = [doc for doc in results if infer_doc_year(doc) in allowed_years]
            print(f"{len(results)} document(s) remain after year filtering: {sorted(allowed_years)}")

        print_institution_counts(results)

        if args.institution:
            allowed_institutions = {x.strip().lower() for x in args.institution}
            results = [
                doc for doc in results
                if infer_doc_institution(doc) in allowed_institutions
            ]
            print(f"{len(results)} document(s) remain after institution filtering: {sorted(allowed_institutions)}")

        if not results:
            print(
                f"Warning: no documents matched the query after applying "
                f"year={args.year or 'all'} and institution={args.institution or 'all'}."
            )
            return

        if args.json:
            save_json(results, args.json)
            print(f"Saved query results to {args.json}")

        if args.create_config:
            config = build_config_from_docs(
                results,
                nodes=args.nodes,
                ppn=args.ppn,
                memory=args.memory,
                walltime=args.walltime,
                selected_components=args.components,
                excluded_components=args.exclude,
            )

            check_conda_env(config)
            save_config_yaml(config, args.output)

        return

    print("No valid mode selected. Use --help for usage details.")


if __name__ == "__main__":
    main()
