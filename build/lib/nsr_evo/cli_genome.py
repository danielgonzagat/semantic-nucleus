from __future__ import annotations

import argparse
from pathlib import Path

from nsr_evo.genome import load_genome, summarize_genome, set_rule_disabled


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m nsr_evo.cli_genome",
        description="Inspeciona e ajusta o genoma simbólico (regras aprendidas).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_cmd = sub.add_parser("list", help="Lista regras aprendidas.")
    list_cmd.add_argument(
        "--rules",
        default=".nsr_learning/learned_rules.jsonl",
        help="Arquivo de regras aprendidas.",
    )

    toggle_cmd = sub.add_parser("toggle", help="Ativa/Desativa uma regra pelo índice.")
    toggle_cmd.add_argument(
        "--rules",
        default=".nsr_learning/learned_rules.jsonl",
        help="Arquivo de regras aprendidas.",
    )
    toggle_cmd.add_argument("--index", type=int, required=True, help="Índice da regra.")
    group = toggle_cmd.add_mutually_exclusive_group(required=True)
    group.add_argument("--disable", action="store_true", help="Desativa a regra.")
    group.add_argument("--enable", action="store_true", help="Reativa a regra.")

    return parser


def _cmd_list(path: Path) -> int:
    summary = summarize_genome(path)
    print(
        f"[nsr_evo] rules total={summary.total} active={summary.active} "
        f"disabled={summary.disabled} avg_support={summary.avg_support:.2f} "
        f"avg_energy_gain={summary.avg_energy_gain:.3f}"
    )
    for entry in load_genome(path):
        spec = entry.spec
        status = "disabled" if spec.disabled else "active"
        version = spec.version or "-"
        gain = spec.energy_gain
        print(
            f"[{entry.index}] v{version} sup={spec.support} gain={gain:.3f} "
            f"{status} :: {spec.if_all} -> {spec.then}"
        )
    return 0


def _cmd_toggle(path: Path, index: int, disable: bool) -> int:
    set_rule_disabled(path, index, disable)
    state = "disabled" if disable else "enabled"
    print(f"[nsr_evo] rule[{index}] marked as {state}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    rules_path = Path(args.rules)

    if args.command == "list":
        return _cmd_list(rules_path)
    if args.command == "toggle":
        return _cmd_toggle(rules_path, args.index, disable=args.disable)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
