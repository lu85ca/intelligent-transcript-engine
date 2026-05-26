#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_CONTEXTS = {
    "work_meetings": "knowledge/work_meetings",
    "macro_categories/finance": "knowledge/macro_categories/finance",
    "macro_categories/travel": "knowledge/macro_categories/travel",
    "macro_categories/social_media_management": "knowledge/macro_categories/social_media_management",
    "macro_categories/generic": "knowledge/macro_categories/generic",
}

VALID_STATUSES = {"candidate", "approved", "rejected", "promoted"}
VALID_TARGETS = {"normalization_rules", "approved_terms", "unknown"}

MSG_DRY_RUN = "Dry run: no files were written."
MSG_NO_CANDIDATE = "Candidate not found."
MSG_PROMOTED = "Candidate promoted manually."
MSG_REJECTED = "Candidate rejected manually."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage normalization/glossary candidates.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="Collect candidates from technical reports.")
    collect.add_argument("basename", help="Transcript/report basename.")
    add_common_context(collect)
    collect.add_argument("--force", action="store_true", help="Regenerate the candidate file.")
    collect.add_argument("--dry-run", action="store_true", help="Print candidates without writing files.")
    collect.add_argument("--json", action="store_true", help="Print technical JSON output.")
    collect.add_argument("--verbose", action="store_true", help="Print diagnostic details.")

    list_cmd = subparsers.add_parser("list", help="List candidates in a context.")
    add_common_context(list_cmd)
    list_cmd.add_argument("--status", choices=sorted(VALID_STATUSES), help="Filter by candidate status.")
    list_cmd.add_argument("--source", help="Filter by candidate source.")
    list_cmd.add_argument("--json", action="store_true", help="Print JSON output.")

    promote = subparsers.add_parser("promote", help="Promote one candidate manually.")
    add_common_context(promote)
    promote.add_argument("--candidate-id", required=True, help="Candidate id to promote.")
    promote.add_argument("--to", required=True, choices=["normalization_rules", "approved_terms"])
    promote.add_argument("--notes", default="", help="Optional promotion notes.")
    promote.add_argument("--json", action="store_true", help="Print JSON output.")

    reject = subparsers.add_parser("reject", help="Reject one candidate manually.")
    add_common_context(reject)
    reject.add_argument("--candidate-id", required=True, help="Candidate id to reject.")
    reject.add_argument("--notes", default="", help="Optional rejection notes.")
    reject.add_argument("--json", action="store_true", help="Print JSON output.")

    return parser.parse_args()


def add_common_context(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--context",
        default="work_meetings",
        choices=sorted(ALLOWED_CONTEXTS),
        help="Knowledge context. Default: work_meetings.",
    )


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def context_dir(root: Path, context: str) -> Path:
    return root / ALLOWED_CONTEXTS[context]


def candidates_dir(root: Path, context: str) -> Path:
    return context_dir(root, context) / "candidates"


def candidate_file(root: Path, context: str, basename: str) -> Path:
    return candidates_dir(root, context) / f"{basename}_candidates.json"


def source_report_paths(root: Path, basename: str) -> dict[str, Path]:
    return {
        "transcription": root / "output" / "transcription" / f"{basename}_transcription.json",
        "review": root / "output" / "review" / f"{basename}_review.json",
        "normalization": root / "output" / "normalization" / f"{basename}_normalization.json",
    }


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def candidate_id(context: str, observed: str, possible_canonical: str | None, target: str) -> str:
    raw = "\x1f".join([context, observed.strip().lower(), (possible_canonical or "").strip().lower(), target])
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"cand_{digest}"


def infer_match(observed: str) -> str:
    observed = observed.strip()
    if not observed:
        return "unknown"
    return "phrase" if re.search(r"\s", observed) else "word"


