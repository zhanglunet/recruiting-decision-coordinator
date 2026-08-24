#!/usr/bin/env python3
"""Create a deterministic ZIP only for an unchanged Source Gate pass."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile

from freeze_source import build_snapshot
from validate_source_receipt import validate_receipt


ARCHIVE_ROOT = "recruiting-decision-coordinator"


def package_release(
    root: Path,
    receipt_path: Path,
    output_path: Path,
    manifest_path: Path | None = None,
) -> Path:
    root = root.resolve()
    if not receipt_path.is_file():
        raise ValueError(f"source receipt not found: {receipt_path}")
    if manifest_path is None or not manifest_path.is_file():
        raise ValueError("frozen source snapshot not found")
    try:
        expected = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid source snapshot: {exc}") from exc
    current = build_snapshot(root)
    if current != expected:
        raise ValueError("source changed after review snapshot")
    receipt_errors = validate_receipt(receipt_path, manifest_path)
    if receipt_errors:
        raise ValueError("invalid source receipt: " + "; ".join(receipt_errors))

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=output_path.name + ".", suffix=".tmp", dir=output_path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            records = {record["path"]: record["sha256"] for record in expected["files"]}
            for relative in sorted(records):
                source = root / relative
                info = zipfile.ZipInfo(f"{ARCHIVE_ROOT}/{relative}")
                info.date_time = (1980, 1, 1, 0, 0, 0)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, source.read_bytes())

        with zipfile.ZipFile(temporary, "r") as archive:
            expected_names = {f"{ARCHIVE_ROOT}/{relative}" for relative in records}
            if set(archive.namelist()) != expected_names:
                raise ValueError("archive file list does not match snapshot")
            for relative, expected_hash in records.items():
                payload = archive.read(f"{ARCHIVE_ROOT}/{relative}")
                payload.decode("utf-8")
                if hashlib.sha256(payload).hexdigest() != expected_hash:
                    raise ValueError(f"archive hash mismatch: {relative}")
        os.replace(temporary, output_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        result = package_release(root, args.receipt, args.output, args.manifest)
    except (OSError, UnicodeDecodeError, ValueError, zipfile.BadZipFile) as exc:
        print(exc)
        return 1
    print(f"release package verified: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
