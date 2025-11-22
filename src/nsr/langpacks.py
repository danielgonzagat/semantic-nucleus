"""
Recursos linguísticos determinísticos obtidos via ferramentas externas (LLMs, tradutores)
e cristalizados como tabelas estáticas para o núcleo simbólico.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Tuple


@dataclass(frozen=True)
class LexemeSpec:
    lemma: str
    semantics: str
    pos: str
    forms: Tuple[str, ...]


@dataclass(frozen=True)
class DialogRuleSpec:
    trigger_role: str
    reply_role: str
    reply_semantics: str
    surface_tokens: Tuple[str, ...]
    language: str


@dataclass(frozen=True)
class ConjugationSpec:
    lemma: str
    tense: str
    person: int
    number: str
    form: str


@dataclass(frozen=True)
class SyntacticPatternSpec:
    name: str
    sequence: Tuple[str, ...]


@dataclass(frozen=True)
class IdiomEquivalentSpec:
    source: str
    target: str


@dataclass(frozen=True)
class LanguagePack:
    code: str
    lexemes: Tuple[LexemeSpec, ...]
    dialog_rules: Tuple[DialogRuleSpec, ...]
    conjugations: Tuple[ConjugationSpec, ...] = ()
    stopwords: Tuple[str, ...] = ()
    syntactic_patterns: Tuple[SyntacticPatternSpec, ...] = ()
    idiom_equivalents: Tuple[IdiomEquivalentSpec, ...] = ()


LANGPACKS_DIR = Path(os.environ.get("NSR_LANGPACKS_DIR", Path(__file__).with_suffix("").with_name("langpacks_data")))
LANGPACKS_DIR.mkdir(parents=True, exist_ok=True)
_PACK_CACHE: Dict[str, LanguagePack] = {}
EXTERNAL_LANGUAGE_PACK_DATA: Dict[str, Dict] = {}


def _merged_payload(code: str) -> Dict:
    base = LANGUAGE_PACK_DATA.get(code, {})
    external = EXTERNAL_LANGUAGE_PACK_DATA.get(code, {})
    merged = dict(base)
    for key, value in external.items():
        if key in {"lexemes", "dialog_rules", "conjugations", "stopwords", "syntactic_patterns", "idiom_equivalents"}:
            base_list = list(base.get(key, []))
            merged[key] = base_list + list(value)
        else:
            merged[key] = value
    merged.setdefault("code", code)
    return merged


def build_language_pack_from_dict(code: str, data: Dict) -> LanguagePack:
    lexemes = tuple(
        LexemeSpec(
            lemma=entry["lemma"],
            semantics=entry["semantics"],
            pos=entry["pos"],
            forms=tuple(entry["forms"]),
        )
        for entry in data.get("lexemes", ())
    )
    dialog_rules = tuple(
        DialogRuleSpec(
            trigger_role=entry["trigger_role"],
            reply_role=entry["reply_role"],
            reply_semantics=entry["reply_semantics"],
            surface_tokens=tuple(entry["surface_tokens"]),
            language=entry["language"],
        )
        for entry in data.get("dialog_rules", ())
    )
    conjugations = tuple(
        ConjugationSpec(
            lemma=entry["lemma"],
            tense=entry["tense"],
            person=entry["person"],
            number=entry["number"],
            form=entry["form"],
        )
        for entry in data.get("conjugations", ())
    )
    stopwords = tuple(entry.upper() for entry in data.get("stopwords", ()))
    patterns = tuple(
        SyntacticPatternSpec(name=entry["name"], sequence=tuple(entry["sequence"]))
        for entry in data.get("syntactic_patterns", ())
    )
    idioms = tuple(
        IdiomEquivalentSpec(source=entry["source"], target=entry["target"])
        for entry in data.get("idiom_equivalents", ())
    )
    return LanguagePack(
        code=code,
        lexemes=lexemes,
        dialog_rules=dialog_rules,
        conjugations=conjugations,
        stopwords=stopwords,
        syntactic_patterns=patterns,
        idiom_equivalents=idioms,
    )


def get_language_pack(code: str) -> LanguagePack:
    normalized = code.lower()
    payload = _merged_payload(normalized)
    if not payload:
        raise ValueError(f"Unknown language pack '{code}'")
    if normalized not in _PACK_CACHE:
        _PACK_CACHE[normalized] = build_language_pack_from_dict(normalized, payload)
    return _PACK_CACHE[normalized]


def iter_language_packs(codes: Iterable[str]) -> Tuple[LanguagePack, ...]:
    return tuple(get_language_pack(code) for code in codes)


def list_available_codes() -> Tuple[str, ...]:
    codes = set(LANGUAGE_PACK_DATA.keys()) | set(EXTERNAL_LANGUAGE_PACK_DATA.keys())
    return tuple(sorted(codes))


def import_language_pack(code: str | None, json_path: str) -> str:
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(json_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    pack_code = (code or payload.get("code") or "").lower()
    if not pack_code:
        raise ValueError("Language pack requires a 'code' field or --code argument.")
    payload["code"] = pack_code
    target = LANGPACKS_DIR / f"{pack_code}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    EXTERNAL_LANGUAGE_PACK_DATA[pack_code] = payload
    _PACK_CACHE.pop(pack_code, None)
    return pack_code


def _load_external_packs() -> Dict[str, Dict]:
    data: Dict[str, Dict] = {}
    if not LANGPACKS_DIR.exists():
        return data
    for path in LANGPACKS_DIR.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        code = (payload.get("code") or path.stem).lower()
        payload["code"] = code
        data[code] = payload
    return data


def _cli(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Language pack manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List available language packs")
    list_parser.add_argument("--codes", action="store_true", help="Only print codes")

    import_parser = subparsers.add_parser("import", help="Import a language pack JSON file")
    import_parser.add_argument("file", help="Path to JSON file")
    import_parser.add_argument("--code", help="Override language code")

    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "list":
        codes = list_available_codes()
        if args.codes:
            print("\n".join(codes))
        else:
            for code in codes:
                pack = get_language_pack(code)
                print(f"{code}: {len(pack.lexemes)} lexemes, {len(pack.dialog_rules)} rules")
        return 0
    if args.command == "import":
        code = import_language_pack(args.code, args.file)
        print(f"Imported language pack '{code}' into {LANGPACKS_DIR}")
        return 0
    return 1


LANGUAGE_PACK_DATA: Dict[str, Dict] = {
    "pt": {
        "lexemes": [
            {"lemma": "OI", "semantics": "GREETING_SIMPLE", "pos": "INTERJ", "forms": ["OI", "OLÁ", "OLA"]},
            {"lemma": "TUDO", "semantics": "ALL_THINGS", "pos": "PRON_INDEF", "forms": ["TUDO"]},
            {"lemma": "BEM", "semantics": "STATE_GOOD", "pos": "ADV", "forms": ["BEM"]},
            {"lemma": "E", "semantics": "CONJ_AND", "pos": "CONJ", "forms": ["E"]},
            {"lemma": "VOCÊ", "semantics": "YOU", "pos": "PRON", "forms": ["VOCÊ", "VOCE"]},
            {"lemma": "EU", "semantics": "SELF", "pos": "PRON", "forms": ["EU"]},
            {"lemma": "SIM", "semantics": "AFFIRM", "pos": "ADV", "forms": ["SIM"]},
            {"lemma": "NÃO", "semantics": "NEGATE", "pos": "ADV", "forms": ["NÃO", "NAO"]},
            {"lemma": "COMO", "semantics": "QUESTION_HOW", "pos": "ADV", "forms": ["COMO"]},
            {"lemma": "ESTAR", "semantics": "BE_STATE", "pos": "VERB", "forms": ["ESTÁ", "ESTA", "ESTOU", "ESTAS"]},
            {"lemma": "MAL", "semantics": "STATE_BAD", "pos": "ADV", "forms": ["MAL"]},
            {"lemma": "RUIM", "semantics": "STATE_BAD", "pos": "ADJ", "forms": ["RUIM"]},
            {"lemma": "TRISTE", "semantics": "STATE_BAD", "pos": "ADJ", "forms": ["TRISTE"]},
        ],
        "stopwords": ["O", "A", "OS", "AS", "DE", "DO", "DA", "QUE", "E", "UM", "UMA"],
        "syntactic_patterns": [
            {"name": "GREETING_SIMPLE", "sequence": ["GREETING_SIMPLE"]},
            {"name": "QUESTION_HEALTH", "sequence": ["ALL_THINGS", "STATE_GOOD"]},
            {"name": "QUESTION_HEALTH_VERBOSE", "sequence": ["QUESTION_HOW", "YOU", "BE_STATE"]},
            {"name": "ANSWER_HEALTH", "sequence": ["STATE_GOOD", "CONJ_AND", "YOU"]},
        ],
        "idiom_equivalents": [
            {"source": "tudo bem", "target": "all good"},
            {"source": "como você está", "target": "how are you"},
        ],
        "dialog_rules": [
            {
                "trigger_role": "QUESTION_HEALTH",
                "reply_role": "ANSWER_HEALTH_AND_RETURN",
                "reply_semantics": "STATE_GOOD_AND_RETURN",
                "surface_tokens": ["tudo", "bem", ",", "e", "você", "?"],
                "language": "pt",
            },
            {
                "trigger_role": "GREETING_SIMPLE",
                "reply_role": "GREETING_SIMPLE_REPLY",
                "reply_semantics": "GREETING_SIMPLE",
                "surface_tokens": ["oi"],
                "language": "pt",
            },
            {
                "trigger_role": "QUESTION_HEALTH_VERBOSE",
                "reply_role": "ANSWER_HEALTH_VERBOSE",
                "reply_semantics": "STATE_GOOD_AND_RETURN",
                "surface_tokens": [":CONJ:estar:pres:1:sing", "bem", ",", "e", "você", "?"],
                "language": "pt",
            },
            {
                "trigger_role": "STATE_POSITIVE",
                "reply_role": "ACK_POSITIVE",
                "reply_semantics": "STATE_POSITIVE_ACK",
                "surface_tokens": ["que", "bom", "!"],
                "language": "pt",
            },
            {
                "trigger_role": "STATE_NEGATIVE",
                "reply_role": "CARE_NEGATIVE",
                "reply_semantics": "STATE_NEGATIVE_SUPPORT",
                "surface_tokens": ["sinto", "muito", ".", "posso", "ajudar", "?"],
                "language": "pt",
            },
        ],
        "conjugations": [
            {"lemma": "estar", "tense": "pres", "person": 1, "number": "sing", "form": "estou"},
            {"lemma": "estar", "tense": "pres", "person": 2, "number": "sing", "form": "está"},
            {"lemma": "estar", "tense": "pres", "person": 3, "number": "sing", "form": "está"},
            {"lemma": "estar", "tense": "pres", "person": 1, "number": "plur", "form": "estamos"},
            {"lemma": "estar", "tense": "pres", "person": 2, "number": "plur", "form": "estão"},
            {"lemma": "estar", "tense": "pres", "person": 3, "number": "plur", "form": "estão"},
        ],
    },
    "en": {
        "lexemes": [
            {"lemma": "HI", "semantics": "GREETING_SIMPLE", "pos": "INTERJ", "forms": ["HI", "HELLO", "HEY"]},
            {"lemma": "FINE", "semantics": "STATE_GOOD", "pos": "ADJ", "forms": ["FINE", "GOOD"]},
            {"lemma": "YOU", "semantics": "YOU", "pos": "PRON", "forms": ["YOU"]},
            {"lemma": "I", "semantics": "SELF", "pos": "PRON", "forms": ["I"]},
            {"lemma": "HOW", "semantics": "QUESTION_HOW", "pos": "ADV", "forms": ["HOW"]},
            {"lemma": "BE", "semantics": "BE_STATE", "pos": "VERB", "forms": ["ARE", "AM", "IS"]},
        ],
        "stopwords": ["THE", "A", "AN", "IS", "ARE", "AM", "OF", "AND"],
        "syntactic_patterns": [
            {"name": "GREETING_SIMPLE_EN", "sequence": ["GREETING_SIMPLE"]},
            {"name": "QUESTION_HEALTH_VERBOSE_EN", "sequence": ["QUESTION_HOW", "SELF", "STATE_GOOD"]},
        ],
        "idiom_equivalents": [
            {"source": "how are you", "target": "como você está"},
            {"source": "i am fine", "target": "estou bem"},
        ],
        "dialog_rules": [
            {
                "trigger_role": "GREETING_SIMPLE_EN",
                "reply_role": "GREETING_SIMPLE_EN_REPLY",
                "reply_semantics": "GREETING_SIMPLE",
                "surface_tokens": ["hi"],
                "language": "en",
            },
            {
                "trigger_role": "QUESTION_HEALTH_VERBOSE_EN",
                "reply_role": "ANSWER_HEALTH_VERBOSE_EN",
                "reply_semantics": "STATE_GOOD_AND_RETURN",
                "surface_tokens": ["i", "am", "fine", ",", "and", "you", "?"],
                "language": "en",
            },
        ],
        "conjugations": [
            {"lemma": "be", "tense": "pres", "person": 1, "number": "sing", "form": "am"},
            {"lemma": "be", "tense": "pres", "person": 2, "number": "sing", "form": "are"},
            {"lemma": "be", "tense": "pres", "person": 3, "number": "sing", "form": "is"},
        ],
    },
    "es": {
        "lexemes": [
            {"lemma": "HOLA", "semantics": "GREETING_SIMPLE", "pos": "INTERJ", "forms": ["HOLA"]},
            {"lemma": "TODO", "semantics": "ALL_THINGS", "pos": "PRON_INDEF", "forms": ["TODO"]},
            {"lemma": "BIEN", "semantics": "STATE_GOOD", "pos": "ADV", "forms": ["BIEN"]},
            {"lemma": "Y", "semantics": "CONJ_AND", "pos": "CONJ", "forms": ["Y"]},
            {"lemma": "TÚ", "semantics": "YOU", "pos": "PRON", "forms": ["TÚ", "TU"]},
            {"lemma": "COMO", "semantics": "QUESTION_HOW", "pos": "ADV", "forms": ["COMO", "CÓMO"]},
            {"lemma": "ESTAR", "semantics": "BE_STATE", "pos": "VERB", "forms": ["ESTOY", "ESTÁS", "ESTA"]},
        ],
        "stopwords": ["EL", "LA", "LOS", "LAS", "DE", "Y", "QUE", "UN", "UNA"],
        "syntactic_patterns": [
            {"name": "GREETING_SIMPLE_ES", "sequence": ["GREETING_SIMPLE"]},
            {"name": "QUESTION_HEALTH_ES", "sequence": ["ALL_THINGS", "STATE_GOOD"]},
            {"name": "QUESTION_HEALTH_VERBOSE_ES", "sequence": ["SELF", "STATE_GOOD", "CONJ_AND", "YOU"]},
        ],
        "idiom_equivalents": [
            {"source": "todo bien", "target": "all good"},
            {"source": "¿cómo estás?", "target": "how are you"},
        ],
        "dialog_rules": [
            {
                "trigger_role": "QUESTION_HEALTH_ES",
                "reply_role": "ANSWER_HEALTH_ES",
                "reply_semantics": "STATE_GOOD_AND_RETURN",
                "surface_tokens": ["todo", "bien", ",", "y", "tú", "?"],
                "language": "es",
            },
            {
                "trigger_role": "QUESTION_HEALTH_VERBOSE_ES",
                "reply_role": "ANSWER_HEALTH_VERBOSE_ES",
                "reply_semantics": "STATE_GOOD_AND_RETURN",
                "surface_tokens": ["estoy", "bien", ",", "y", "tú", "?"],
                "language": "es",
            },
        ],
        "conjugations": [
            {"lemma": "estar", "tense": "pres", "person": 1, "number": "sing", "form": "estoy"},
            {"lemma": "estar", "tense": "pres", "person": 2, "number": "sing", "form": "estás"},
            {"lemma": "estar", "tense": "pres", "person": 3, "number": "sing", "form": "está"},
        ],
    },
    "fr": {
        "lexemes": [
            {"lemma": "BONJOUR", "semantics": "GREETING_SIMPLE", "pos": "INTERJ", "forms": ["BONJOUR"]},
            {"lemma": "SALUT", "semantics": "GREETING_SIMPLE", "pos": "INTERJ", "forms": ["SALUT"]},
            {"lemma": "TOUT", "semantics": "ALL_THINGS", "pos": "PRON_INDEF", "forms": ["TOUT"]},
            {"lemma": "BIEN", "semantics": "STATE_GOOD", "pos": "ADV", "forms": ["BIEN"]},
            {"lemma": "ET", "semantics": "CONJ_AND", "pos": "CONJ", "forms": ["ET"]},
            {"lemma": "TOI", "semantics": "YOU", "pos": "PRON", "forms": ["TOI"]},
            {"lemma": "COMMENT", "semantics": "QUESTION_HOW", "pos": "ADV", "forms": ["COMMENT"]},
            {"lemma": "ÇA", "semantics": "YOU", "pos": "PRON", "forms": ["ÇA", "CA"]},
            {"lemma": "JE", "semantics": "SELF", "pos": "PRON", "forms": ["JE"]},
            {"lemma": "ALLER", "semantics": "BE_STATE", "pos": "VERB", "forms": ["VA", "VAS", "VAIS"]},
        ],
        "stopwords": ["LE", "LA", "LES", "DES", "ET", "DE", "UN", "UNE"],
        "syntactic_patterns": [
            {"name": "GREETING_SIMPLE_FR", "sequence": ["GREETING_SIMPLE"]},
            {"name": "QUESTION_HEALTH_FR", "sequence": ["ALL_THINGS", "STATE_GOOD"]},
            {"name": "QUESTION_HEALTH_VERBOSE_FR", "sequence": ["SELF", "BE_STATE", "STATE_GOOD", "CONJ_AND", "YOU"]},
        ],
        "idiom_equivalents": [
            {"source": "comment ça va", "target": "how are you"},
            {"source": "tout va bien", "target": "everything is fine"},
        ],
        "dialog_rules": [
            {
                "trigger_role": "GREETING_SIMPLE_FR",
                "reply_role": "GREETING_SIMPLE_FR_REPLY",
                "reply_semantics": "GREETING_SIMPLE",
                "surface_tokens": ["bonjour"],
                "language": "fr",
            },
            {
                "trigger_role": "QUESTION_HEALTH_FR",
                "reply_role": "ANSWER_HEALTH_FR",
                "reply_semantics": "STATE_GOOD_AND_RETURN",
                "surface_tokens": ["tout", "va", "bien", ",", "et", "toi", "?"],
                "language": "fr",
            },
            {
                "trigger_role": "QUESTION_HEALTH_VERBOSE_FR",
                "reply_role": "ANSWER_HEALTH_VERBOSE_FR",
                "reply_semantics": "STATE_GOOD_AND_RETURN",
                "surface_tokens": ["je", "vais", "bien", ",", "et", "toi", "?"],
                "language": "fr",
            },
        ],
        "conjugations": [
            {"lemma": "aller", "tense": "pres", "person": 1, "number": "sing", "form": "vais"},
            {"lemma": "aller", "tense": "pres", "person": 2, "number": "sing", "form": "vas"},
            {"lemma": "aller", "tense": "pres", "person": 3, "number": "sing", "form": "va"},
        ],
      },
      "it": {
          "lexemes": [
              {"lemma": "CIAO", "semantics": "GREETING_SIMPLE", "pos": "INTERJ", "forms": ["CIAO"]},
              {"lemma": "TUTTO", "semantics": "ALL_THINGS", "pos": "PRON_INDEF", "forms": ["TUTTO"]},
              {"lemma": "BENE", "semantics": "STATE_GOOD", "pos": "ADV", "forms": ["BENE"]},
              {"lemma": "E", "semantics": "CONJ_AND", "pos": "CONJ", "forms": ["E", "ED"]},
              {"lemma": "TU", "semantics": "YOU", "pos": "PRON", "forms": ["TU"]},
              {"lemma": "COME", "semantics": "QUESTION_HOW", "pos": "ADV", "forms": ["COME"]},
              {"lemma": "STARE", "semantics": "BE_STATE", "pos": "VERB", "forms": ["STAI", "STO", "STA"]},
              {"lemma": "IO", "semantics": "SELF", "pos": "PRON", "forms": ["IO"]},
          ],
          "stopwords": ["IL", "LA", "LO", "GLI", "LE", "DI", "CHE", "E", "UN", "UNA"],
          "syntactic_patterns": [
              {"name": "GREETING_SIMPLE_IT", "sequence": ["GREETING_SIMPLE"]},
              {"name": "QUESTION_HEALTH_IT", "sequence": ["ALL_THINGS", "STATE_GOOD"]},
              {"name": "QUESTION_HEALTH_VERBOSE_IT", "sequence": ["QUESTION_HOW", "BE_STATE"]},
          ],
          "idiom_equivalents": [
              {"source": "tutto bene", "target": "all good"},
              {"source": "come stai", "target": "how are you"},
          ],
          "dialog_rules": [
              {
                  "trigger_role": "GREETING_SIMPLE_IT",
                  "reply_role": "GREETING_SIMPLE_IT_REPLY",
                  "reply_semantics": "GREETING_SIMPLE",
                  "surface_tokens": ["ciao"],
                  "language": "it",
              },
              {
                  "trigger_role": "QUESTION_HEALTH_IT",
                  "reply_role": "ANSWER_HEALTH_IT",
                  "reply_semantics": "STATE_GOOD_AND_RETURN",
                  "surface_tokens": ["tutto", "bene", ",", "e", "tu", "?"],
                  "language": "it",
              },
              {
                  "trigger_role": "QUESTION_HEALTH_VERBOSE_IT",
                  "reply_role": "ANSWER_HEALTH_VERBOSE_IT",
                  "reply_semantics": "STATE_GOOD_AND_RETURN",
                  "surface_tokens": [":CONJ:stare:pres:1:sing", "bene", ",", "e", "tu", "?"],
                  "language": "it",
              },
          ],
          "conjugations": [
              {"lemma": "stare", "tense": "pres", "person": 1, "number": "sing", "form": "sto"},
              {"lemma": "stare", "tense": "pres", "person": 2, "number": "sing", "form": "stai"},
              {"lemma": "stare", "tense": "pres", "person": 3, "number": "sing", "form": "sta"},
          ],
    },
}

EXTERNAL_LANGUAGE_PACK_DATA = _load_external_packs()


def reload_external_packs() -> None:
    global EXTERNAL_LANGUAGE_PACK_DATA
    EXTERNAL_LANGUAGE_PACK_DATA = _load_external_packs()
    _PACK_CACHE.clear()


__all__ = [
    "LanguagePack",
    "LexemeSpec",
    "DialogRuleSpec",
    "ConjugationSpec",
    "SyntacticPatternSpec",
    "IdiomEquivalentSpec",
    "build_language_pack_from_dict",
    "get_language_pack",
    "iter_language_packs",
    "list_available_codes",
    "import_language_pack",
    "reload_external_packs",
]


if __name__ == "__main__":
    raise SystemExit(_cli())

