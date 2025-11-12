import argparse
import yaml
import os
from typing import List, Tuple, Dict, TypedDict
from datetime import datetime
import pymongo
from pymongo.errors import PyMongoError
class ResourcesDict(TypedDict):
    nodes: int
    ppn: int
    memory: str
    walltime: str

### DATABASE CONNECTION

def get_database_names(mongo_client: "pymongo.MongoClient"):
    """Return a list of database names."""
    return mongo_client.list_database_names()

def get_collection_names(mongo_client: "pymongo.MongoClient", database: str):
    """Return a list of collection names in a given database."""
    db = mongo_client.get_database(database)
    return db.list_collection_names()

def print_components_by_status(
    mongo_client,
    db_name: str,
    status_value: str,
    limit: int = 10
) -> None:
    """
    From 'sample_components', print up to `limit` entries whose top-level
    `status` equals `status_value`. For each, print `component.name` and
    `sample.name`. Sorted by metadata.updated_at desc if available.
    """

    db = mongo_client.get_database(db_name)
    col = db.get_collection("sample_components")

    filt = {"status": status_value} #value to filter status on
    #projection to identify entries within a collection
    proj = {
        "_id": 0,
        "component.name": 1,
        "sample.name": 1,
        "metadata.updated_at": 1,
    }

    try:
        """
        col.find(filt, projection=proj) : query mongoDB documents matching the status filtering - returning only the fields defined in the projection

        sort([("metadata.updated_at", -1)]) : orders results by the metadata updated field to show the newst first

        limit : for printing purpose during the devolpment phase
        """
        cursor = col.find(filt, projection=proj).sort([("metadata.updated_at", -1)]).limit(limit)
    except Exception:
        # if sort key doesn't exist on the collection, fall back to unsorted
        cursor = col.find(filt, projection=proj).limit(limit)

    count = 0
    for count, doc in enumerate(cursor, start=1):
        comp_name = (doc.get("component") or {}).get("name", "<component.name missing>")
        samp_name = (doc.get("sample") or {}).get("name", "<sample.name missing>")
        print(f"[{count}] component.name: {comp_name} - sample.name: {samp_name}")
              
    if count == 0:
        print(f"No documents in 'sample_components' with status == '{status_value}'.")  

### SEARCH HELPER FUNCTIONS

def find_runname(base_dir: str, institution: str, year: str, run_id: str) -> str:
    """
    Search for a folder containing run_id inside $BIFROST_OUTPUT_DIR/{institution}/{year}/.
    """
    search_path = os.path.join(base_dir, institution, year)
    print(f"Searching for run_id '{run_id}' in {search_path}")

    if not os.path.exists(search_path):
        raise FileNotFoundError(f"Directory {search_path} does not exist.")

    for folder in os.listdir(search_path):
        if run_id in folder:
            print(f"Found matching runname: {folder} in year {year}")
            return folder

    raise FileNotFoundError(f"No folder containing '{run_id}' found in {search_path}.")

def find_runname_by_runno(base_dir: str, institution: str, year: str, run_no: str) -> Tuple[List[str], List[str]]:
    """
    Find all folders matching *_N_WGS_{run_no}_* inside $BIFROST_OUTPUT_DIR/{institution}/{year}/ and return their subfolders as samples.
    """
    search_path = os.path.join(base_dir, institution, year)
    print(f"Searching for run_no '{run_no}' in {search_path}")

    if not os.path.exists(search_path):
        raise FileNotFoundError(f"Directory {search_path} does not exist.")

    matching_runs = [folder for folder in os.listdir(search_path) if f"N_WGS_{run_no}_" in folder]

    if not matching_runs:
        raise FileNotFoundError(f"No folder containing 'N_WGS_{run_no}_' found in {search_path}.")

    sample_names = []
    for run in matching_runs:
        full_path = os.path.join(search_path, run)
        if os.path.isdir(full_path):
            subfolders = [
                f for f in os.listdir(full_path) 
                if os.path.isdir(os.path.join(full_path, f)) and f != "samples"
            ]
            sample_names.extend([f"{sub}" for sub in subfolders])

    return matching_runs, sample_names

def create_config_file(
    conda_envs: List[str], 
    component_names: List[str],
    samples: List[str],
    resources: ResourcesDict,
    institution: List[str],
    years: List[str],
    runname: List[str], 
    output_file: str = "config.yaml"
) -> None:
    if len(conda_envs) != len(component_names):
        raise ValueError("--conda_envs and --component_names must have equal length.")

    prefix = "bifrost_"
    stage = f"{os.environ.get('BIFROST_STAGE', 'dev')}_"

    conda_envs_with_stage = [
        f"{prefix}{stage}{comp}_{env}" for comp, env in zip(component_names, conda_envs)
    ]

    config = {
        "component_names": [prefix + name for name in component_names],
        "conda_envs": conda_envs_with_stage,
        "institution": [institution] if isinstance(institution, str) else institution,
        "year": [str(year) for year in years],
        "runname": [runname] if isinstance(runname, str) else runname,
        "sample_names": [samples] if isinstance(samples, str) else samples,
        "resources": resources,
    }

    with open(output_file, "w") as file:
        yaml.dump(config, file, default_flow_style=False)

    print(f"Config file '{output_file}' created successfully.")

