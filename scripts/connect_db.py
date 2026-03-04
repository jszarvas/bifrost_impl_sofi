#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
from typing import Any, Dict, List, Optional

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
# Main CLI Logic
# -----------------------------

def main() -> None:
    default_dbkey = os.environ.get("BIFROST_DB_KEY")

    parser = argparse.ArgumentParser(description="MongoDB exploration and query tool.")

    parser.add_argument(
        "--dbkey",
        default=default_dbkey,
        help="Environment variable containing MongoDB URI (default: BIFROST_DB_KEY)."
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

    args = parser.parse_args()

    if not args.dbkey:
        raise RuntimeError("No MongoDB key provided and BIFROST_DB_KEY is not set.")

    client = MongoClient(args.dbkey)

    if not ping_database(client):
        raise RuntimeError("Failed to connect to MongoDB.")
    else:
        print("succesfully connected to MongoDB")
    
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
    # MODE 3: Run a query
    # -----------------------------
    if args.dbname and args.collectionname and args.query:
        query_dict = parse_query_string(args.query)
        result = run_find_one(client, args.dbname, args.collectionname, query_dict)

        if args.json:
            save_json(result, args.json)
            print(f"Saved query result to {args.json}")
        else:
            print("Query result:")
            print(result)
        
        return

    # -----------------------------
    # If user gave insufficient arguments
    # -----------------------------
    print("No valid mode selected. Use --help for usage details.")


if __name__ == "__main__":
    main()
