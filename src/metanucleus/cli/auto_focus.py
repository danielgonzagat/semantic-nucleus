"""Suggest targeted pytest selections based on auto-report output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

CATEGORY_TESTS: Dict[str, List[str]] = {
    "semantic": [
        "tests/nsr/test_meta_*",
        "tests/test_evolution_semantics_smoke.py",
    ],
    "rule": [
        "tests/test_evolution_rules_smoke.py",
        "tests/nsr/test_meta_reasoner.py",
    ],
    "meta_calculus": [
        "tests/test_meta_calculus_smoke.py",
        "tests/nsr/test_meta_calculator.py",
        "tests/nsr/test_meta_calculus_router.py",
    ],
    "logic": [
        "tests/nsr/test_logic_*",
        "tests/test_runtime_semantic_integration.py",
    ],
    "meta_memory": [
        "tests/nsr/test_meta_memory*.py",
    ],
    "default": [
        "tests",
    ],
}


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="nucleo-auto-focus",
        description="Read auto-report JSON and suggest focused pytest targets.",
    )
    parser.add_argument(
        "--report",
        required=False,
        default="ci-artifacts/auto-report.json",
        help="Path to auto-report JSON (defaults to ci-artifacts/auto-report.json).",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "command"],
        default="text",
        help="Output format: human-readable text (default), JSON summary, or bare pytest command.",
    )
    parser.add_argument(
        "--base-command",
        default="pytest",
        help="Base command when using --format command (default: pytest).",
    )
    return parser.parse_args(argv)


def _load_entries(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError("Report is not a list of entries.")
        return data


def select_targets(
    entries: Iterable[dict],
    mapping: Dict[str, List[str]],
) -> Tuple[Set[str], Set[str]]:
    selected: Set[str] = set()
    unknown: Set[str] = set()
    for entry in entries:
        label = str(entry.get("label") or "").strip()
        if not label:
            continue
        patterns = mapping.get(label)
        if patterns:
            for pattern in patterns:
                selected.add(pattern)
        else:
            unknown.add(label)
    if not selected and mapping.get("default"):
        for pattern in mapping["default"]:
            selected.add(pattern)
    return selected, unknown


def render_text(selected: Sequence[str], unknown: Sequence[str]) -> str:
    lines = []
    if selected:
        lines.append("Suggested pytest targets:")
        for pattern in selected:
            lines.append(f"  - {pattern}")
    else:
        lines.append("No specific targets identified; run the full test suite.")
    if unknown:
        lines.append("")
        lines.append("Unmapped categories (consider updating the mapping):")
        for label in unknown:
            lines.append(f"  - {label}")
    return "\n".join(lines)


def render_json(selected: Sequence[str], unknown: Sequence[str]) -> str:
    payload = {
        "targets": list(selected),
        "unmapped_categories": list(unknown),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_command(selected: Sequence[str], base_command: str) -> str:
    parts: List[str] = [base_command]
    if selected:
        parts.extend(selected)
    else:
        parts.append("tests")
    return " ".join(parts)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    report_path = Path(args.report)
    if not report_path.exists():
        raise SystemExit(f"Report file not found: {report_path}")
    entries = _load_entries(report_path)
    selected, unknown = select_targets(entries, CATEGORY_TESTS)
    ordered_selected = sorted(selected)
    ordered_unknown = sorted(unknown)

    if args.format == "text":
        print(render_text(ordered_selected, ordered_unknown))
    elif args.format == "json":
        print(render_json(ordered_selected, ordered_unknown))
    elif args.format == "command":
        print(build_command(ordered_selected, args.base_command))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