def normalize_candidate(
    *,
    basename: str,
    context: str,
    raw: dict[str, Any],
    source: str,
    created_at: str,
) -> dict[str, Any] | None:
    observed = str(raw.get("observed", "")).strip()
    if not observed:
        return None

    possible = raw.get("possible_canonical")
    possible_canonical = str(possible).strip() if possible not in (None, "") else None
    target = "normalization_rules" if possible_canonical else "unknown"
    match = str(raw.get("match") or infer_match(observed))
    if match not in {"word", "phrase", "regex", "unknown"}:
        match = "unknown"
    candidate = {
        "id": candidate_id(context, observed, possible_canonical, target),
        "observed": observed,
        "possible_canonical": possible_canonical,
        "source": source,
        "sources": [source],
        "target": target,
        "match": match,
        "status": "candidate",
        "confidence": raw.get("confidence"),
        "notes": raw.get("reason") or raw.get("notes") or "Candidate generated from technical report; requires manual review.",
        "first_seen_in": basename,
        "seen_in": [basename],
        "occurrences": raw.get("occurrences"),
        "created_at": created_at,
        "updated_at": created_at,
    }
    return candidate


def candidate_from_conflict(
    *,
    basename: str,
    context: str,
    conflict: dict[str, Any],
    created_at: str,
) -> dict[str, Any] | None:
    observed = str(conflict.get("observed", "")).strip()
    if not observed:
        return None
    raw = {
        "observed": observed,
        "possible_canonical": None,
        "match": "unknown",
        "notes": "Normalization conflict requires manual review.",
    }
    candidate = normalize_candidate(
        basename=basename,
        context=context,
        raw=raw,
        source="normalization.conflicts",
        created_at=created_at,
    )
    if candidate:
        candidate["target"] = "unknown"
        candidate["conflict"] = conflict
        candidate["id"] = candidate_id(context, observed, None, "unknown")
    return candidate


def collect_from_reports(root: Path, basename: str, context: str) -> tuple[list[dict[str, Any]], list[str]]:
    created_at = now_iso()
    candidates: list[dict[str, Any]] = []
    source_reports: list[str] = []
    paths = source_report_paths(root, basename)

    transcription = load_json(paths["transcription"])
    if transcription is not None:
        source_reports.append(rel(paths["transcription"], root))
        for raw in transcription.get("normalization_candidates", []):
            if isinstance(raw, dict):
                candidate = normalize_candidate(
                    basename=basename,
                    context=context,
                    raw=raw,
                    source="transcription.normalization_candidates",
                    created_at=created_at,
                )
                if candidate:
                    candidates.append(candidate)

    review = load_json(paths["review"])
    if review is not None:
        source_reports.append(rel(paths["review"], root))
        for raw in review.get("normalization_candidates", []):
            if isinstance(raw, dict):
                candidate = normalize_candidate(
                    basename=basename,
                    context=context,
                    raw=raw,
                    source="review.normalization_candidates",
                    created_at=created_at,
                )
                if candidate:
                    candidates.append(candidate)
        for raw in review.get("manual_review_items", []):
            if isinstance(raw, dict) and raw.get("type") == "normalization_candidate":
                candidate = normalize_candidate(
                    basename=basename,
                    context=context,
                    raw=raw,
                    source="review.manual_review_items",
                    created_at=created_at,
                )
                if candidate:
                    candidates.append(candidate)

    normalization = load_json(paths["normalization"])
    if normalization is not None:
        source_reports.append(rel(paths["normalization"], root))
        for conflict in normalization.get("conflicts", []):
            if isinstance(conflict, dict):
                candidate = candidate_from_conflict(
                    basename=basename,
                    context=context,
                    conflict=conflict,
                    created_at=created_at,
                )
                if candidate:
                    candidates.append(candidate)

    return candidates, source_reports


def empty_candidate_payload(basename: str, context: str, source_reports: list[str]) -> dict[str, Any]:
    return {
        "basename": basename,
        "context": context,
        "source_reports": source_reports,
        "candidate_count": 0,
        "candidates": [],
        "warnings": [],
        "updated_at": now_iso(),
    }


def load_candidate_payload(path: Path, basename: str, context: str, source_reports: list[str]) -> dict[str, Any]:
    data = load_json(path)
    if not data:
        return empty_candidate_payload(basename, context, source_reports)
    data.setdefault("basename", basename)
    data.setdefault("context", context)
    data.setdefault("source_reports", [])
    data.setdefault("candidates", [])
    data.setdefault("warnings", [])
    return data


