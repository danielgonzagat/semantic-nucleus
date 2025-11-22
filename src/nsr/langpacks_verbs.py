"""
Geradores de verbos/conjugações para os LangPacks, compartilhados pelo IAN e pelo parser.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple


def _build_romance_verbs(
    verbs_by_group: Dict[str, Iterable[str]],
    patterns: Dict[str, Dict[str, Dict[str, object]]],
    semantics: str = "ACTION",
) -> Tuple[List[dict], List[dict], Dict[str, dict]]:
    lexemes: List[dict] = []
    conjugations: List[dict] = []
    metadata: Dict[str, dict] = {}
    for group, lemmas in verbs_by_group.items():
        group = group.lower()
        if group not in patterns:
            continue
        group_pattern = patterns[group]
        for lemma in lemmas:
            lemma = lemma.lower()
            forms_set = {lemma.upper()}
            for tense, pattern in group_pattern.items():
                base_mode = pattern["base"]
                for (person, number), ending in pattern["endings"].items():
                    if base_mode == "root":
                        base = lemma[:-2]
                    elif base_mode == "lemma":
                        base = lemma
                    elif base_mode == "lemma_drop_last":
                        base = lemma[:-1]
                    else:
                        base = lemma
                    form = (base + ending).lower()
                    conjugations.append(
                        {"lemma": lemma, "tense": tense, "person": person, "number": number, "form": form}
                    )
                    forms_set.add(form.upper())
                    metadata[form.upper()] = {
                        "lemma": lemma.upper(),
                        "tense": tense,
                        "person": person,
                        "number": number,
                    }
            lexemes.append({"lemma": lemma.upper(), "semantics": semantics, "pos": "VERB", "forms": sorted(forms_set)})
    return lexemes, conjugations, metadata


def build_pt_verbs() -> Tuple[List[dict], List[dict], Dict[str, dict]]:
    verbs = {
        "ar": [
            "falar",
            "andar",
            "amar",
            "chegar",
            "trabalhar",
            "estudar",
            "jogar",
            "lavar",
            "olhar",
            "pensar",
            "tocar",
            "usar",
            "viajar",
            "voltar",
            "ajudar",
            "cantar",
            "dançar",
            "encontrar",
            "esperar",
            "pagar",
            "tomar",
            "brincar",
            "comprar",
            "guardar",
        ],
        "er": [
            "comer",
            "beber",
            "correr",
            "escrever",
            "vender",
            "viver",
            "aprender",
            "receber",
            "ver",
            "crescer",
            "defender",
            "resolver",
            "mover",
            "escolher",
            "proteger",
        ],
        "ir": [
            "abrir",
            "assistir",
            "decidir",
            "dividir",
            "existir",
            "seguir",
            "unir",
            "servir",
            "permitir",
            "produzir",
            "surgir",
            "construir",
            "partir",
            "ferir",
            "expandir",
        ],
    }
    patterns = {
        "ar": {
            "pres": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "o",
                    ("2", "sing"): "as",
                    ("3", "sing"): "a",
                    ("1", "plur"): "amos",
                    ("2", "plur"): "ais",
                    ("3", "plur"): "am",
                },
            },
            "past": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "ei",
                    ("2", "sing"): "aste",
                    ("3", "sing"): "ou",
                    ("1", "plur"): "amos",
                    ("2", "plur"): "astes",
                    ("3", "plur"): "aram",
                },
            },
            "fut": {
                "base": "lemma",
                "endings": {
                    ("1", "sing"): "ei",
                    ("2", "sing"): "ás",
                    ("3", "sing"): "á",
                    ("1", "plur"): "emos",
                    ("2", "plur"): "eis",
                    ("3", "plur"): "ão",
                },
            },
        },
        "er": {
            "pres": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "o",
                    ("2", "sing"): "es",
                    ("3", "sing"): "e",
                    ("1", "plur"): "emos",
                    ("2", "plur"): "eis",
                    ("3", "plur"): "em",
                },
            },
            "past": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "i",
                    ("2", "sing"): "este",
                    ("3", "sing"): "eu",
                    ("1", "plur"): "emos",
                    ("2", "plur"): "estes",
                    ("3", "plur"): "eram",
                },
            },
            "fut": {
                "base": "lemma",
                "endings": {
                    ("1", "sing"): "ei",
                    ("2", "sing"): "ás",
                    ("3", "sing"): "á",
                    ("1", "plur"): "emos",
                    ("2", "plur"): "eis",
                    ("3", "plur"): "ão",
                },
            },
        },
        "ir": {
            "pres": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "o",
                    ("2", "sing"): "es",
                    ("3", "sing"): "e",
                    ("1", "plur"): "imos",
                    ("2", "plur"): "is",
                    ("3", "plur"): "em",
                },
            },
            "past": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "i",
                    ("2", "sing"): "iste",
                    ("3", "sing"): "iu",
                    ("1", "plur"): "imos",
                    ("2", "plur"): "istes",
                    ("3", "plur"): "iram",
                },
            },
            "fut": {
                "base": "lemma",
                "endings": {
                    ("1", "sing"): "ei",
                    ("2", "sing"): "ás",
                    ("3", "sing"): "á",
                    ("1", "plur"): "emos",
                    ("2", "plur"): "eis",
                    ("3", "plur"): "ão",
                },
            },
        },
    }
    return _build_romance_verbs(verbs, patterns)


def build_es_verbs() -> Tuple[List[dict], List[dict], Dict[str, dict]]:
    verbs = {
        "ar": [
            "hablar",
            "caminar",
            "amar",
            "llegar",
            "trabajar",
            "estudiar",
            "jugar",
            "lavar",
            "mirar",
            "pensar",
            "tocar",
            "usar",
            "viajar",
            "ayudar",
            "cantar",
            "bailar",
            "encontrar",
            "esperar",
            "pagar",
            "tomar",
            "comprar",
            "visitar",
            "llamar",
            "soñar",
            "gritar",
        ],
        "er": [
            "comer",
            "beber",
            "correr",
            "vender",
            "aprender",
            "leer",
            "creer",
            "romper",
            "defender",
            "ofrecer",
            "perder",
            "prender",
            "poseer",
            "temer",
            "mover",
        ],
        "ir": [
            "vivir",
            "abrir",
            "decidir",
            "escribir",
            "recibir",
            "subir",
            "seguir",
            "unir",
            "servir",
            "existir",
            "cumplir",
            "partir",
            "sentir",
            "permitir",
            "descubrir",
        ],
    }
    patterns = {
        "ar": {
            "pres": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "o",
                    ("2", "sing"): "as",
                    ("3", "sing"): "a",
                    ("1", "plur"): "amos",
                    ("2", "plur"): "áis",
                    ("3", "plur"): "an",
                },
            },
            "past": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "é",
                    ("2", "sing"): "aste",
                    ("3", "sing"): "ó",
                    ("1", "plur"): "amos",
                    ("2", "plur"): "asteis",
                    ("3", "plur"): "aron",
                },
            },
            "fut": {
                "base": "lemma",
                "endings": {
                    ("1", "sing"): "é",
                    ("2", "sing"): "ás",
                    ("3", "sing"): "á",
                    ("1", "plur"): "emos",
                    ("2", "plur"): "éis",
                    ("3", "plur"): "án",
                },
            },
        },
        "er": {
            "pres": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "o",
                    ("2", "sing"): "es",
                    ("3", "sing"): "e",
                    ("1", "plur"): "emos",
                    ("2", "plur"): "éis",
                    ("3", "plur"): "en",
                },
            },
            "past": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "í",
                    ("2", "sing"): "iste",
                    ("3", "sing"): "ió",
                    ("1", "plur"): "imos",
                    ("2", "plur"): "isteis",
                    ("3", "plur"): "ieron",
                },
            },
            "fut": {
                "base": "lemma",
                "endings": {
                    ("1", "sing"): "é",
                    ("2", "sing"): "ás",
                    ("3", "sing"): "á",
                    ("1", "plur"): "emos",
                    ("2", "plur"): "éis",
                    ("3", "plur"): "án",
                },
            },
        },
        "ir": {
            "pres": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "o",
                    ("2", "sing"): "es",
                    ("3", "sing"): "e",
                    ("1", "plur"): "imos",
                    ("2", "plur"): "ís",
                    ("3", "plur"): "en",
                },
            },
            "past": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "í",
                    ("2", "sing"): "iste",
                    ("3", "sing"): "ió",
                    ("1", "plur"): "imos",
                    ("2", "plur"): "isteis",
                    ("3", "plur"): "ieron",
                },
            },
            "fut": {
                "base": "lemma",
                "endings": {
                    ("1", "sing"): "é",
                    ("2", "sing"): "ás",
                    ("3", "sing"): "á",
                    ("1", "plur"): "emos",
                    ("2", "plur"): "éis",
                    ("3", "plur"): "án",
                },
            },
        },
    }
    return _build_romance_verbs(verbs, patterns)


def build_it_verbs() -> Tuple[List[dict], List[dict], Dict[str, dict]]:
    verbs = {
        "are": [
            "parlare",
            "amare",
            "cercare",
            "guardare",
            "giocare",
            "lavorare",
            "studiare",
            "cantare",
            "ballare",
            "trovare",
            "pensare",
            "sperare",
            "pagare",
            "comprare",
            "visitare",
        ],
        "ere": [
            "correre",
            "scrivere",
            "vendere",
            "vivere",
            "prendere",
            "credere",
            "chiedere",
            "vedere",
            "rivedere",
            "rispondere",
            "ricevere",
            "proteggere",
        ],
        "ire": [
            "aprire",
            "servire",
            "seguire",
            "dormire",
            "sentire",
            "capire",
            "finire",
            "offrire",
            "partire",
            "preferire",
            "pulire",
        ],
    }
    patterns = {
        "are": {
            "pres": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "o",
                    ("2", "sing"): "i",
                    ("3", "sing"): "a",
                    ("1", "plur"): "iamo",
                    ("2", "plur"): "ate",
                    ("3", "plur"): "ano",
                },
            },
            "fut": {
                "base": "lemma_drop_last",
                "endings": {
                    ("1", "sing"): "erò",
                    ("2", "sing"): "erai",
                    ("3", "sing"): "erà",
                    ("1", "plur"): "eremo",
                    ("2", "plur"): "erete",
                    ("3", "plur"): "eranno",
                },
            },
        },
        "ere": {
            "pres": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "o",
                    ("2", "sing"): "i",
                    ("3", "sing"): "e",
                    ("1", "plur"): "iamo",
                    ("2", "plur"): "ete",
                    ("3", "plur"): "ono",
                },
            },
            "fut": {
                "base": "lemma_drop_last",
                "endings": {
                    ("1", "sing"): "erò",
                    ("2", "sing"): "erai",
                    ("3", "sing"): "erà",
                    ("1", "plur"): "eremo",
                    ("2", "plur"): "erete",
                    ("3", "plur"): "eranno",
                },
            },
        },
        "ire": {
            "pres": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "o",
                    ("2", "sing"): "i",
                    ("3", "sing"): "e",
                    ("1", "plur"): "iamo",
                    ("2", "plur"): "ite",
                    ("3", "plur"): "ono",
                },
            },
            "fut": {
                "base": "lemma_drop_last",
                "endings": {
                    ("1", "sing"): "irò",
                    ("2", "sing"): "irai",
                    ("3", "sing"): "irà",
                    ("1", "plur"): "iremo",
                    ("2", "plur"): "irete",
                    ("3", "plur"): "iranno",
                },
            },
        },
    }
    return _build_romance_verbs(verbs, patterns)


def build_fr_verbs() -> Tuple[List[dict], List[dict], Dict[str, dict]]:
    verbs = {
        "er": [
            "parler",
            "aimer",
            "chercher",
            "regarder",
            "travailler",
            "étudier",
            "jouer",
            "chanter",
            "danser",
            "trouver",
            "penser",
            "espérer",
            "payer",
            "visiter",
            "parvenir",
        ],
        "ir": [
            "finir",
            "choisir",
            "réussir",
            "agir",
            "bâtir",
            "unir",
            "applaudir",
            "nourrir",
            "grandir",
            "obéir",
        ],
        "re": [
            "vendre",
            "attendre",
            "répondre",
            "entendre",
            "perdre",
            "défendre",
            "rendre",
            "fondre",
        ],
    }
    patterns = {
        "er": {
            "pres": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "e",
                    ("2", "sing"): "es",
                    ("3", "sing"): "e",
                    ("1", "plur"): "ons",
                    ("2", "plur"): "ez",
                    ("3", "plur"): "ent",
                },
            },
            "fut": {
                "base": "lemma",
                "endings": {
                    ("1", "sing"): "ai",
                    ("2", "sing"): "as",
                    ("3", "sing"): "a",
                    ("1", "plur"): "ons",
                    ("2", "plur"): "ez",
                    ("3", "plur"): "ont",
                },
            },
        },
        "ir": {
            "pres": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "is",
                    ("2", "sing"): "is",
                    ("3", "sing"): "it",
                    ("1", "plur"): "issons",
                    ("2", "plur"): "issez",
                    ("3", "plur"): "issent",
                },
            },
            "fut": {
                "base": "lemma",
                "endings": {
                    ("1", "sing"): "ai",
                    ("2", "sing"): "as",
                    ("3", "sing"): "a",
                    ("1", "plur"): "ons",
                    ("2", "plur"): "ez",
                    ("3", "plur"): "ont",
                },
            },
        },
        "re": {
            "pres": {
                "base": "root",
                "endings": {
                    ("1", "sing"): "s",
                    ("2", "sing"): "s",
                    ("3", "sing"): "",
                    ("1", "plur"): "ons",
                    ("2", "plur"): "ez",
                    ("3", "plur"): "ent",
                },
            },
            "fut": {
                "base": "lemma_drop_last",
                "endings": {
                    ("1", "sing"): "rai",
                    ("2", "sing"): "ras",
                    ("3", "sing"): "ra",
                    ("1", "plur"): "rons",
                    ("2", "plur"): "rez",
                    ("3", "plur"): "ront",
                },
            },
        },
    }
    return _build_romance_verbs(verbs, patterns)


def build_en_verbs() -> Tuple[List[dict], List[dict], Dict[str, dict]]:
    verbs = {
        "go": {"past": "went"},
        "come": {"past": "came"},
        "make": {"past": "made"},
        "do": {"past": "did"},
        "see": {"past": "saw"},
        "tell": {"past": "told"},
        "speak": {"past": "spoke"},
        "travel": {},
        "work": {},
        "study": {},
        "play": {},
        "watch": {},
        "drive": {"past": "drove"},
        "build": {"past": "built"},
        "write": {"past": "wrote"},
        "read": {"past": "read"},
        "ask": {},
        "answer": {},
        "learn": {},
        "teach": {"past": "taught"},
        "think": {"past": "thought"},
        "plan": {},
        "explain": {},
        "solve": {},
        "create": {},
        "support": {},
        "decide": {},
        "believe": {},
        "remember": {},
    }
    lexemes: List[dict] = []
    conjugations: List[dict] = []
    metadata: Dict[str, dict] = {}
    for lemma, special in verbs.items():
        lemma = lemma.lower()
        forms = {lemma.upper()}
        third = lemma + "s" if not lemma.endswith("s") else lemma + "es"
        past = special.get("past", lemma + "ed")
        prog = lemma + "ing"
        for person, number, form, tense in [
            ("1", "sing", lemma, "pres"),
            ("2", "sing", lemma, "pres"),
            ("3", "sing", third, "pres"),
            ("1", "plur", lemma, "pres"),
            ("2", "plur", lemma, "pres"),
            ("3", "plur", lemma, "pres"),
            ("1", "sing", past, "past"),
            ("2", "sing", past, "past"),
            ("3", "sing", past, "past"),
            ("1", "plur", past, "past"),
            ("2", "plur", past, "past"),
            ("3", "plur", past, "past"),
        ]:
            form_lower = form.lower()
            conjugations.append({"lemma": lemma, "tense": tense, "person": person, "number": number, "form": form_lower})
            metadata[form_lower.upper()] = {
                "lemma": lemma.upper(),
                "tense": tense,
                "person": person,
                "number": number,
            }
            forms.add(form_lower.upper())
        forms.add(prog.upper())
        metadata[prog.upper()] = {"lemma": lemma.upper(), "tense": "prog", "person": "-", "number": "-"}
        lexemes.append({"lemma": lemma.upper(), "semantics": "ACTION", "pos": "VERB", "forms": sorted(forms)})
    return lexemes, conjugations, metadata


PT_VERB_LEXEMES, PT_CONJUGATIONS, PT_VERB_METADATA = build_pt_verbs()
ES_VERB_LEXEMES, ES_CONJUGATIONS, ES_VERB_METADATA = build_es_verbs()
IT_VERB_LEXEMES, IT_CONJUGATIONS, IT_VERB_METADATA = build_it_verbs()
FR_VERB_LEXEMES, FR_CONJUGATIONS, FR_VERB_METADATA = build_fr_verbs()
EN_VERB_LEXEMES, EN_CONJUGATIONS, EN_VERB_METADATA = build_en_verbs()

VERB_METADATA_MAP = {
    "pt": PT_VERB_METADATA,
    "es": ES_VERB_METADATA,
    "it": IT_VERB_METADATA,
    "fr": FR_VERB_METADATA,
    "en": EN_VERB_METADATA,
}


__all__ = [
    "PT_VERB_LEXEMES",
    "PT_CONJUGATIONS",
    "ES_VERB_LEXEMES",
    "ES_CONJUGATIONS",
    "FR_VERB_LEXEMES",
    "FR_CONJUGATIONS",
    "IT_VERB_LEXEMES",
    "IT_CONJUGATIONS",
    "EN_VERB_LEXEMES",
    "EN_CONJUGATIONS",
    "VERB_METADATA_MAP",
]
