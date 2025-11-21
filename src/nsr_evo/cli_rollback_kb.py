from __future__ import annotations

import argparse

from nsr_evo.env_kb import rollback_kb_version


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m nsr_evo.cli_rollback_kb",
        description="Atualiza current_kb.json para apontar uma versão específica das regras.",
    )
    parser.add_argument("--env", required=True, help="Ambiente alvo (dev/staging/prod/etc.).")
    parser.add_argument(
        "--to-version",
        type=int,
        required=True,
        help="Versão desejada (usa learned_rules_v{N}.jsonl).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    target = rollback_kb_version(args.env, args.to_version)
    print(f"[nsr_evo] {args.env} now points to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
