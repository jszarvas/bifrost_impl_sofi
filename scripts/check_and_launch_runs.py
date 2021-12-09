import os
import sys
import re
import subprocess
from typing import Set, List, Dict
from pathlib import Path

from cs_tools.sample_container import SampleContainer

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
    /usr/local/bin/qsub -W umask=002 -W group_list=fvst_admins -N "bf_launch_{run_name}" -e {log_dir} -o {log_dir} -F "{institution} {year} {run_name} {settings_dir}" {script_dir}/launch_bifrost.sh '
    process: subprocess.Popen = subprocess.Popen(command,
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.STDOUT,
                                                 shell=True,
                                                 env=os.environ)
    process_out, process_err = process.communicate()
    sys.stdout.write(str(process_out))
    sys.stderr.write(str(process_err))

def launch_chewiesnake(script_dir: Path, species_dir: Path, log_dir: Path) -> None:
    sample_list = Path(species_dir, "sample_list.tsv")
    if args['chewiesnake_dryrun'] == 'True':
        print("Running ChewieSnake with --dryrun option.")
        command: str = f'cd {species_dir};\
        /usr/local/bin/qsub -W umask=002,group_list=fvst_admins -N "cs_{species_dir.name[:12]}" -e {log_dir} -o {log_dir} -F "{str(sample_list)} --dryrun" {str(script_dir)}/cs_tools/run_chewiesnake.sh'
    else:
        command: str = f'cd {species_dir};\
        /usr/local/bin/qsub -W umask=002 -W group_list=fvst_admins -N "cs_{species_dir.name[:12]}" -e {log_dir} -o {log_dir} -F "{str(sample_list)}" {str(script_dir)}/cs_tools/run_chewiesnake.sh'
    print("Command:", command)
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

    # chewieSnake
    print()
    print("Update ChewieSnake sample lists")
    script_dir = Path(args["script_dir"])
    log_dir = Path(args["log_dir"])
    species_to_run = ('Salmonella_enterica',)
    for species in species_to_run:
        print(f"Update sample list for {species}")
        species_dir = Path(args["chewiesnake_config_dir"], species)
        sample_list = Path(species_dir, "sample_list.tsv")
        container = SampleContainer(species, sample_list)
        for institution, year, run_name in to_run:
            fastq_dir = Path(args["raw_data_dir"], institution, year, run_name)
            print()
            print(f"Update {species} sample list with samples from {institution}/{year}/{run_name}")
            if container.maintain(fastq_dir):
                print(f"Sample list update function succeeded for {institution}/{year}/{run_name}")
            else:
                print(f"Sample list update function failed for {institution}/{year}/{run_name}")
    
        print(f"Finished updating sample list for {species}")
        print()
        print(f"Check if it's OK to run ChewieSnake for {species} at this point")
        try:
            with open(species_dir.joinpath('output').joinpath('pipeline_status.txt')) as pipeline_status:
                status, date = pipeline_status.readline().split('\t')
        except FileNotFoundError:
                status = 'pipeline_status.txt not found'
        if status != 'running':
            print(f"Pipeline status OK - submit chewieSnake job for {species}")
            launch_chewiesnake(script_dir, species_dir, log_dir)
        else:
            print(f"A ChewieSnake pipeline appears to be running for {species} already - skipping this step.")

if __name__ == '__main__':

    # args: argparse.Namespace = cmdline_args()
    args: Dict = {
        "raw_data_dir": os.environ["BIFROST_RAW_DATA_MNT"],
        "output_dir": os.environ["BIFROST_OUTPUT_DIR"],
        "config_dir": os.environ["BIFROST_CONFIG_DIR"],
        "settings_dir": os.environ["BIFROST_SETTINGS_DIR"],
        "script_dir": os.environ["BIFROST_SCRIPT_DIR"],
        "log_dir": os.environ["BIFROST_LOG_DIR"],
        "chewiesnake_config_dir": os.environ["CHEWIESNAKE_CONFIG_DIR"],
        "chewiesnake_dryrun": os.environ["CHEWIESNAKE_DRYRUN"],
    }
    main(args)
