import os
import sys
import re
import subprocess
from typing import Set, List, Dict
from pathlib import Path


def launch_bifrost(script_dir: str, log_dir: str, settings_dir: str, institution: str, year: str, run_name: str) -> None:
    command: str = f'cd {script_dir};\
    /usr/local/bin/qsub -W umask=002 -W group_list=fvst_admins -N "bf_launch_{run_name}" -e {log_dir} -o {log_dir} -F "{institution} {year} {run_name} {settings_dir}" {script_dir}/launch_bifrost.sh '
    process: subprocess.Popen = subprocess.Popen(command,
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.STDOUT,
                                                 shell=True,
                                                 env=os.environ)
    process_out, process_err = process.communicate()
    sys.stdout.write(str(process_out))
    sys.stderr.write(str(process_err))

def get_year_folders(dirname):
    year_run_folders = []
    for year in os.listdir(dirname):
        # Will stop working on 2100, sorry.
        if re.match("20\d\d", year) is not None:
            year_path = os.path.join(dirname, year)
            for run_folder in os.listdir(year_path):
                # If run folders should be filtered, do it here
                year_run_folders.append((year, run_folder))
    return year_run_folders # List of [(year, run_folder)]

def get_institution_year_folders(dirname):
    institution_year_run_folders = []
    for institution in os.listdir(dirname):
        institution_path = os.path.join(dirname, institution)
        if os.path.isdir(institution_path):
            for year in os.listdir(institution_path):
                if re.match("20\d\d", year) is not None:
                    year_path = os.path.join(institution_path, year)
                    for list_item in os.listdir(year_path):
                        # If run folders should be filtered, do it here
                        institution_year_run_folders.append((institution, year, list_item))
    return institution_year_run_folders # List of [(institution, year, run_folder)]

def main(args: Dict) -> None:
    seqs: Set = set(get_institution_year_folders(args["raw_data_dir"]))
    output: Set = set(get_institution_year_folders(args["output_dir"]))
    # Code here checks if output folder has "complete.txt", but this
    # would trigger runs to start again if they haven't finished. So we 
    # just check if they exist.

    # for run_name in os.listdir(args["output_dir"]):
    #     run_dir: Text = os.path.join(args["output_dir"], run_name)
    #     if os.path.isfile(os.path.join(run_dir, "complete.txt")):
    #         output.add(run_name)

    # Bifrost
    print()
    print("Start Bifrost pipeline")
    print("Raw data folders:")
    for institution, year, run in seqs:
        print(f"{institution}\t{year}\t{run}")
    print("Existing Bifrost output folders:")
    for institution, year, run in output:
        print(f"{institution}\t{year}\t{run}")
    to_run: List = list(seqs - output)
    print()
    print("Running Bifrost with these folders:")
    for institution, year, run_name in to_run:
        print(f"{institution}\t{year}\t{run_name}")
        launch_bifrost(args["script_dir"], args["log_dir"], args["settings_dir"], institution, year, run_name)


if __name__ == '__main__':

    # args: argparse.Namespace = cmdline_args()
    args: Dict = {
        "raw_data_dir": os.environ["BIFROST_RAW_DATA_MNT"],
        "output_dir": os.environ["BIFROST_OUTPUT_DIR"],
        "config_dir": os.environ["BIFROST_CONFIG_DIR"],
        "settings_dir": os.environ["BIFROST_SETTINGS_DIR"],
        "script_dir": os.environ["BIFROST_SCRIPT_DIR"],
        "log_dir": os.environ["BIFROST_LOG_DIR"],
    }
    main(args)
