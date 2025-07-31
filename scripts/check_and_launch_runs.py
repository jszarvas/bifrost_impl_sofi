#!/usr/bin/env python3
import os
import sys
import re
import subprocess
from typing import Set, List, Dict
from pathlib import Path
import logging
from datetime import datetime
#import json
#import hashlib
#from Bio import SeqIO
#from bson import ObjectId
#from pymongo import MongoClient
#from pymongo.server_api import ServerApi

def setup_logging(log_dir: str, script_name: str):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    script_basename = os.path.splitext(os.path.basename(script_name))[0]

    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)

    # Construct log file path correctly
    log_file = os.path.join(log_dir, f"bifrost_script_{script_basename}.log")

    # Get root logger
    logger = logging.getLogger()

    # Remove all handlers to reset logging to a new file
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])

    # Set up logging with a new file for each run
    logging.basicConfig(
        filename=log_file,
        filemode="a",  # Append mode
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )

    # Add console logging
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

    logging.info(f"Logging started for {log_file}")

def has_metadata(institution: str, year: str, run_name: str, raw_data_dir: str) -> bool:
    data_dir = Path(raw_data_dir, institution, year, run_name)
    for ext in ("xlsx", "tsv"):
        metadata = data_dir/f"sofi_metadata.{ext}"
        if metadata.exists():
            return True
    return False

def launch_bifrost(script_dir: str, log_dir: str, settings_dir: str, institution: str, year: str, run_name: str, script_name) -> None:
    bifrost_qsub_options=os.environ.get("BIFROST_QSUB_OPTIONS")
    job_name = f"launch_bifrost_sh_{run_name}"
    #script_name = "launch_bifrost.sh"

    command = f'cd {script_dir};\
    /usr/local/bin/qsub {bifrost_qsub_options} -N "{job_name}" -e {log_dir} -o {log_dir} \
    -F "{institution} {year} {run_name} {settings_dir}" {script_dir}/{script_name}'

    #print(f"the sequencing command is {command}")
    logging.info(f"Submitting sequencing job: {command}")

    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               shell=True,
                               env=os.environ)
    process_out, process_err = process.communicate()

    if process.returncode == 0:
        logging.info(f"Sequencing job {job_name} submitted successfully.")
    else:
        logging.error(f"Error submitting sequencing job {job_name}: {process_err.decode().strip()}")

def get_institution_year_folders(dirname):
    institution_year_run_folders = []
    for institution in os.listdir(dirname):
        institution_path = os.path.join(dirname, institution)
        if os.path.isdir(institution_path):
            for year in os.listdir(institution_path):
                if re.match(r"20\d\d", year) is not None:
                    year_path = os.path.join(institution_path, year)
                    for list_item in os.listdir(year_path):
                        # If run folders should be filtered, do it here
                        institution_year_run_folders.append((institution, year, list_item))
    return institution_year_run_folders # List of [(institution, year, run_folder)]

def main_seq(args: Dict) -> None:
    seqs: Set = set(get_institution_year_folders(args["raw_data_dir"]))
    output: Set = set(get_institution_year_folders(args["output_dir"]))
    to_run: List = list(seqs - output)
    logging.info(f"output is : {output}")
    # Bifrost

    logging.info("\n===== Starting Bifrost Sequencing pipeline =====")
    logging.info("Raw sequencing data folders:")

    for institution, year, run in seqs:
        logging.info(f"{institution}\t{year}\t{run}")
   
    #print("Existing Bifrost output folders:")
    logging.info("Existing Bifrost output folders:")
    for institution, year, run in output:
        logging.info(f"{institution}\t{year}\t{run}")#print(f"{institution}\t{year}\t{run}")
    
    logging.info("Running Bifrost with these folders:")#print("Running Bifrost with these folders:")
    for institution, year, run_name in to_run:
        if has_metadata(institution, year, run_name, args["raw_data_dir"]):
            tmp_folder = os.path.join(args["output_dir"], institution, year, run_name)
            os.makedirs(tmp_folder, exist_ok=True)  # Ensure directory exists
            setup_logging(tmp_folder, sys.argv[0])
            logging.info(f"{institution}\t{year}\t{run_name}")
            script_name = "launch_bifrost.sh"
            launch_bifrost(args["script_dir"], tmp_folder, args["settings_dir"], institution, year, run_name,script_name)
        else:
            logging.info(f"{institution}\t{year}\t{run_name}\tSkipping (no metadata found)")