def merge_list(existing: list[Any], new_values: list[Any]) -> list[Any]:
    result = list(existing)
    for value in new_values:
        if value not in result:
            result.append(value)
    return result


def merge_candidates(
    existing_payload: dict[str, Any],
    new_candidates: list[dict[str, Any]],
    source_reports: list[str],
) -> dict[str, Any]:
    payload = dict(existing_payload)
    payload["source_reports"] = merge_list(list(payload.get("source_reports", [])), source_reports)
    payload.setdefault("warnings", [])
    existing_by_id = {
        str(candidate.get("id")): candidate
        for candidate in payload.get("candidates", [])
        if isinstance(candidate, dict) and candidate.get("id")
    }

    for candidate in new_candidates:
        cid = candidate["id"]
        if cid in existing_by_id:
            existing = existing_by_id[cid]
            existing["sources"] = merge_list(list(existing.get("sources", [])), list(candidate.get("sources", [])))
            existing["seen_in"] = merge_list(list(existing.get("seen_in", [])), list(candidate.get("seen_in", [])))
            existing["updated_at"] = now_iso()
            if existing.get("occurrences") is None and candidate.get("occurrences") is not None:
                existing["occurrences"] = candidate["occurrences"]
            continue
        payload.setdefault("candidates", []).append(candidate)
        existing_by_id[cid] = candidate

    payload["warnings"] = candidate_warnings(payload.get("candidates", []))
    payload["candidate_count"] = len(payload.get("candidates", []))
    payload["updated_at"] = now_iso()
    return payload


