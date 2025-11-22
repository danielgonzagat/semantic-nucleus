#!/usr/bin/env python3
"""
Valida pacotes de idioma embutidos ou arquivos externos.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from nsr.langpacks import (
    build_language_pack_from_dict,
    get_language_pack,
)
from nsr.langpacks_validator import has_errors, validate_pack


def load_pack_from_file(path: str):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    code = (payload.get("code") or Path(path).stem).lower()
    payload["code"] = code
    return build_language_pack_from_dict(code, payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validador determinístico de pacotes de idioma.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--code", help="Código de um idioma já disponível (ex.: pt, en, it).")
    group.add_argument("--file", help="Caminho para JSON de idioma a validar (não é importado).")
    parser.add_argument(
        "--fail-on-warn",
        action="store_true",
        help="Retorna código 1 mesmo se apenas warnings forem encontrados.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.code:
        pack = get_language_pack(args.code)
        origin = f"code '{args.code}'"
    else:
        pack = load_pack_from_file(args.file)
        origin = f"file '{args.file}'"
    issues = validate_pack(pack)
    if issues:
        for issue in issues:
            print(f"[{issue.severity.upper()}] {issue.message}")
    else:
        print(f"[OK] language pack {origin} passed validation")
    exit_code = 0
    if has_errors(issues):
        exit_code = 1
    elif args.fail_on_warn and issues:
        exit_code = 1
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
