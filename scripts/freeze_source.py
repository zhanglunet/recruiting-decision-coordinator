#!/usr/bin/env python3
"""Build or verify a deterministic source snapshot for review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from validate import VERSION, validate_cases, validate_package


EXCLUDED_NAMES = {".DS_Store", "Thumbs.db"}


def _source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts:
            continue
        if path.name in EXCLUDED_NAMES or path.suffix == ".pyc":
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def build_snapshot(root: Path) -> dict[str, object]:
    root = root.resolve()
    records: list[dict[str, object]] = []
    identity = hashlib.sha256()
    for path in _source_files(root):
        relative = path.relative_to(root).as_posix()
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        records.append({"path": relative, "bytes": len(content), "sha256": digest})
        identity.update(relative.encode("utf-8"))
        identity.update(b"\0")
        identity.update(digest.encode("ascii"))
        identity.update(b"\0")
    identity.update(b"forbidden_evaluation_terms\0")
    evaluation_count = 0
    cases_path = root / "evaluation/cases.json"
    if cases_path.is_file():
        suite = json.loads(cases_path.read_text(encoding="utf-8"))
        cases = suite.get("cases")
        if isinstance(cases, list):
            evaluation_count = len(cases)
    return {
        "manifest_version": "1.2",
        "target_root": str(root),
        "entry": "SYSTEM_PROMPT.md",
        "source_snapshot_id": f"sha256:{identity.hexdigest()}",
        "evaluation_count": evaluation_count,
        "forbidden_evaluation_terms": [],
        "files": records,
    }


def _validated_snapshot(root: Path) -> dict[str, object]:
    errors = validate_package(root) + validate_cases(root)
    if errors:
        raise ValueError("source validation failed: " + "; ".join(errors))
    return build_snapshot(root)


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path)
    group.add_argument("--check", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        current = _validated_snapshot(root)
    except ValueError as exc:
        print(exc)
        return 1

    if args.output:
        try:
            args.output.resolve().relative_to(root)
        except ValueError:
            pass
        else:
            print("source review manifest must be outside target root")
            return 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(current, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(current["source_snapshot_id"])
        return 0

    try:
        expected = json.loads(args.check.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read source snapshot: {exc}")
        return 1
    if current != expected:
        print("source snapshot changed")
        return 1
    print("source snapshot unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