def main_asm(args: Dict) -> None:
    asm: Set = set(get_institution_year_folders(args["raw_data_dir"]))
    output: Set = set(get_institution_year_folders(args["output_dir"]))
    to_run: List = list(asm - output)
    # Bifrost

    
    logging.info("\n===== Starting Bifrost Assembly pipeline =====")
    logging.info("Assembly data folders:")

    for institution, year, run in asm:
        logging.info(f"{institution}\t{year}\t{run}")
    #    print(f"{institution}\t{year}\t{run}")

    logging.info("Existing Bifrost assembly output folders:")
    for institution, year, run in output:
        logging.info(f"{institution}\t{year}\t{run}")

    logging.info("Running Bifrost assembly with these folders:")
    for institution, year, run_name in to_run:
        if has_metadata(institution, year, run_name, args["raw_data_dir"]):
            tmp_folder = os.path.join(args["output_dir"], institution, year, run_name)
            os.makedirs(tmp_folder, exist_ok=True)  # Ensure directory exists
            setup_logging(tmp_folder, sys.argv[0])
            logging.info(f"{institution}\t{year}\t{run_name}")
            script_name = "launch_bifrost_asm.sh"
            launch_bifrost(args["script_dir"], tmp_folder, args["settings_dir"], institution, year, run_name,script_name)
        else:
            logging.info(f"{institution}\t{year}\t{run_name}\tSkipping (no metadata found)")

if __name__ == '__main__':
   
    # args: argparse.Namespace = cmdline_args()

    setup_logging(os.environ["BIFROST_OUTPUT_DIR"],sys.argv[0])
    
    args: Dict = {
        "raw_data_dir": os.environ["BIFROST_RAW_DATA_MNT"],
        "output_dir": os.environ["BIFROST_OUTPUT_DIR"],
        "config_dir": os.environ["BIFROST_CONFIG_DIR"],
        "settings_dir": os.environ["BIFROST_SETTINGS_DIR"],
        "script_dir": os.environ["BIFROST_SCRIPT_DIR"],
        "log_dir": os.environ["BIFROST_LOG_DIR"],
    }
    
    #print(f"running main sequencing pipeline with data dir : {os.environ['BIFROST_RAW_DATA_MNT']} and output dir: {os.environ['BIFROST_OUTPUT_DIR']}")
    logging.info(f"running main sequencing pipeline with data dir : {os.environ['BIFROST_RAW_DATA_MNT']} and output dir: {os.environ['BIFROST_OUTPUT_DIR']}")
    main_seq(args)
    print(f"Done running main sequencing pipeline")

    setup_logging(os.environ["BIFROST_ASM_OUTPUT_DIR"],sys.argv[0])

    args_asm: Dict = {
        "raw_data_dir": os.environ["BIFROST_ASM_DATA_MNT"],
        "output_dir": os.environ["BIFROST_ASM_OUTPUT_DIR"],
        "config_dir": os.environ["BIFROST_CONFIG_DIR"],
        "settings_dir": os.environ["BIFROST_SETTINGS_DIR"],
        "script_dir": os.environ["BIFROST_SCRIPT_DIR"],
        "log_dir": os.environ["BIFROST_LOG_DIR"],
    }

    #print(f"running main assembly pipeline with data dir : {os.environ['BIFROST_ASM_DATA_MNT']} and output dir: {os.environ['BIFROST_ASM_OUTPUT_DIR']}")
    logging.info(f"running main assembly pipeline with data dir : {os.environ['BIFROST_ASM_DATA_MNT']} and output dir: {os.environ['BIFROST_ASM_OUTPUT_DIR']}")

    main_asm(args_asm)
    print(f"Done running main assembly pipeline")