def candidate_warnings(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_observed: dict[str, set[str]] = {}
    for candidate in candidates:
        observed = str(candidate.get("observed", "")).strip().lower()
        canonical = str(candidate.get("possible_canonical") or "").strip()
        if observed:
            by_observed.setdefault(observed, set()).add(canonical)
    warnings: list[dict[str, Any]] = []
    for observed, canonicals in sorted(by_observed.items()):
        real_canonicals = {value for value in canonicals if value}
        if len(real_canonicals) > 1:
            warnings.append(
                {
                    "type": "candidate_conflict",
                    "observed": observed,
                    "possible_canonical_values": sorted(real_canonicals),
                    "message": "Same observed form has multiple candidate canonical values; manual review required.",
                }
            )
    return warnings


def collect_candidates(
    *,
    root: Path,
    basename: str,
    context: str,
    force: bool = False,
) -> dict[str, Any]:
    new_candidates, source_reports = collect_from_reports(root, basename, context)
    path = candidate_file(root, context, basename)
    existing = empty_candidate_payload(basename, context, source_reports) if force else load_candidate_payload(
        path,
        basename,
        context,
        source_reports,
    )
    payload = merge_candidates(existing, new_candidates, source_reports)
    payload["candidate_file"] = rel(path, root)
    return payload


def iter_candidate_files(root: Path, context: str) -> list[Path]:
    base = candidates_dir(root, context)
    if not base.exists():
        return []
    return sorted(path for path in base.glob("*_candidates.json") if path.is_file())


def list_candidates(
    *,
    root: Path,
    context: str,
    status: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in iter_candidate_files(root, context):
        payload = load_json(path) or {}
        for candidate in payload.get("candidates", []):
            if not isinstance(candidate, dict):
                continue
            if status and candidate.get("status") != status:
                continue
            sources = list(candidate.get("sources", [])) or [candidate.get("source")]
            if source and source not in sources and candidate.get("source") != source:
                continue
            row = dict(candidate)
            row["candidate_file"] = rel(path, root)
            rows.append(row)
    return {"context": context, "candidate_count": len(rows), "candidates": rows}


def find_candidate(root: Path, context: str, candidate_id_value: str) -> tuple[Path | None, dict[str, Any] | None, dict[str, Any] | None]:
    for path in iter_candidate_files(root, context):
        payload = load_json(path) or {}
        for candidate in payload.get("candidates", []):
            if isinstance(candidate, dict) and candidate.get("id") == candidate_id_value:
                return path, payload, candidate
    return None, None, None


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def split_key_value(text: str) -> tuple[str, str]:
    key, value = text.split(":", 1)
    return key.strip(), value.strip()


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_rule_blocks(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    rules_start: int | None = None
    for idx, line in enumerate(lines):
        if line.strip() == "rules: []":
            return []
        if line.strip() == "rules:":
            rules_start = idx + 1
            break
    if rules_start is None:
        return []
    rules: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    active_list_key: str | None = None
    for raw_line in lines[rules_start:]:
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()
        if indent == 0:
            break
        if indent == 2 and stripped.startswith("- "):
            if current is not None:
                rules.append(current)
            current = {}
            active_list_key = None
            remainder = stripped[2:].strip()
            if remainder and ":" in remainder:
                key, value = split_key_value(remainder)
                current[key] = strip_quotes(value)
            continue
        if current is None:
            continue
        if indent == 4 and ":" in stripped:
            key, value = split_key_value(stripped)
            if value == "":
                current[key] = []
                active_list_key = key
            else:
                current[key] = strip_quotes(value)
                active_list_key = None
            continue
        if indent >= 6 and stripped.startswith("- ") and active_list_key:
            current.setdefault(active_list_key, [])
            if isinstance(current[active_list_key], list):
                current[active_list_key].append(strip_quotes(stripped[2:].strip()))
    if current is not None:
        rules.append(current)
    return rules


def slug(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^a-z0-9]+", "_", lowered)
    return lowered.strip("_") or "term"


def rule_id_for(candidate: dict[str, Any]) -> str:
    canonical = str(candidate.get("possible_canonical") or "")
    observed = str(candidate.get("observed") or "")
    return f"{slug(canonical)}_from_{slug(observed)}"


def rule_block(candidate: dict[str, Any], notes: str = "") -> list[str]:
    rule_id = rule_id_for(candidate)
    observed = str(candidate["observed"])
    canonical = str(candidate["possible_canonical"])
    match = str(candidate.get("match") or infer_match(observed))
    if match not in {"word", "phrase", "regex"}:
        match = infer_match(observed)
    note = notes or f"Promoted manually from candidate {candidate['id']}."
    return [
        f"  - id: {rule_id}",
        "    enabled: true",
        "    observed:",
        f"      - {yaml_quote(observed)}",
        f"    canonical: {yaml_quote(canonical)}",
        f"    match: {yaml_quote(match)}",
        "    case_sensitive: false",
        f"    notes: {yaml_quote(note)}",
    ]


def insert_yaml_list_item(path: Path, key: str, block: list[str], empty_marker: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(f"version: 1\n{key}:\n" + "\n".join(block) + "\n", encoding="utf-8")
        return True

    lines = path.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines):
        if line.strip() == empty_marker:
            lines[idx : idx + 1] = [f"{key}:", *block]
            path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
            return True

    key_idx: int | None = None
    for idx, line in enumerate(lines):
        if line.strip() == f"{key}:":
            key_idx = idx
            break
    if key_idx is None:
        lines.extend([f"{key}:", *block])
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return True

    insert_at = len(lines)
    for idx in range(key_idx + 1, len(lines)):
        stripped = lines[idx].strip()
        if stripped and not lines[idx].startswith(" "):
            insert_at = idx
            break
    lines[insert_at:insert_at] = block
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return True


def promote_to_normalization_rules(root: Path, context: str, candidate: dict[str, Any], notes: str = "") -> dict[str, Any]:
    observed = str(candidate.get("observed") or "").strip()
    canonical = str(candidate.get("possible_canonical") or "").strip()
    if not observed or not canonical:
        return {"ok": False, "reason": "Candidate requires observed and possible_canonical."}

    target = context_dir(root, context) / "normalization_rules.yml"
    for rule in parse_rule_blocks(target):
        observed_values = [str(item) for item in rule.get("observed", [])]
        existing_canonical = str(rule.get("canonical", "")).strip()
        for existing_observed in observed_values:
            if existing_observed.lower() == observed.lower():
                if existing_canonical.lower() == canonical.lower():
                    return {
                        "ok": True,
                        "changed": False,
                        "target_file": rel(target, root),
                        "promoted_rule_id": str(rule.get("id") or rule_id_for(candidate)),
                        "reason": "Equivalent normalization rule already exists.",
                    }
                return {
                    "ok": False,
                    "reason": "Conflicting normalization rule already exists.",
                    "target_file": rel(target, root),
                    "existing_canonical": existing_canonical,
                }

    insert_yaml_list_item(target, "rules", rule_block(candidate, notes), "rules: []")
    return {
        "ok": True,
        "changed": True,
        "target_file": rel(target, root),
        "promoted_rule_id": rule_id_for(candidate),
    }


def parse_approved_terms(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    terms_start: int | None = None
    for idx, line in enumerate(lines):
        if line.strip() == "approved_terms: []":
            return []
        if line.strip() == "approved_terms:":
            terms_start = idx + 1
            break
    if terms_start is None:
        return []
    terms: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    active_list_key: str | None = None
    for raw_line in lines[terms_start:]:
        if not raw_line.strip():
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()
        if indent == 0:
            break
        if indent == 2 and stripped.startswith("- "):
            if current is not None:
                terms.append(current)
            current = {}
            active_list_key = None
            remainder = stripped[2:].strip()
            if remainder and ":" in remainder:
                key, value = split_key_value(remainder)
                current[key] = strip_quotes(value)
            continue
        if current is None:
            continue
        if indent == 4 and ":" in stripped:
            key, value = split_key_value(stripped)
            if value == "":
                current[key] = []
                active_list_key = key
            else:
                current[key] = strip_quotes(value)
                active_list_key = None
            continue
        if indent >= 6 and stripped.startswith("- ") and active_list_key:
            current.setdefault(active_list_key, [])
            if isinstance(current[active_list_key], list):
                current[active_list_key].append(strip_quotes(stripped[2:].strip()))
    if current is not None:
        terms.append(current)
    return terms


def approved_term_block(candidate: dict[str, Any], notes: str = "") -> list[str]:
    canonical = str(candidate.get("possible_canonical") or candidate.get("observed") or "").strip()
    observed = str(candidate.get("observed") or "").strip()
    note = notes or f"Promoted manually from candidate {candidate['id']}."
    block = [
        f"  - canonical: {yaml_quote(canonical)}",
        "    aliases:",
    ]
    if observed and observed.lower() != canonical.lower():
        block.append(f"      - {yaml_quote(observed)}")
    block.append(f"    notes: {yaml_quote(note)}")
    return block


def promote_to_approved_terms(root: Path, context: str, candidate: dict[str, Any], notes: str = "") -> dict[str, Any]:
    canonical = str(candidate.get("possible_canonical") or candidate.get("observed") or "").strip()
    if not canonical:
        return {"ok": False, "reason": "Candidate requires observed or possible_canonical."}

    target = context_dir(root, context) / "approved_terms.yml"
    for term in parse_approved_terms(target):
        existing = str(term.get("canonical", "")).strip()
        if existing.lower() == canonical.lower():
            return {
                "ok": True,
                "changed": False,
                "target_file": rel(target, root),
                "promoted_term": existing,
                "reason": "Equivalent approved term already exists.",
            }

    insert_yaml_list_item(target, "approved_terms", approved_term_block(candidate, notes), "approved_terms: []")
    return {"ok": True, "changed": True, "target_file": rel(target, root), "promoted_term": canonical}


def update_candidate_status(
    *,
    path: Path,
    payload: dict[str, Any],
    candidate: dict[str, Any],
    status: str,
    fields: dict[str, Any],
) -> None:
    candidate["status"] = status
    candidate.update(fields)
    candidate["updated_at"] = now_iso()
    payload["updated_at"] = now_iso()
    write_json(path, payload)


def promote_candidate(
    *,
    root: Path,
    context: str,
    candidate_id_value: str,
    target: str,
    notes: str = "",
) -> tuple[dict[str, Any], int]:
    path, payload, candidate = find_candidate(root, context, candidate_id_value)
    if path is None or payload is None or candidate is None:
        return {"status": "error", "message": MSG_NO_CANDIDATE, "candidate_id": candidate_id_value}, 1

    if target == "normalization_rules":
        result = promote_to_normalization_rules(root, context, candidate, notes)
    else:
        result = promote_to_approved_terms(root, context, candidate, notes)

    if not result.get("ok"):
        return {
            "status": "error",
            "message": "Promotion blocked.",
            "candidate_id": candidate_id_value,
            "result": result,
        }, 1

    promoted_at = now_iso()
    fields = {
        "promoted_to": target,
        "promoted_at": promoted_at,
        "promotion_notes": notes or f"Promoted manually to {target}.",
    }
    if target == "normalization_rules":
        fields["promoted_rule_id"] = result.get("promoted_rule_id")
    else:
        fields["promoted_term"] = result.get("promoted_term")
    update_candidate_status(path=path, payload=payload, candidate=candidate, status="promoted", fields=fields)

    log_payload = {
        "candidate_id": candidate_id_value,
        "context": context,
        "promoted_to": target,
        "target_file": result.get("target_file"),
        "promoted_at": promoted_at,
    }
    append_jsonl(candidates_dir(root, context) / "promotion_log.jsonl", log_payload)

    return {
        "status": "ok",
        "message": MSG_PROMOTED,
        "candidate_id": candidate_id_value,
        "candidate_file": rel(path, root),
        "result": result,
    }, 0


def reject_candidate(
    *,
    root: Path,
    context: str,
    candidate_id_value: str,
    notes: str = "",
) -> tuple[dict[str, Any], int]:
    path, payload, candidate = find_candidate(root, context, candidate_id_value)
    if path is None or payload is None or candidate is None:
        return {"status": "error", "message": MSG_NO_CANDIDATE, "candidate_id": candidate_id_value}, 1
    update_candidate_status(
        path=path,
        payload=payload,
        candidate=candidate,
        status="rejected",
        fields={"rejected_at": now_iso(), "rejection_notes": notes},
    )
    return {
        "status": "ok",
        "message": MSG_REJECTED,
        "candidate_id": candidate_id_value,
        "candidate_file": rel(path, root),
    }, 0


def print_candidate_table(candidates: list[dict[str, Any]]) -> None:
    if not candidates:
        print("No candidates found.")
        return
    for candidate in candidates:
        print(
            "\t".join(
                [
                    str(candidate.get("id", "")),
                    str(candidate.get("observed", "")),
                    str(candidate.get("possible_canonical") or ""),
                    str(candidate.get("status", "")),
                    str(candidate.get("source", "")),
                    str(candidate.get("target", "")),
                ]
            )
        )


def main() -> int:
    args = parse_args()
    root = project_root()

    if args.command == "collect":
        payload = collect_candidates(root=root, basename=args.basename, context=args.context, force=args.force)
        if args.dry_run:
            if args.json:
                print(json.dumps({**payload, "dry_run": True}, ensure_ascii=False, indent=2))
            else:
                print(MSG_DRY_RUN)
                print_candidate_table(payload["candidates"])
            return 0
        write_json(candidate_file(root, args.context, args.basename), payload)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Candidate file: {payload['candidate_file']}")
            print(f"Candidates: {payload['candidate_count']}")
            if args.verbose and payload.get("warnings"):
                print(json.dumps(payload["warnings"], ensure_ascii=False, indent=2))
        return 0

    if args.command == "list":
        payload = list_candidates(root=root, context=args.context, status=args.status, source=args.source)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print_candidate_table(payload["candidates"])
        return 0

    if args.command == "promote":
        payload, code = promote_candidate(
            root=root,
            context=args.context,
            candidate_id_value=args.candidate_id,
            target=args.to,
            notes=args.notes,
        )
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        elif code == 0:
            print(payload["message"])
        else:
            print(payload["message"], file=sys.stderr)
        return code

    if args.command == "reject":
        payload, code = reject_candidate(
            root=root,
            context=args.context,
            candidate_id_value=args.candidate_id,
            notes=args.notes,
        )
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        elif code == 0:
            print(payload["message"])
        else:
            print(payload["message"], file=sys.stderr)
        return code

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
