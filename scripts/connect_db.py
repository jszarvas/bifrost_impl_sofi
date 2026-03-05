#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
from typing import Any, Dict, List, Optional, Tuple
import re
import datetime

import yaml
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson import ObjectId


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
# Component helpers
# -----------------------------

def parse_component_full_name(full_name: str) -> Tuple[str, str]:
    """
    From a component name like "min_read_check__v2.2.8" extract:
      short:   "min_read_check"
      version: "v2.2.8"
    If no version is present, default to "v1.0.0".
    """
    if "__" in full_name:
        short, version = full_name.split("__", 1)
    else:
        short = full_name
        version = "v1.0.0"
    return short, version


def version_to_tuple(version: str) -> Tuple[int, int, int]:
    """
    Convert a version string like "v2.10.0" or "2.10.0" to a numeric tuple (2,10,0).
    Non-matching parts default to 0.
    """
    m = re.search(r'v?(\d+)(?:\.(\d+))?(?:\.(\d+))?', version)
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
      short_name -> list of versions seen
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
        # This should be prevented earlier, but keep a guard.
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
        # Pick newest version by numeric tuple
        newest = max(versions, key=version_to_tuple)
        bifrost_name = f"bifrost_{short}"
        env = f"bifrost_{stage}_{short}_{newest}"
        if bifrost_name not in component_names:
            component_names.append(bifrost_name)
        if env not in conda_envs:
            conda_envs.append(env)

    return component_names, conda_envs


# -----------------------------
# Config creation helpers
# -----------------------------

def build_config_from_docs(
    docs: List[Dict[str, Any]],
    institution_arg: Optional[str],
    year_arg: Optional[str],
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

    # Stage for conda envs
    stage = os.environ.get("BIFROST_STAGE", "dev")

    # Collect all components from all docs
    comp_map = collect_components_from_docs(docs)

    # Apply component selection rules
    component_names, conda_envs = select_components(
        comp_map,
        include_components=selected_components,
        exclude_components=excluded_components,
        stage=stage,
    )

    # Collect per-sample metadata
    institutions: List[str] = []
    years: List[str] = []
    runnames: List[str] = []
    sample_names: List[str] = []

    for doc in docs:
        sample_info = (
            doc.get("categories", {})
               .get("sample_info", {})
               .get("summary", {})
        )

        # Institution
        if institution_arg:
            inst = institution_arg
        else:
            inst = sample_info.get("institution", "ssi")
        institutions.append(inst)

        # Year
        if year_arg:
            year_val = year_arg
        else:
            seq_date = sample_info.get("sequence_run_date", "")
            year_val = seq_date[:4] if len(seq_date) >= 4 else str(datetime.datetime.now().year)
        years.append(year_val)

        # runname and sample_names
        db_name_field = doc.get("name", "")
        sample_name_field = sample_info.get("sample_name", db_name_field)

        runnames.append(sample_name_field)
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

    # Config-related arguments
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
        help="Institution for config. If omitted, taken from documents if available."
    )

    parser.add_argument(
        "--year",
        help="Year for config. If omitted, taken from documents if available."
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

    # Validate component/exclude combination
    if args.components and args.exclude:
        raise ValueError("You cannot use --components and --exclude together. Choose one mode.")

    if not args.dbkey:
        raise RuntimeError("No MongoDB key provided and BIFROST_DB_KEY is not set.")

    client = MongoClient(args.dbkey)

    if not ping_database(client):
        raise RuntimeError("Failed to connect to MongoDB.")
    else:
        print("Successfully connected to MongoDB.")

    # -----------------------------
    # MODE 1: List all DBs
    # -----------------------------
    if args.dbname == "__LIST__":
        dbs = list_databases(client)
        print("Available databases:")
        for d in dbs:
            print(f"- {d}")

        if args.json:
            save_json(dbs, args.json)
            print(f"Saved database list to {args.json}")
        return

    # -----------------------------
    # MODE 2: List collections in a DB
    # -----------------------------
    if args.dbname and args.collectionname == "__LIST__":
        collections = list_collections(client, args.dbname)
        print(f"Available collections in {args.dbname}:")
        for c in collections:
            print(f"- {c}")
        
        if args.json:
            save_json(collections, args.json)
            print(f"Saved collection list to {args.json}")
        return

    # -----------------------------
    # MODE 3: Run a query (multi-sample) and optionally create config
    # -----------------------------
    if args.dbname and args.collectionname and args.query:
        query_dict = parse_query_string(args.query)
        results = run_find_many(client, args.dbname, args.collectionname, query_dict)

        print(f"Query matched {len(results)} document(s).")

        if args.json:
            save_json(results, args.json)
            print(f"Saved query results to {args.json}")

        if args.create_config:
            if not results:
                raise RuntimeError("No documents found for query; cannot create config.")
            config = build_config_from_docs(
                results,
                institution_arg=args.institution,
                year_arg=args.year,
                nodes=args.nodes,
                ppn=args.ppn,
                memory=args.memory,
                walltime=args.walltime,
                selected_components=args.components,
                excluded_components=args.exclude,
            )
            save_config_yaml(config, args.output)

        return

    # -----------------------------
    # If user gave insufficient arguments
    # -----------------------------
    print("No valid mode selected. Use --help for usage details.")


if __name__ == "__main__":
    main()

