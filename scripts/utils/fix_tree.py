#!/usr/bin/env python3
"""
Recursively fix group ownership and permissions in a file tree.

Behavior:
- Walks a directory tree rooted at the given path.
- Optionally changes group ownership to the provided group.
- Sets directory permissions to 2775 by default (rwxrwxr-x with setgid).
- Sets file permissions to 0664 by default (rw-rw-r--).
- Only attempts changes if the current user owns the file or directory.

Examples:
    ./fix_tree.py /data/project
    ./fix_tree.py /data/project --group mygroup
    ./fix_tree.py /data/project --dir-mode 2775 --file-mode 664 --dry-run
"""

from __future__ import annotations

import argparse
import grp
import os
import stat
import sys
from pathlib import Path
from typing import Optional


DEFAULT_DIR_MODE = 0o2775
DEFAULT_FILE_MODE = 0o664


def parse_mode(value: str) -> int:
    """Parse an octal permission string such as '2775' or '664'."""
    try:
        mode = int(value, 8)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid mode '{value}'. Use octal notation like 2775 or 664."
        ) from exc

    if mode < 0 or mode > 0o7777:
        raise argparse.ArgumentTypeError(
            f"Mode '{value}' is out of range. Use a valid octal mode."
        )
    return mode


def resolve_group(group_name: Optional[str]) -> Optional[int]:
    """Resolve a group name to a gid, or return None if no group was provided."""
    if group_name is None:
        return None

    try:
        return grp.getgrnam(group_name).gr_gid
    except KeyError as exc:
        raise SystemExit(f"Error: group '{group_name}' does not exist.") from exc


def current_user_uid() -> int:
    """Return the effective UID of the calling user."""
    return os.geteuid()


def is_owned_by_user(path: Path, uid: int) -> bool:
    """Return True if path is owned by the given uid."""
    try:
        st = path.lstat()
    except OSError as exc:
        print(f"ERROR: could not stat {path}: {exc}", file=sys.stderr)
        return False
    return st.st_uid == uid

def set_group(path: Path, gid: int, dry_run: bool, verbose: bool) -> None:
    """Set group ownership on a path, preserving user ownership."""
    try:
        st = path.lstat()
        if st.st_gid == gid:
            return

        if dry_run:
            print(f"DRY-RUN chgrp : {path}")
            return

        os.chown(path, -1, gid)
        if verbose:
            print(f"chgrp   : {path}")
    except PermissionError as exc:
        print(f"ERROR: chgrp failed for {path}: {exc}", file=sys.stderr)
    except OSError as exc:
        print(f"ERROR: chgrp failed for {path}: {exc}", file=sys.stderr)


def set_mode(path: Path, desired_mode: int, dry_run: bool, verbose: bool) -> None:
    """Set permissions on a path if different from the current mode."""
    try:
        st = path.lstat()
        current_mode = stat.S_IMODE(st.st_mode)
        if current_mode == desired_mode:
            return

        if dry_run:
            print(f"DRY-RUN chmod {desired_mode:o} : {path}")
            return

        os.chmod(path, desired_mode)
        if verbose:
            print(f"chmod {desired_mode:o}: {path}")
    except PermissionError as exc:
        print(f"ERROR: chmod failed for {path}: {exc}", file=sys.stderr)
    except OSError as exc:
        print(f"ERROR: chmod failed for {path}: {exc}", file=sys.stderr)


def process_path(
    path: Path,
    uid: int,
    gid: Optional[int],
    dir_mode: int,
    file_mode: int,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Apply group/mode updates to a single filesystem object if owned by uid."""
    try:
        st = path.lstat()
    except OSError as exc:
        print(f"ERROR: could not stat {path}: {exc}", file=sys.stderr)
        return

    if stat.S_ISLNK(st.st_mode):
        if verbose or dry_run:
            print(f"skip symlink: {path}")
        return

    if st.st_uid != uid:
        if verbose or dry_run:
            print(f"skip not-owned: {path}")
        return

    if stat.S_ISDIR(st.st_mode):
        if gid is not None:
            set_group(path, gid, dry_run)
        set_mode(path, dir_mode, dry_run)
    elif stat.S_ISREG(st.st_mode):
        if gid is not None:
            set_group(path, gid, dry_run)
        set_mode(path, file_mode, dry_run)
    else:
        if verbose or dry_run:
            print(f"skip special: {path}")

def walk_tree(
    root: Path,
    uid: int,
    gid: Optional[int],
    dir_mode: int,
    file_mode: int,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Walk the tree top-down and process directories and files."""
    # Process root itself first.
    process_path(root, uid, gid, dir_mode, file_mode, dry_run)

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        base = Path(dirpath)

        for dirname in dirnames:
            process_path(base / dirname, uid, gid, dir_mode, file_mode, dry_run)

        for filename in filenames:
            process_path(base / filename, uid, gid, dir_mode, file_mode, dry_run)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Recursively change group ownership and permissions for a file tree, "
            "but only on files/directories owned by the calling user."
        )
    )
    parser.add_argument(
        "root",
        help="Root of the file tree to process",
    )
    parser.add_argument(
        "--group",
        default="fvst_admins",
        help="Group name to set as group ownership",
    )
    parser.add_argument(
        "--dir-mode",
        default="2775",
        type=parse_mode,
        help="Directory mode in octal (default: 2775)",
    )
    parser.add_argument(
        "--file-mode",
        default="664",
        type=parse_mode,
        help="File mode in octal (default: 664)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without applying it",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show the actions taken",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    root = Path(args.root)

    if not root.exists():
        print(f"Error: path does not exist: {root}", file=sys.stderr)
        return 1

    uid = current_user_uid()
    gid = resolve_group(args.group)

    walk_tree(
        root=root,
        uid=uid,
        gid=gid,
        dir_mode=args.dir_mode,
        file_mode=args.file_mode,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
