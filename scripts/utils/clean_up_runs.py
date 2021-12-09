import os
import sys
import re
import subprocess
from shutil import rmtree
from typing import Set, List, Dict
from pathlib import Path

def complain(message):
    print(message, file=sys.stderr)

def die(message, code=1):
    print(message, file=sys.stderr)
    sys.exit(code)

def get_institution_year_folders_to_remove(dirname: Path):
    institution_year_run_folders = []
    for institution in os.listdir(dirname):
        institution_path = os.path.join(dirname, institution)
        if Path.isdir(institution_path):
            for year in os.listdir(institution_path):
                if re.match("20\d\d", year) is not None:
                    year_path = os.path.join(institution_path, year)
                    for run_folder in os.listdir(year_path):
                        if marked_for_cleanup(os.path.join(year_path, run_folder)):
                            institution_year_run_folders.append((institution, year, run_folder))
    return institution_year_run_folders # List of [(institution, year, run_folder)]

def marked_for_cleanup(dirname):
    return os.path.exists(str(dirname) + ".remove")

def remove_mark(dirname):
    try:
        os.remove(str(dirname) + ".remove")
    except PermissionError:
        complain(f"Failed to remove {dirname}.remove: Permission denied")

def locked(dirname):
    return os.path.exists(str(dirname) + ".remove.lock")

def lock(dirname):
    if not locked(dirname):
        try:
            Path(str(dirname) + ".remove.lock").touch()
            return True
        except Exception:
            return False
    else:
        return False

def unlock(dirname):
    try:
        os.remove(str(dirname) + ".remove.lock")
    except Exception:
        complain("Failed to remove lock: " + str(dirname) + ".remove.lock")

def clean_up_dir(dirname: Path) -> None:
    if marked_for_cleanup(dirname) and lock(dirname):
        try:
            rmtree(dirname)
            remove_mark(dirname)
        except PermissionError:
            f"Failed to remove {dirname}: Permission denied"
        finally:
            unlock(dirname)

def main(args: Dict) -> None:
    print("Cleaning up.")
    clean_up_dirs: List = get_institution_year_folders_to_remove(args["output_dir"])
    for dir_elements in clean_up_dirs:
        clean_up_dir(Path(args["output_dir"],*dir_elements))

if __name__ == '__main__':
    args: Dict = {
        "output_dir": os.environ["BIFROST_OUTPUT_DIR"],
    }
    main(args)
