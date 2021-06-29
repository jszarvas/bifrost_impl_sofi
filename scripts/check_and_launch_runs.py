import os
import sys
import re
# import argparse
import subprocess
from typing import Set, List, Text, Dict


# def cmdline_args() -> argparse.Namespace:

#     def dir_path(path) -> bool:
#         if os.path.isdir(path):
#             return path
#         else:
#             raise argparse.ArgumentTypeError(f"readable_dir:{path} is not a valid path")

#     # Make parser object
#     p: argparse.ArgumentParser = argparse.ArgumentParser(description=("This script will detect new runs in the "
#                                                                       "runs folder and run them through bifrost."))

#     # p.add_argument("required_positional_arg",
#     #                help="desc")
#     p.add_argument("config_dir", type=dir_path,
#                    help="path to KMA config /home/projects/***/apps/bifrost_config")
#     # p.add_argument("output_dir", type=dir_path,
#     #                help="path to output directory", default="./runs")
#     # p.add_argument("sequences_dir", type=dir_path,
#     #                help="path to directory that contains directories of sequences (runs)", default="./seqdata")
#     # p.add_argument("--on", action="store_true",
#     #                help="include to enable")
#     # p.add_argument("-v", "--verbosity", type=int, choices=[0,1,2], default=0,
#     #                help="increase output verbosity (default: %(default)s)")
#     # group1 = p.add_mutually_exclusive_group(required=True)
#     # group1.add_argument('--enable',action="store_true")
#     # group1.add_argument('--disable',action="store_false")

#     return(p.parse_args())


def launch_bifrost(script_dir: str, log_dir: str, settings_dir: str, institution: str, year: str, run_name: str) -> None:
    command: str = f'cd {script_dir};\
 qsub -W umask=002 -N "bf_launch_{run_name}" -e {log_dir} -o {log_dir} -F "{institution} {year} {run_name} {settings_dir}" {script_dir}/launch_bifrost.sh '
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
                    for run_folder in os.listdir(year_path):
                        # If run folders should be filtered, do it here
                        institution_year_run_folders.append((institution, year, run_folder))
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

    print("Runs in raw_data folder:")
    for institution, year, run in seqs:
        print(f"{institution}\t{year}\t{run}")
    print("Runs in output folder:")
    for institution, year, run in output:
        print(f"{institution}\t{year}\t{run}")
    to_run: List = list(seqs - output)
    print("Running:")
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
