#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
from typing import Any, Dict, List, Optional

import yaml
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson import ObjectId
import datetime


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
    try:
        return eval(query_str, {"__builtins__": {}})
    except Exception as exc:
        raise ValueError(f"Invalid query string: {exc}")


def list_databases(client: MongoClient) -> List[str]:
    return client.list_database_names()


def list_collections(client: MongoClient, dbname: str) -> List[str]:
    return client[dbname].list_collection_names()


def run_find_one(
    client: MongoClient,
    dbname: str,
    collection: str,
    query: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    return client[dbname][collection].find_one(query)


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
# Config creation helpers
# -----------------------------

def extract_components(
    doc: Dict[str, Any],
    selected_components: Optional[List[str]],
    stage: str
) -> Dict[str, List[str]]:
    """
    From a sample document, extract component_names and conda_envs.

    - components[*].name like "min_read_check__v2.2.8"
    - short name: "min_read_check"
    - version: "v2.2.8"
    - component_names: ["bifrost_min_read_check", ...]
    - conda_envs: ["bifrost_<stage>_min_read_check_v2.2.8", ...]
    """
    components = doc.get("components", [])
    comp_names: List[str] = []
    conda_envs: List[str] = []

    for comp in components:
        full_name = comp.get("name")
        if not full_name:
            continue

        if "__" in full_name:
            short, version = full_name.split("__", 1)
        else:
            short = full_name
            version = "v1.0.0"

        if selected_components:
            if short not in selected_components:
                continue

        bifrost_name = f"bifrost_{short}"
        if bifrost_name not in comp_names:
            comp_names.append(bifrost_name)

        env = f"bifrost_{stage}_{short}_{version}"
        if env not in conda_envs:
            conda_envs.append(env)

    return {"component_names": comp_names, "conda_envs": conda_envs}


def build_config_from_doc(
    doc: Dict[str, Any],
    institution_arg: Optional[str],
    year_arg: Optional[str],
    nodes: int,
    ppn: int,
    memory: str,
    walltime: str,
    selected_components: Optional[List[str]],
) -> Dict[str, Any]:
    # Stage for conda envs
    stage = os.environ.get("BIFROST_STAGE", "dev")

    # Components
    comp_info = extract_components(doc, selected_components, stage)
    component_names = comp_info["component_names"]
    conda_envs = comp_info["conda_envs"]

    # Institution and year
    sample_info = (
        doc.get("categories", {})
           .get("sample_info", {})
           .get("summary", {})
    )

    if institution_arg:
        institution = [institution_arg]
    else:
        inst = sample_info.get("institution", "ssi")
        institution = [inst]

    if year_arg:
        year = [year_arg]
    else:
        seq_date = sample_info.get("sequence_run_date", "")
        year_val = seq_date[:4] if len(seq_date) >= 4 else str(datetime.datetime.now().year)
        year = [year_val]

    # runname and sample_names
    # According to your mapping:
    # - name (db) -> sample_names (config)
    # - categories.sample_info.summary.sample_name -> runname
    db_name_field = doc.get("name", "")
    sample_name_field = sample_info.get("sample_name", db_name_field)

    runname = [sample_name_field]
    sample_names = [db_name_field]

    resources = {
        "nodes": nodes,
        "ppn": ppn,
        "memory": memory,
        "walltime": walltime,
    }

    config = {
        "component_names": component_names,
        "conda_envs": conda_envs,
        "institution": institution,
        "year": year,
        "runname": runname,
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

    parser = argparse.ArgumentParser(description="MongoDB exploration, query, and config tool.")

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
        help="MongoDB find_one query as a Python dict string."
    )

    parser.add_argument(
        "--json",
        help="Output JSON file to store results."
    )

    # Config-related arguments
    parser.add_argument(
        "--create_config",
        action="store_true",
        help="If set, create a YAML config from the queried document."
    )

    parser.add_argument(
        "--components",
        type=lambda s: [x.strip() for x in s.split(",")],
        help="Comma-separated list of short component names to include (e.g. min_read_check,assemblatron). "
             "If omitted, all components in the document are used."
    )

    parser.add_argument(
        "--institution",
        help="Institution for config. If omitted, taken from document if available."
    )

    parser.add_argument(
        "--year",
        help="Year for config. If omitted, taken from document if available."
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
    # MODE 3: Run a query (and optionally create config)
    # -----------------------------
    if args.dbname and args.collectionname and args.query:
        query_dict = parse_query_string(args.query)
        result = run_find_one(client, args.dbname, args.collectionname, query_dict)

        #print("Query result:")
        #print(result)

        if args.json:
            save_json(result, args.json)
            print(f"Saved query result to {args.json}")
        else:
            print("Query result:")
            print(result)
        
        if args.create_config:
            if not result:
                raise RuntimeError("No document found for query; cannot create config.")
            config = build_config_from_doc(
                result,
                institution_arg=args.institution,
                year_arg=args.year,
                nodes=args.nodes,
                ppn=args.ppn,
                memory=args.memory,
                walltime=args.walltime,
                selected_components=args.components,
            )
            save_config_yaml(config, args.output)

        return

    # -----------------------------
    # If user gave insufficient arguments
    # -----------------------------
    print("No valid mode selected. Use --help for usage details.")


if __name__ == "__main__":
    main()
