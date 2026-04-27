# test_fix_tree.py

import os
import stat
from pathlib import Path

import pytest

import fix_tree


def mode_bits(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def test_parse_mode_accepts_valid_octal():
    assert fix_tree.parse_mode("2775") == 0o2775
    assert fix_tree.parse_mode("664") == 0o664


def test_parse_mode_rejects_invalid_value():
    with pytest.raises(Exception):
        fix_tree.parse_mode("not-a-mode")


def test_resolve_group_none_returns_none():
    assert fix_tree.resolve_group(None) is None


def test_process_path_sets_directory_mode_for_owned_dir(tmp_path, monkeypatch):
    root = tmp_path / "owned_dir"
    root.mkdir()

    uid = root.lstat().st_uid
    mode_calls = []
    group_calls = []

    def fake_set_mode(path, desired_mode, dry_run):
        mode_calls.append((path, desired_mode, dry_run))

    def fake_set_group(path, gid, dry_run):
        group_calls.append((path, gid, dry_run))

    monkeypatch.setattr(fix_tree, "set_mode", fake_set_mode)
    monkeypatch.setattr(fix_tree, "set_group", fake_set_group)

    fix_tree.process_path(
        path=root,
        uid=uid,
        gid=None,
        dir_mode=0o2775,
        file_mode=0o664,
        dry_run=False,
    )

    assert mode_calls == [(root, 0o2775, False)]
    assert group_calls == []


def test_process_path_sets_file_mode_for_owned_file(tmp_path, monkeypatch):
    f = tmp_path / "owned_file.txt"
    f.write_text("hello")

    uid = f.lstat().st_uid
    mode_calls = []
    group_calls = []

    def fake_set_mode(path, desired_mode, dry_run):
        mode_calls.append((path, desired_mode, dry_run))

    def fake_set_group(path, gid, dry_run):
        group_calls.append((path, gid, dry_run))

    monkeypatch.setattr(fix_tree, "set_mode", fake_set_mode)
    monkeypatch.setattr(fix_tree, "set_group", fake_set_group)

    fix_tree.process_path(
        path=f,
        uid=uid,
        gid=None,
        dir_mode=0o2775,
        file_mode=0o664,
        dry_run=False,
    )

    assert mode_calls == [(f, 0o664, False)]
    assert group_calls == []


def test_process_path_applies_group_when_gid_provided(tmp_path, monkeypatch):
    f = tmp_path / "file.txt"
    f.write_text("hello")

    uid = f.lstat().st_uid
    gid = f.lstat().st_gid + 1

    mode_calls = []
    group_calls = []

    def fake_set_mode(path, desired_mode, dry_run):
        mode_calls.append((path, desired_mode, dry_run))

    def fake_set_group(path, gid_arg, dry_run):
        group_calls.append((path, gid_arg, dry_run))

    monkeypatch.setattr(fix_tree, "set_mode", fake_set_mode)
    monkeypatch.setattr(fix_tree, "set_group", fake_set_group)

    fix_tree.process_path(
        path=f,
        uid=uid,
        gid=gid,
        dir_mode=0o2775,
        file_mode=0o664,
        dry_run=False,
    )

    assert group_calls == [(f, gid, False)]
    assert mode_calls == [(f, 0o664, False)]


def test_process_path_skips_when_not_owned(tmp_path, capsys, monkeypatch):
    f = tmp_path / "file.txt"
    f.write_text("hello")

    real_uid = f.lstat().st_uid
    different_uid = real_uid + 99999

    group_calls = []
    chmod_calls = []

    def fake_set_group(path, gid_arg, dry_run):
        group_calls.append((path, gid_arg, dry_run))

    def fake_set_mode(path, desired_mode, dry_run):
        chmod_calls.append((path, desired_mode, dry_run))

    monkeypatch.setattr(fix_tree, "set_group", fake_set_group)
    monkeypatch.setattr(fix_tree, "set_mode", fake_set_mode)

    fix_tree.process_path(
        path=f,
        uid=different_uid,
        gid=1234,
        dir_mode=0o2775,
        file_mode=0o664,
        dry_run=False,
    )

    out = capsys.readouterr().out
    assert "skip not-owned" in out
    assert group_calls == []
    assert chmod_calls == []


def test_process_path_skips_symlink(tmp_path, capsys, monkeypatch):
    target = tmp_path / "target.txt"
    target.write_text("hello")

    link = tmp_path / "link.txt"
    link.symlink_to(target)

    group_calls = []
    chmod_calls = []

    def fake_set_group(path, gid_arg, dry_run):
        group_calls.append((path, gid_arg, dry_run))

    def fake_set_mode(path, desired_mode, dry_run):
        chmod_calls.append((path, desired_mode, dry_run))

    monkeypatch.setattr(fix_tree, "set_group", fake_set_group)
    monkeypatch.setattr(fix_tree, "set_mode", fake_set_mode)

    fix_tree.process_path(
        path=link,
        uid=link.lstat().st_uid,
        gid=1234,
        dir_mode=0o2775,
        file_mode=0o664,
        dry_run=False,
    )

    out = capsys.readouterr().out
    assert "skip symlink" in out
    assert group_calls == []
    assert chmod_calls == []


def test_set_mode_calls_os_chmod_when_different(tmp_path, monkeypatch):
    f = tmp_path / "file.txt"
    f.write_text("hello")
    f.chmod(0o600)

    calls = []

    def fake_chmod(path, mode, *, follow_symlinks):
        calls.append((path, mode, follow_symlinks))

    monkeypatch.setattr(os, "chmod", fake_chmod)

    fix_tree.set_mode(f, 0o664, dry_run=False)

    assert calls == [(f, 0o664, False)]


def test_set_mode_dry_run_does_not_change_mode(tmp_path, capsys, monkeypatch):
    f = tmp_path / "file.txt"
    f.write_text("hello")
    f.chmod(0o600)

    called = {"value": False}

    def fake_chmod(*args, **kwargs):
        called["value"] = True

    monkeypatch.setattr(os, "chmod", fake_chmod)

    fix_tree.set_mode(f, 0o664, dry_run=True)

    out = capsys.readouterr().out
    assert "DRY-RUN chmod 664" in out
    assert called["value"] is False
    assert mode_bits(f) == 0o600


def test_set_mode_no_change_when_already_correct(tmp_path, capsys, monkeypatch):
    f = tmp_path / "file.txt"
    f.write_text("hello")
    f.chmod(0o664)

    called = {"value": False}

    def fake_chmod(*args, **kwargs):
        called["value"] = True

    monkeypatch.setattr(os, "chmod", fake_chmod)

    fix_tree.set_mode(f, 0o664, dry_run=False)

    out = capsys.readouterr().out
    assert out == ""
    assert called["value"] is False


def test_set_group_dry_run_does_not_call_chown(tmp_path, monkeypatch, capsys):
    f = tmp_path / "file.txt"
    f.write_text("hello")

    original_gid = f.lstat().st_gid
    new_gid = original_gid + 1

    called = {"value": False}

    def fake_chown(*args, **kwargs):
        called["value"] = True

    monkeypatch.setattr(os, "chown", fake_chown)

    fix_tree.set_group(f, new_gid, dry_run=True)

    out = capsys.readouterr().out
    assert "DRY-RUN chgrp" in out
    assert called["value"] is False


def test_set_group_no_change_when_gid_already_matches(tmp_path, monkeypatch, capsys):
    f = tmp_path / "file.txt"
    f.write_text("hello")

    current_gid = f.lstat().st_gid

    called = {"value": False}

    def fake_chown(*args, **kwargs):
        called["value"] = True

    monkeypatch.setattr(os, "chown", fake_chown)

    fix_tree.set_group(f, current_gid, dry_run=False)

    out = capsys.readouterr().out
    assert out == ""
    assert called["value"] is False


def test_walk_tree_processes_root_and_children(tmp_path, monkeypatch):
    root = tmp_path / "tree"
    root.mkdir()

    d1 = root / "dir1"
    d1.mkdir()

    f1 = root / "file1.txt"
    f1.write_text("a")

    f2 = d1 / "file2.txt"
    f2.write_text("b")

    seen = []

    def fake_process_path(path, uid, gid, dir_mode, file_mode, dry_run):
        seen.append(path)

    monkeypatch.setattr(fix_tree, "process_path", fake_process_path)

    fix_tree.walk_tree(
        root=root,
        uid=123,
        gid=456,
        dir_mode=0o2775,
        file_mode=0o664,
        dry_run=False,
    )

    assert set(seen) == {root, d1, f1, f2}


