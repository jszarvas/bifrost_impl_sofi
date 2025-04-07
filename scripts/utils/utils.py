import os
import sys
from pathlib import Path
from shutil import rmtree
from subprocess import run

def complain(message):
    print(message, file=sys.stderr)

"""
def complain(message):
    print(message, file=sys.stderr)

def complain(message):
    print(message, file=sys.stderr)
"""

def die(message, code=1):
    print(message, file=sys.stderr)
    sys.exit(code)

"""
def die(message, code=1):
    print(message, file=sys.stderr)
    sys.exit(code)

def die(message, code=1):
    print(message, file=sys.stderr)
    sys.exit(code)
"""

def marked_for_cleanup(dirname):
    return os.path.exists(str(dirname) + ".remove")

"""
def marked_for_cleanup(dirname):
    return os.path.exists(str(dirname) + ".remove")

def __init__(self, *args, **kwargs): # args caught by __new__ above
        self.clean_up_mark = Path(str(self) + ".remove")
def marked_for_cleanup(self):
    return self.clean_up_mark.exists()
"""

def mark_for_cleanup(dirname):
    try:
        Path(str(dirname) + ".remove").touch()
    except PermissionError:
        complain(f"Failed to touch {dirname}.remove: Permission denied")

def remove_mark(dirname):
    try:
        os.remove(str(dirname) + ".remove") #.unlink() and os.remove() are identical as of python 2.7
    except PermissionError:
        complain(f"Failed to remove {dirname}.remove: Permission denied")
    except Exception:
        complain(f"Failed to remove mark: {dirname}.remove")

"""
def remove_mark(dirname):
    try:
        os.remove(str(dirname) + ".remove")
    except PermissionError:
        complain(f"Failed to remove {dirname}.remove: Permission denied")

 def remove_clean_mark(self):
        try:
            self.clean_up_mark.unlink()
        except Exception:
            complain("Failed to remove mark: " + str(self.clean_up_mark))
"""

def remove_clean_mark(self):
    try:
        self.clean_up_mark.unlink()
    except Exception:
        complain("Failed to remove mark: " + str(self.clean_up_mark))

def locked(dirname):
    return os.path.exists(str(dirname) + ".remove.lock")

"""
def locked(dirname):
    return os.path.exists(str(dirname) + ".remove.lock")

def locked(self):
    return self.lockfile.exists()   
"""

def lock(dirname):
    if not locked(dirname):
        try:
            Path(str(dirname) + ".remove.lock").touch()
            return True
        except Exception:
            return False
    else:
        return False

"""
def lock(dirname):
    if not locked(dirname):
        try:
            Path(str(dirname) + ".remove.lock").touch()
            return True
        except Exception:
            return False
    else:
        return False

def __init__(self, *args, **kwargs): # args caught by __new__ above
        self.lockfile = Path(str(self) + ".lock")

def lock(self):
        try:
            self.lockfile.touch(exist_ok=False)
            return True
        except Exception:
            return False
"""

def unlock(dirname):
    try:
        os.remove(str(dirname) + ".remove.lock")
    except Exception:
        complain(f"Failed to remove lock: {dirname}.remove.lock")

"""
def unlock(dirname):
    try:
        os.remove(str(dirname) + ".remove.lock")
    except Exception:
        complain("Failed to remove lock: " + str(dirname) + ".remove.lock")

def unlock(self):
    try:
        self.lockfile.unlink()
    except Exception:
        complain("Failed to remove lock: " + str(self.lockfile))
"""

def clean_up_dir(dirname: Path):
    if marked_for_cleanup(dirname) and lock(dirname):
        try:
            rmtree(dirname)
            remove_clean_mark(dirname)
        except PermissionError:
            complain(f"Failed to remove {dirname}: Permission denied")
        finally:
            unlock(dirname)

"""
def clean_up_dir(dirname: Path) -> None:
    if marked_for_cleanup(dirname) and lock(dirname):
        try:
            rmtree(dirname)
            remove_mark(dirname)
        except PermissionError:
            f"Failed to remove {dirname}: Permission denied"
        finally:
            unlock(dirname)

def cleanup(self):
    if self.marked_for_cleanup() and self.lock():
        try:
            rmtree(self)
        except PermissionError:
            complain(f"Failed to remove {self}: Permission denied")
        finally:
            self.remove_clean_mark()
            self.unlock()
"""

def marked_for_rerun(dirname):
    return os.path.exists(str(dirname) + ".rerun")

"""
def marked_for_rerun(self):
    return self.rerun_mark.exists()
"""