def expand_list(param: List[str], count: int) -> List[str]:
    """Ensure single values are applied across all elements."""
    return param * count if len(param) == 1 else param

def extract_run_id(sequence_ID: str, institution: str) -> str:
    """
    Extracts the correct run_id from sequence_ID based on institution.
    
    - If sequence_ID contains "SSI", take parts from 2nd to 4th underscore.
    - If institution is FVST, take the last underscore-separated part.
    - Otherwise, default to taking everything after the first underscore.

    #based on sofi.platform.dk production information

    """
    parts = sequence_ID.split("_")

    if "SSI" in sequence_ID:
        if len(parts) >= 4:
            return "_".join(parts[1:4])  # Extract 2nd, 3rd, and 4th elements
        else:
            raise ValueError(f"Invalid sequence_ID format for SSI: {sequence_ID}")

    elif institution and "FVST" in institution:
        return parts[-1]  # Extract last element

    else:
        return "_".join(parts[1:])  # Default case


def main():
    parser = argparse.ArgumentParser(description="Create a YAML configuration file.", add_help=True)

    # Required options for folder search
    parser.add_argument("--conda_envs", type=lambda s: s.split(","), required=True, help="Comma-separated list of conda environments.")
    parser.add_argument("--component_names", type=lambda s: s.split(","), required=True, help="Comma-separated list of component names.")

    # Optional options for folder search
    parser.add_argument("--institution", type=lambda s: s.split(","), default=["ssi"], help="Institution name. Defaults to 'ssi'.")
    parser.add_argument("--years", type=lambda s: s.split(","), default=[str(datetime.now().year)], help="Specify the year(s).")

    # Optional options for resource management
    parser.add_argument("--nodes", type=int, default=1, help="Number of nodes for qsub (default: 1).")
    parser.add_argument("--ppn", type=int, default=4, help="Processors per node for qsub (default: 4).")
    parser.add_argument("--memory", type=str, default="2gb", help="Memory allocation for qsub (default: 2gb).")
    parser.add_argument("--walltime", type=str, default="01:00:00", help="Walltime for qsub (default: 01:00:00).")
    parser.add_argument("--output", default="config.yaml", help="Output file name (default: config.yaml).")

    # Different input methods
    parser.add_argument("--sequence_ID", type=lambda s: s.split(","), help="Comma-separated list of sequence IDs.")
    parser.add_argument("--isolate_id", type=lambda s: s.split(","), help="Comma-separated list of isolate IDs.")
    parser.add_argument("--run_id", type=lambda s: s.split(","), help="Comma-separated list of run IDs.")
    parser.add_argument("--run_name", type=lambda s: s.split(","), help="Comma-separated list of run names.")
    parser.add_argument("--sample_names", type=lambda s: s.split(","), help="Comma-separated list of sample names.")
    parser.add_argument("--run_no", type=lambda s: s.split(","), help="Comma-separated list of run numbers (e.g., 910). Requires --institution and --years.")

    # Handle mongoDB connection
    parser.add_argument("--status", type=str,choices=["Failure", "Requirements not met", "Running"],help='Pipeline status. If set, a MongoDB key/URI must be resolvable.')
    parser.add_argument("--mongodb_key", type=lambda s: s.strip() or None, default=None, help="MongoDB key/URI to use directly. If omitted, falls back to --mongodb_envvar.")
    parser.add_argument("--mongodb_envvar", type=str, default="BIFROST_DB_KEY", help="Name of the environment variable that holds the MongoDB key/URI (default: BIFROST_DB_KEY).")
                        
    args = parser.parse_args()

    print(f"default year {args.years} and insitution {args.institution}")
    
    
    # Ensure single institution value applies to all
    if len(args.institution) == 1:
        args.institution = args.institution * len(args.years)

    bifrost_output_dir = os.environ.get("BIFROST_OUTPUT_DIR")
    if not bifrost_output_dir:
        raise EnvironmentError("BIFROST_OUTPUT_DIR is not set.")

    # Resolve connection key to a mongoDB - to estimate the status of the different components
    mongodb_key = None
    if args.status is not None:
    
        if args.mongodb_key:
            mongodb_key = args.mongodb_key
        else:
            mongodb_key = os.environ.get(args.mongodb_envvar)
            if not mongodb_key:
                raise EnvironmentError(f"{args.mongodb_envvar} is not set.")

        print(f"Status is {args.status} with determined mongo db key {mongodb_key}")

        try:
            client = pymongo.MongoClient(
                mongodb_key,
                serverSelectionTimeoutMS=5000,  # 5s timeout for initial handshake
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
            )

            print(f"Succesfully connected with pymongo.client")
            
            db_names = get_database_names(client)
            print(f"connected db_names {db_names}")
            
            if not db_names:
                raise RuntimeError("Connected to MongoDB, but no databases were returned.")

            database = db_names[0]

            print(f"succesfully connected and extract database name {database}")
            # Optionally fetch collections for a quick sanity check (can be commented out)
            try:
                collection_name = get_collection_names(client, database)
                print(f"collections names are {collection_name}")
            except PyMongoError:
                # Collections may require auth/permissions; not fatal for connectivity
                pass

            print("database connection done")

            print(f"First 10 entries from 'sample_components' where status == '{args.status}':")
            print_components_by_status(client, database, args.status, limit=10)
            
        except PyMongoError as e:
            raise RuntimeError(f"Failed to connect to MongoDB when --status Failure: {e}") from e
            
    # Handling cases based on input
    num_elements = None
    
    if args.sequence_ID:
        num_elements = len(args.sequence_ID)

    elif args.isolate_id:
        num_elements = len(args.isolate_id)

    elif args.run_name:
        num_elements = len(args.run_name)

    elif args.sample_names:
        num_elements = len(args.sample_names)

    elif args.run_no:
        num_elements = len(args.run_no)

    else:
        parser.error("You must provide --sequence_ID, --isolate_id with --run_name/--run_id, or --sample_names.")

    input_modes = sum([
        bool(args.sequence_ID),
        bool(args.isolate_id),
        bool(args.sample_names),
        bool(args.run_no)
    ])
    if input_modes != 1:
        parser.error("You must provide exactly one of --sequence_ID, --isolate_id, --sample_names, or --run_no.")

    args.years = expand_list(args.years, num_elements)
    args.institution = expand_list(args.institution, num_elements)

    #Determine runnames and sample_names for four different running modes
    runnames = []
    sample_names = []

    if args.sequence_ID:
        num_elements = len(args.sequence_ID)
        isolate_ids = [seq.split("_")[0] for seq in args.sequence_ID]
        run_ids = [extract_run_id(seq, args.institution[i]) for i, seq in enumerate(args.sequence_ID)]
        runnames = [find_runname(bifrost_output_dir, inst, yr, run_id) for run_id, yr, inst in zip(run_ids, args.years, args.institution)]
        sample_names = [f"{runname}___{iso}" for runname, iso in zip(runnames, isolate_ids)]

    elif args.isolate_id:
        if args.run_id and args.run_name:
            parser.error("You cannot specify both --run_name and --run_id when using --isolate_id. Choose one.")

        if not args.run_name and not args.run_id:
            parser.error("If --isolate_id is provided, you must specify either --run_name or --run_id.")

        if args.run_id:
            if len(args.isolate_id) == len(args.run_id):
                runnames = [find_runname(bifrost_output_dir, inst, yr, run_id) for run_id, yr, inst in zip(args.run_id, args.years, args.institution)]
            else:
                parser.error("If --isolate_id and --run_id are specified, they must be of equal length.")

        else:
            if len(args.isolate_id) == len(args.run_name):
                runnames = args.run_name
            else:
                parser.error("If --isolate_id and --run_name are specified, they must be of equal length.")

        sample_names = [f"{runname}___{iso}" for runname, iso in zip(runnames, args.isolate_id)]

    elif args.sample_names:
        runnames = [sample.split("___")[0] for sample in args.sample_names]
        sample_names = args.sample_names
        num_elements = len(sample_names)
    
    elif args.run_no:
        if len(args.run_no) != 1:
            parser.error("--run_no expects exactly one run number.")
        if len(args.institution) != 1 or len(args.years) != 1:
            parser.error("--run_no mode requires exactly one institution and one year.")

        runnames, sample_names = find_runname_by_runno(
            bifrost_output_dir,
            args.institution[0],
            args.years[0],
            args.run_no[0]
        )
        num_elements = len(sample_names)
        runnames = [runnames[0]] * num_elements
        args.institution = [args.institution[0]] * num_elements
        args.years = [args.years[0]] * num_elements

    else:
        parser.error("You must provide --sequence_ID, --isolate_id with --run_name/--run_id, --sample_names or --run_no.")

    # Ensure correct number of years
    if len(args.years) == 1:
        args.years = args.years * num_elements
    elif len(args.years) != num_elements:
        parser.error(f"--years must have the same number of elements as input ({num_elements}), or one value to apply to all.")

    # Ensure correct number of institutions
    if len(args.institution) == 1:
        args.institution = args.institution * num_elements
    elif len(args.institution) != num_elements:
        parser.error(f"--institution must have the same number of elements as input ({num_elements}), or one value to apply to all.")

    # Create resources dictionary
    resources: ResourcesDict = {
        "nodes": args.nodes,
        "ppn": args.ppn,
        "memory": args.memory,
        "walltime": str(args.walltime),
    }

    # Create YAML config
    create_config_file(
        args.conda_envs,
        args.component_names,
        sample_names,
        resources,
        args.institution,
        args.years,
        runnames,
        args.output
    )

if __name__ == "__main__":
    main()

