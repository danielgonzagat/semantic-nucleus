#!/usr/bin/env python3
"""
Converte uma especificação compacta (DSL JSON) em um LanguagePack completo.

Formato de entrada (JSON):
{
  "code": "xx",
  "lexemes": {
    "OI": {"semantics": "GREETING_SIMPLE", "pos": "INTERJ", "forms": ["oi", "ola"]}
  },
  "dialog": [
    {"trigger": "GREETING_SIMPLE", "reply": "GREETING_SIMPLE_REPLY", "semantics": "GREETING_SIMPLE",
     "language": "xx", "surface": ["oi"]}
  ],
  "conjugations": [
    {"lemma": "estar", "tense": "pres", "person": 1, "number": "sing", "form": "estou"}
  ],
  "stopwords": ["O", "A"],
  "patterns": [
    {"name": "GREETING_SIMPLE_XX", "sequence": ["GREETING_SIMPLE"]}
  ],
  "idioms": [
    {"source": "oi", "target": "hello"}
  ]
}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


def _upper_forms(forms: List[str]) -> List[str]:
    return [form.upper() for form in forms]


def load_dsl(path: str) -> Dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_pack_payload(dsl: Dict) -> Dict:
    code = (dsl.get("code") or "").lower()
    if not code:
        raise ValueError("DSL requires a 'code' field.")
    lexemes_dsl = dsl.get("lexemes", {})
    lexemes = []
    for lemma, spec in lexemes_dsl.items():
        lexemes.append(
            {
                "lemma": lemma.upper(),
                "semantics": spec["semantics"],
                "pos": spec["pos"],
                "forms": _upper_forms(spec.get("forms", [lemma])),
            }
        )
    dialog = []
    for entry in dsl.get("dialog", []):
        surface = entry.get("surface", [])
        if isinstance(surface, str):
            surface_tokens = surface.split()
        else:
            surface_tokens = list(surface)
        dialog.append(
            {
                "trigger_role": entry["trigger"],
                "reply_role": entry["reply"],
                "reply_semantics": entry["semantics"],
                "surface_tokens": surface_tokens,
                "language": entry.get("language", code),
            }
        )
    conjugations = dsl.get("conjugations", [])
    stopwords = _upper_forms(dsl.get("stopwords", []))
    patterns = [
        {"name": pattern["name"], "sequence": pattern["sequence"]}
        for pattern in dsl.get("patterns", [])
    ]
    idioms = [
        {"source": item["source"], "target": item["target"]}
        for item in dsl.get("idioms", [])
    ]
    return {
        "code": code,
        "lexemes": lexemes,
        "dialog_rules": dialog,
        "conjugations": conjugations,
        "stopwords": stopwords,
        "syntactic_patterns": patterns,
        "idiom_equivalents": idioms,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Converte DSL JSON para o formato LanguagePack.")
    parser.add_argument("--input", required=True, help="Arquivo DSL (JSON).")
    parser.add_argument("--output", required=True, help="Arquivo de saída JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dsl = load_dsl(args.input)
    payload = build_pack_payload(dsl)
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Pack '{payload['code']}' gerado em {args.output}")


if __name__ == "__main__":
    main()
