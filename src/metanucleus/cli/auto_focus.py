"""Suggest targeted pytest selections based on auto-report output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

DEFAULT_CATEGORY_TESTS: Dict[str, List[str]] = {
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
    parser.add_argument(
        "--config",
        help="JSON file mapping mismatch labels to pytest targets.",
    )
    parser.add_argument(
        "--config-mode",
        choices=["merge", "replace"],
        default="merge",
        help="How to combine --config with o mapeamento padrão (default: %(default)s).",
    )
    return parser.parse_args(argv)


def load_entries(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError("Report is not a list of entries.")
        return data


def _normalize_patterns(value) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    raise ValueError("Each mapping entry must be a string or list of strings.")


def load_mapping(path: Path | None, *, mode: str = "merge") -> Dict[str, List[str]]:
    if mode not in {"merge", "replace"}:
        raise ValueError("mode must be 'merge' or 'replace'")
    mapping: Dict[str, List[str]] = (
        {label: list(patterns) for label, patterns in DEFAULT_CATEGORY_TESTS.items()}
        if mode == "merge"
        else {}
    )
    if not path:
        return mapping
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as exc:
        raise ValueError(f"unable to read focus config: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in focus config: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("focus config must be a JSON object {label: [patterns]}")
    for label, value in data.items():
        mapping[label] = _normalize_patterns(value)
    return mapping


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
    config_path = Path(args.config).resolve() if args.config else None
    try:
        mapping = load_mapping(config_path, mode=args.config_mode)
    except ValueError as exc:
        raise SystemExit(str(exc))
    entries = load_entries(report_path)
    selected, unknown = select_targets(entries, mapping)
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
