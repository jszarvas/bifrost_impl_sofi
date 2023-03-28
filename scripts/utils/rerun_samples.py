import os
import sys
import re
from shutil import rmtree
from typing import List, Dict
from pathlib import Path
from subprocess import run

def complain(message):
    print(message, file=sys.stderr)

def die(message, code=1):
    print(message, file=sys.stderr)
    sys.exit(code)

class markedfolder(Path):
    _flavour = type(Path())._flavour  # type: ignore
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs): # args caught by __new__ above
        self.clean_up_mark = Path(str(self) + ".remove")
        self.rerun_mark = Path(str(self) + ".rerun")
        self.lockfile = Path(str(self) + ".lock")
        super().__init__()

    def cleanup(self):
        if self.marked_for_cleanup() and self.lock():
            try:
                rmtree(self)
            except PermissionError:
                complain(f"Failed to remove {self}: Permission denied")
            except FileNotFoundError:
                complain(f"FileNotFoundError: {self} doesn't exist")
            finally:
                self.remove_clean_mark()
                self.unlock()
    def mark_for_cleanup(self):
        try:
            self.clean_up_mark.touch()
        except PermissionError:
            complain(f"Failed to touch {self.clean_up_mark}: Permission denied")
    def remove_clean_mark(self):
        try:
            self.clean_up_mark.unlink()
        except Exception:
            complain("Failed to remove mark: " + str(self.clean_up_mark))
    def marked_for_cleanup(self):
        return self.clean_up_mark.exists()
    def remove_rerun_mark(self):
        try:
            self.rerun_mark.unlink()
        except Exception:
            complain("Failed to remove mark: " + str(self.rerun_mark))

    def marked_for_rerun(self):
        return self.rerun_mark.exists()

    def lock(self):
        try:
            self.lockfile.touch(exist_ok=False)
            return True
        except Exception:
            return False

    def locked(self):
        return self.lockfile.exists()

    def unlock(self):
        try:
            self.lockfile.unlink()
        except Exception:
            complain("Failed to remove lock: " + str(self.lockfile))

    def rerun(self):
        if self.marked_for_rerun() and self.lock():
            try:
                rerun_samples = []
                with open(self.rerun_mark, 'r') as fh:
                    for sample_id in fh:
                        sample_dir = markedfolder(self/sample_id.strip())
                        sample_dir.mark_for_cleanup()
                        sample_dir.cleanup()
                        rerun_samples.append(sample_id)
                try:
                    rerun_samples = [x.split('___')[-1].strip() for x in rerun_samples]
                except IndexError:
                    pass
                self.submit_rerun(",".join(rerun_samples))
                
                self.remove_rerun_mark()
            finally:
                self.unlock()

    def submit_rerun(self, samples: str):
        try:
            inst, year, rundir = self.parts[-3:]
            run(['/usr/local/bin/qsub', '-F', f"{inst} {year} {rundir} {samples}", 'rerun_samples.sh'])
        except ValueError:
            print(f"Not implemented: Rerunning {self}")
        pass

def search_institution_year_folders(dirname: Path, func):
    institution_year_run_folders = []
    for institution in os.listdir(dirname):
        institution_path = Path(dirname, institution)
        if os.path.isdir(institution_path):
            for year in os.listdir(institution_path):
                if re.match(r"20\d\d", year) is not None:
                    year_path = Path(institution_path, year)
                    for run_folder in os.listdir(year_path):
                        folder = markedfolder(year_path, run_folder)
                        if func(folder):
                            institution_year_run_folders.append(folder)
    return institution_year_run_folders # List of [(institution, year, run_folder)]


def main(args: Dict) -> None:
    print("Cleaning up.")
    rerun_dirs: List = search_institution_year_folders(args["output_dir"], lambda d: d.marked_for_rerun())
    for rerun_dir in rerun_dirs:
        rerun_dir.rerun()

if __name__ == '__main__':
    args: Dict = {
        "output_dir": os.environ["BIFROST_OUTPUT_DIR"],
    }
    main(args)
