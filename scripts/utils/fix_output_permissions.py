import os
import sys
import re
import subprocess
from shutil import rmtree
from typing import Set, List, Dict
from pathlib import Path

def get_institution_year_folders(dirname):
    institution_year_run_folders = []
    for institution in os.listdir(dirname):
        institution_path = os.path.join(dirname, institution)
        if os.path.isdir(institution_path):
            for year in os.listdir(institution_path):
                if re.match("20\d\d", year) is not None:
                    year_path = os.path.join(institution_path, year)
                    for run_folder in os.listdir(year_path):
                        institution_year_run_folders.append((institution, year, run_folder))
    return institution_year_run_folders # List of [(institution, year, run_folder)]

def fix_permissions(dirname: Path) -> None:
    try:
        os.chmod(dirname,0o775)
    except Exception:
        print("Could not fix permissions on " + str(dirname), file=sys.stderr)

def main(args: Dict) -> None:
    print("Fixing permissions")
    output_dirs: List = get_institution_year_folders(args["output_dir"])
    for dir_elements in output_dirs:
        fix_permissions(Path(args["output_dir"],*dir_elements))

if __name__ == '__main__':
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
