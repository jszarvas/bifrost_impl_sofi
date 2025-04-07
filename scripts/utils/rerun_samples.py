import os
import sys
import re
from shutil import rmtree
from typing import List, Dict
from pathlib import Path
from subprocess import run
from utils import (
    complain, die, marked_for_rerun, lock, unlock,
    mark_for_cleanup, remove_clean_mark
)

from subprocess import run

def submit_rerun(dirname: Path, samples: str):
    """
    Submit a rerun job using qsub. Assumes the structure (institution/year/run).
    """
    try:
        parts = dirname.parts[-3:]  # Extract institution, year, and run folder
        if len(parts) != 3:
            raise ValueError("Invalid directory structure for rerun submission")
        inst, year, rundir = parts
        run(['/usr/local/bin/qsub', '-F', f"{inst} {year} {rundir} {samples}", 'rerun_samples.sh'])
    except ValueError as e:
        print(f"Error: {e}")

def search_institution_year_folders(dirname: Path, func):
    institution_year_run_folders = []
    for institution in os.listdir(dirname):
        institution_path = Path(dirname, institution)
        if os.path.isdir(institution_path):
            for year in os.listdir(institution_path):
                if re.match(r"20\d\d", year) is not None:
                    year_path = Path(institution_path, year)
                    for run_folder in os.listdir(year_path):
                        folder = Path(year_path, run_folder)
                        if func(folder):
                            institution_year_run_folders.append(folder)
    return institution_year_run_folders

def rerun(directory: Path):
    if marked_for_rerun(directory) and lock(directory):
        try:
            rerun_samples = []
            with open(str(directory) + ".rerun", 'r') as fh:
                for sample_id in fh:
                    sample_dir = Path(directory, sample_id.strip())
                    mark_for_cleanup(sample_dir)
                    clean_up_dir(sample_dir)
                    rerun_samples.append(sample_id.strip())
            
            try:
                rerun_samples = [x.split('___')[-1].strip() for x in rerun_samples]
            except IndexError:
                pass
            
            submit_rerun(directory, ",".join(rerun_samples))
        finally:
            unlock(directory)

def process_reruns(output_dir: Path):
    print(f"Cleaning up runs in {output_dir}.")
    rerun_dirs: List = search_institution_year_folders(output_dir, marked_for_rerun)
    
    if not rerun_dirs:
        print(f"No rerun folders found in {output_dir}.")

    for rerun_dir in rerun_dirs:
        rerun(rerun_dir)

def main():
    output_dirs = [
        Path(os.environ["BIFROST_OUTPUT_DIR"]),
        Path(os.environ["BIFROST_ASM_OUTPUT_DIR"])
    ]

    for output_dir in output_dirs:
        process_reruns(output_dir)

if __name__ == '__main__':
    main()
