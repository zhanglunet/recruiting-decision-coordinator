#!/usr/bin/env python3
"""Validate an isolated Source Gate receipt against a frozen snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_RECEIPT_FIELDS = {
    "review_mode",
    "review_scope",
    "review_round",
    "verdict",
    "lowest_failed_layer",
    "decisive_reason",
    "evidence",
    "preserve",
    "return_to",
    "next_action",
    "change_condition",
    "reviewed_snapshot_id",
    "grounding_audit",
    "source_audit",
    "materiality_audit",
    "authority_audit",
}
STABLE_RULE_FIELDS = {
    "rule_id",
    "rule",
    "artifact",
    "business_effect",
    "source_kind",
    "source",
}
SOURCE_KINDS = {
    "user-confirmed",
    "formal-material",
    "verified-platform-fact",
    "reversible-design-default",
}


def _read_object(path: Path, label: str) -> tuple[dict[str, object] | None, list[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, [f"cannot read {label}: {exc}"]
    except json.JSONDecodeError as exc:
        return None, [f"invalid {label} json: {exc}"]
    if not isinstance(value, dict):
        return None, [f"{label} must be a JSON object"]
    return value, []


def validate_receipt(receipt_path: Path, snapshot_path: Path) -> list[str]:
    receipt, errors = _read_object(receipt_path, "receipt")
    snapshot, snapshot_errors = _read_object(snapshot_path, "snapshot")
    errors.extend(snapshot_errors)
    if receipt is None or snapshot is None:
        return errors

    target_root = snapshot.get("target_root")
    authority_scope: dict[str, str] = {}
    if not isinstance(target_root, str) or not target_root:
        errors.append("snapshot target_root must be a non-empty string")
    else:
        scope_path = Path(target_root) / "contracts/authority-audit-scope.json"
        try:
            scope = json.loads(scope_path.read_text(encoding="utf-8"))
        except OSError as exc:
            errors.append(f"cannot read authority audit scope: {exc}")
        except json.JSONDecodeError as exc:
            errors.append(f"invalid authority audit scope json: {exc}")
        else:
            rules = scope.get("rules") if isinstance(scope, dict) else None
            if not isinstance(rules, list) or not rules:
                errors.append("authority audit scope must contain rules")
            else:
                for index, rule in enumerate(rules):
                    if not isinstance(rule, dict):
                        errors.append(f"authority scope rule {index} must be an object")
                        continue
                    rule_id = rule.get("rule_id")
                    source_kind = rule.get("source_kind")
                    if not isinstance(rule_id, str) or not rule_id:
                        errors.append(f"authority scope rule {index} missing rule_id")
                    elif rule_id in authority_scope:
                        errors.append(f"duplicate authority scope rule_id: {rule_id}")
                    elif source_kind not in SOURCE_KINDS:
                        errors.append(f"authority scope rule {rule_id} source_kind is not allowed")
                    else:
                        authority_scope[rule_id] = source_kind

    missing = REQUIRED_RECEIPT_FIELDS - set(receipt)
    if missing:
        errors.append(f"receipt missing fields: {sorted(missing)}")
    if receipt.get("review_mode") != "source-gate":
        errors.append("receipt review_mode must be source-gate")
    if receipt.get("review_scope") != "isolated-subagent":
        errors.append("receipt review_scope must be isolated-subagent")
    if receipt.get("verdict") != "pass":
        errors.append("receipt verdict must be pass")
    if receipt.get("lowest_failed_layer") != "none":
        errors.append("pass receipt lowest_failed_layer must be none")
    snapshot_id = snapshot.get("source_snapshot_id")
    if not isinstance(snapshot_id, str) or not snapshot_id.startswith("sha256:"):
        errors.append("snapshot id must use sha256: prefix")
    if receipt.get("reviewed_snapshot_id") != snapshot_id:
        errors.append("receipt snapshot id does not match")
    review_round = receipt.get("review_round")
    if (
        not isinstance(review_round, int)
        or isinstance(review_round, bool)
        or review_round < 1
    ):
        errors.append("receipt review_round must be a positive integer")
    for field in (
        "decisive_reason",
        "next_action",
        "change_condition",
    ):
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            errors.append(f"receipt {field} must be non-empty")
    for field in ("evidence", "preserve"):
        value = receipt.get(field)
        if (
            not isinstance(value, list)
            or not value
            or any(not isinstance(item, str) or not item.strip() for item in value)
        ):
            errors.append(f"receipt {field} must be a non-empty list of strings")
    if receipt.get("grounding_audit") != "not_applicable":
        errors.append("source-gate receipt grounding_audit must be not_applicable")
    authority = receipt.get("authority_audit")
    if not isinstance(authority, dict):
        errors.append("receipt authority_audit must be an object")
    else:
        unresolved = authority.get("unresolved_or_unauthorized")
        if not isinstance(unresolved, list):
            errors.append(
                "receipt authority_audit.unresolved_or_unauthorized must be a list"
            )
        elif unresolved:
            errors.append("pass receipt contains unresolved or unauthorized rules")
        reviewed = authority.get("stable_rules_reviewed")
        if not isinstance(reviewed, list):
            errors.append("receipt authority_audit.stable_rules_reviewed must be a list")
        elif not reviewed:
            errors.append("pass receipt must review at least one stable rule")
        else:
            reviewed_rule_ids: list[str] = []
            for index, record in enumerate(reviewed):
                if not isinstance(record, dict):
                    errors.append(f"stable rule audit {index} must be an object")
                    continue
                missing_rule_fields = STABLE_RULE_FIELDS - set(record)
                if missing_rule_fields:
                    errors.append(
                        f"stable rule audit {index} missing fields: "
                        f"{sorted(missing_rule_fields)}"
                    )
                    continue
                reviewed_rule_ids.append(record["rule_id"])
                for field in STABLE_RULE_FIELDS:
                    if not isinstance(record.get(field), str) or not record[field].strip():
                        errors.append(
                            f"stable rule audit {index} field {field} must be non-empty"
                        )
                if record.get("source_kind") not in SOURCE_KINDS:
                    errors.append(
                        f"stable rule audit {index} source_kind is not allowed"
                    )
                elif authority_scope.get(record["rule_id"]) != record.get("source_kind"):
                    errors.append(
                        f"stable rule audit {index} source_kind does not match authority scope"
                    )
            if len(reviewed_rule_ids) != len(set(reviewed_rule_ids)):
                errors.append("stable rule audit contains duplicate rule_id values")
            missing_rule_ids = sorted(set(authority_scope) - set(reviewed_rule_ids))
            extra_rule_ids = sorted(set(reviewed_rule_ids) - set(authority_scope))
            if missing_rule_ids:
                errors.append(f"missing required stable rule audits: {missing_rule_ids}")
            if extra_rule_ids:
                errors.append(f"unknown stable rule audit ids: {extra_rule_ids}")

    source_audit = receipt.get("source_audit")
    if not isinstance(source_audit, dict):
        errors.append("receipt source_audit must be an object")
    else:
        if source_audit.get("normal_case_replay") != "pass":
            errors.append("source audit normal case replay must pass")
        if source_audit.get("highest_risk_case_replay") != "pass":
            errors.append("source audit highest risk case replay must pass")
        if source_audit.get("finding_classification_consistent") is not True:
            errors.append("source audit finding classification must be consistent")
        if source_audit.get("unsupported_scope_expansion_found") is not False:
            errors.append("source audit must exclude unsupported scope expansion")
        if source_audit.get("skill_dependency_closure") != "pass":
            errors.append("source audit skill dependency closure must pass")

    materiality = receipt.get("materiality_audit")
    if not isinstance(materiality, dict):
        errors.append("receipt materiality_audit must be an object")
    else:
        if materiality.get("material_blocker_found") is not False:
            errors.append("pass receipt must not contain a material blocker")
        if materiality.get("late_round_blocking_justification") != "not_applicable":
            errors.append(
                "pass receipt late round blocking justification must be not_applicable"
            )
        for field in (
            "overall_goal",
            "consumer_decision",
            "first_release_boundary",
            "material_effect",
        ):
            if not isinstance(materiality.get(field), str) or not materiality[field].strip():
                errors.append(f"receipt materiality_audit.{field} must be non-empty")
        for field in ("same_failure_family_scope", "deferred_non_blocking"):
            if not isinstance(materiality.get(field), list):
                errors.append(f"receipt materiality_audit.{field} must be a list")
    if receipt.get("return_to") != "delivery-finalizer":
        errors.append("pass receipt must return to delivery-finalizer")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    args = parser.parse_args()
    errors = validate_receipt(args.receipt, args.snapshot)
    if errors:
        print("\n".join(errors))
        return 1
    print("source receipt valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
