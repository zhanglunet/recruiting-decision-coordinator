#!/usr/bin/env python3
"""Install a reviewed portable source archive into an explicit directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile


PACKAGE_NAME = "recruiting-decision-coordinator"
VERSION = "0.1.0"


def _safe_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = archive.infolist()
    if not members:
        raise ValueError("release archive is empty")
    top_levels: set[str] = set()
    for member in members:
        path = PurePosixPath(member.filename)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError(f"unsafe archive path: {member.filename}")
        top_levels.add(path.parts[0])
        mode = member.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ValueError(f"archive symlink is not allowed: {member.filename}")
    if top_levels != {PACKAGE_NAME}:
        raise ValueError("archive must contain one expected top-level directory")
    return members


def _hash_files(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def install_local(archive_path: Path, destination: Path) -> Path:
    if not destination.is_absolute():
        raise ValueError("installation destination must be an absolute path")
    if destination.exists():
        raise FileExistsError(f"installation destination exists: {destination}")
    if not archive_path.is_file():
        raise ValueError(f"release archive not found: {archive_path}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.install-", dir=destination.parent)
    )
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            members = _safe_members(archive)
            for member in members:
                relative = PurePosixPath(member.filename)
                target = temporary_root.joinpath(*relative.parts)
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member, "r") as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)

        source_root = temporary_root / PACKAGE_NAME
        if not (source_root / "SYSTEM_PROMPT.md").is_file():
            raise ValueError("archive is missing SYSTEM_PROMPT.md")
        files = _hash_files(source_root)
        receipt = {
            "package_name": PACKAGE_NAME,
            "version": VERSION,
            "install_kind": "portable_source_only",
            "runtime_activation": "not_claimed",
            "archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
            "files": files,
        }
        (source_root / ".installation-receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if _hash_files(source_root / "skills") != {
            path.removeprefix("skills/"): digest
            for path, digest in files.items()
            if path.startswith("skills/")
        }:
            raise ValueError("installed skill files failed read-back verification")
        os.rename(source_root, destination)
    finally:
        if temporary_root.exists():
            shutil.rmtree(temporary_root)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    try:
        installed = install_local(args.archive, args.destination)
    except (FileExistsError, OSError, UnicodeDecodeError, ValueError, zipfile.BadZipFile) as exc:
        print(exc)
        return 1
    print(installed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
