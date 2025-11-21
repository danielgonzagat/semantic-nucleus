from __future__ import annotations

import argparse

from nsr_evo.env_kb import promote_kb_version


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m nsr_evo.cli_promote_kb",
        description="Promove um arquivo de regras aprendido entre ambientes (dev → staging → prod).",
    )
    parser.add_argument("--from-env", required=True, help="Ambiente de origem (ex.: dev).")
    parser.add_argument("--to-env", required=True, help="Ambiente de destino (ex.: staging).")
    parser.add_argument(
        "--version",
        type=int,
        required=True,
        help="Versão numérica do arquivo learned_rules_v{N}.jsonl que será promovido.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    dst = promote_kb_version(args.from_env, args.to_env, args.version)
    print(
        f"[nsr_evo] promoted KB v{args.version} "
        f"from {args.from_env} -> {args.to_env} ({dst})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
