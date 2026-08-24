#!/usr/bin/env python3
"""Static delivery checks; passing does not prove Agent behavior."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


VERSION = "0.1.0"
SKILLS = (
    "shape-job-and-publishing",
    "assess-candidate-evidence",
    "design-structured-interview",
)
FORBIDDEN_CLAIMS = (
    "平台已激活",
    "ATS 已连接",
    "日历已连接",
    "消息已真实发送",
    "自动录用",
    "自动发送淘汰",
    "筛选准确率已提升",
    "招聘周期已缩短",
)
REQUIRED_FILES = (
    "PACKAGE.yaml",
    "README.md",
    "SYSTEM_PROMPT.md",
    "contracts/runtime-integrations.md",
    "contracts/authority-audit-scope.json",
    "skills/shape-job-and-publishing/SKILL.md",
    "skills/assess-candidate-evidence/SKILL.md",
    "skills/design-structured-interview/SKILL.md",
    "evaluation/README.md",
    "evaluation/cases.json",
    "scripts/freeze_source.py",
    "scripts/validate_source_receipt.py",
    "scripts/package_release.py",
    "scripts/install_local.py",
)
CASE_FIELDS = {
    "id",
    "category",
    "user_request",
    "context",
    "runtime_standards",
    "mock_tools",
    "expected_behaviors",
    "prohibited_behaviors",
    "expected_end_state",
    "next_human_action",
}


def validate_package(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing file: {relative}")

    manifest = root / "PACKAGE.yaml"
    if manifest.is_file():
        text = manifest.read_text(encoding="utf-8")
        if not re.search(rf"(?m)^version:\s*{re.escape(VERSION)}\s*$", text):
            errors.append("manifest version mismatch")
        if "tool_evidence_status: none" not in text:
            errors.append("tool evidence must remain none")
        if "behavior_evidence: designed_not_run" not in text:
            errors.append("behavior evidence must remain designed_not_run")
        for skill in SKILLS:
            if text.count(f"name: {skill}") != 1:
                errors.append(f"manifest must declare skill exactly once: {skill}")

    version_markers = {
        "SYSTEM_PROMPT.md": "Agent-Version: 0.1.0",
        "contracts/runtime-integrations.md": "Contract-Version: 0.1.0",
        "skills/shape-job-and-publishing/SKILL.md": "Skill-Version: 0.1.0",
        "skills/assess-candidate-evidence/SKILL.md": "Skill-Version: 0.1.0",
        "skills/design-structured-interview/SKILL.md": "Skill-Version: 0.1.0",
    }
    for relative, marker in version_markers.items():
        path = root / relative
        if path.is_file() and marker not in path.read_text(encoding="utf-8"):
            errors.append(f"version marker mismatch: {relative}")

    prompt = root / "SYSTEM_PROMPT.md"
    if prompt.is_file():
        text = prompt.read_text(encoding="utf-8")
        for skill in SKILLS:
            if skill not in text:
                errors.append(f"system prompt does not route to skill: {skill}")
        if "必须人工确认" not in text:
            errors.append("system prompt must preserve high-impact human gate")

    contract = root / "contracts/runtime-integrations.md"
    if contract.is_file():
        text = contract.read_text(encoding="utf-8")
        if "connection_status = required_not_connected" not in text:
            errors.append("runtime contract must remain required_not_connected")
        if "tool_evidence_status = none" not in text:
            errors.append("runtime contract tool evidence must remain none")

    scan_paths = [root / "SYSTEM_PROMPT.md", root / "README.md", contract]
    scan_paths.extend(root / "skills" / name / "SKILL.md" for name in SKILLS)
    for path in scan_paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for claim in FORBIDDEN_CLAIMS:
            if claim in text:
                errors.append(f"unsupported production claim in {path.relative_to(root)}: {claim}")

    cases_path = root / "evaluation/cases.json"
    if cases_path.is_file():
        try:
            suite = json.loads(cases_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid cases json: {exc}")
        else:
            if suite.get("version") != VERSION:
                errors.append("evaluation version mismatch")
    return errors


def validate_cases(root: Path) -> list[str]:
    path = root / "evaluation/cases.json"
    if not path.is_file():
        return ["missing evaluation/cases.json"]
    try:
        suite = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid cases json: {exc}"]

    errors: list[str] = []
    if suite.get("version") != VERSION:
        errors.append("evaluation version mismatch")
    if suite.get("evidence_status") != "designed_not_run":
        errors.append("evaluation evidence status must be designed_not_run")
    cases = suite.get("cases")
    if not isinstance(cases, list) or len(cases) != 9:
        return errors + ["evaluation suite must contain exactly 9 cases"]

    ids: list[str] = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"case {index} must be an object")
            continue
        missing = CASE_FIELDS - set(case)
        if missing:
            errors.append(f"case {index} missing fields: {sorted(missing)}")
        case_id = case.get("id")
        if isinstance(case_id, str) and case_id:
            ids.append(case_id)
        else:
            errors.append(f"case {index} must have a non-empty id")
        for field in (
            "context",
            "runtime_standards",
            "expected_behaviors",
            "prohibited_behaviors",
        ):
            if not isinstance(case.get(field), list) or not case[field]:
                errors.append(
                    f"case {case_id} field {field} must be a non-empty list"
                )
        if not isinstance(case.get("mock_tools"), list):
            errors.append(f"case {case_id} field mock_tools must be a list")
        for field in ("expected_end_state", "next_human_action"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                errors.append(f"case {case_id} field {field} must be non-empty")
    if len(ids) != len(set(ids)):
        errors.append("case ids must be unique")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate_package(root) + validate_cases(root)
    if errors:
        print("\n".join(errors))
        return 1
    print("package validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
