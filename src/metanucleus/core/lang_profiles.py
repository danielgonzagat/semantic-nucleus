"""Perfis multilíngues determinísticos para o Metanúcleo."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Dict, Iterable, List, Optional, Set

_WORD_RE = re.compile(r"[a-zA-ZÀ-ÖØ-öø-ÿ0-9_]+", re.UNICODE)


def _tokenize(text: str) -> List[str]:
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


@dataclass(frozen=True)
class LanguageProfile:
    code: str
    labels: Set[str]
    stopwords: Set[str]
    greetings: Set[str]
    question_markers: Set[str]
    yes_words: Set[str]
    no_words: Set[str]
    command_markers: Set[str]


@dataclass(frozen=True)
class LanguageGuess:
    code: str
    confidence: float
    scores: Dict[str, float]


class LanguageCode(str, Enum):
    PT = "pt"
    EN = "en"
    ES = "es"
    FR = "fr"
    IT = "it"
    DE = "de"
    UNKNOWN = "unknown"


PROFILES: Dict[str, LanguageProfile] = {}


def _build_profile(
    code: str,
    labels: Iterable[str],
    stopwords: Iterable[str],
    greetings: Iterable[str],
    question_markers: Iterable[str],
    yes_words: Iterable[str],
    no_words: Iterable[str],
    command_markers: Iterable[str],
) -> None:
    PROFILES[code] = LanguageProfile(
        code=code,
        labels={label.lower() for label in labels},
        stopwords={s.lower() for s in stopwords},
        greetings={g.lower() for g in greetings},
        question_markers={q.lower() for q in question_markers},
        yes_words={w.lower() for w in yes_words},
        no_words={w.lower() for w in no_words},
        command_markers={w.lower() for w in command_markers},
    )


_build_profile(
    "pt",
    ["pt", "pt-br", "português", "portugues", "portuguese"],
    [
        "o",
        "a",
        "os",
        "as",
        "um",
        "uma",
        "de",
        "do",
        "da",
        "das",
        "dos",
        "em",
        "no",
        "na",
        "nos",
        "nas",
        "por",
        "pra",
        "para",
        "com",
        "sem",
        "é",
        "ser",
        "estar",
        "foi",
        "era",
        "que",
        "se",
        "e",
        "ou",
        "mas",
        "eu",
        "tu",
        "você",
        "voce",
        "ele",
        "ela",
        "nós",
        "nos",
        "eles",
        "elas",
    ],
    ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"],
    ["?", "por que", "porque", "como", "quando", "onde", "quem", "qual", "quais"],
    ["sim", "claro", "com certeza", "aham"],
    ["não", "nao", "nunca", "jamais"],
    ["faça", "faz", "cria", "gera", "mostra", "executa", "roda", "abre", "fecha", "lista"],
)

_build_profile(
    "en",
    ["en", "english", "inglês", "ingles"],
    [
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "to",
        "of",
        "in",
        "on",
        "at",
        "for",
        "with",
        "without",
        "is",
        "are",
        "am",
        "was",
        "were",
        "be",
        "being",
        "been",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
    ],
    ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"],
    ["?", "why", "how", "when", "where", "who", "which"],
    ["yes", "yep", "yeah", "sure", "of course"],
    ["no", "nope", "never"],
    ["run", "execute", "do", "create", "make", "show", "list", "reset"],
)

_build_profile(
    "es",
    ["es", "español", "espanol", "spanish"],
    [
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "de",
        "del",
        "en",
        "por",
        "para",
        "con",
        "sin",
        "y",
        "o",
        "pero",
        "que",
        "se",
        "soy",
        "eres",
        "es",
        "somos",
        "son",
        "yo",
        "tú",
        "tu",
        "usted",
        "nosotros",
        "ellos",
        "ellas",
    ],
    ["hola", "buenos dias", "buenas tardes", "buenas noches"],
    ["?", "por qué", "porque", "como", "cuando", "donde", "quien", "qué"],
    ["sí", "si", "claro", "por supuesto"],
    ["no", "nunca", "jamás", "jamas"],
    ["haz", "hacer", "ejecuta", "lista", "muestra"],
)

_build_profile(
    "fr",
    ["fr", "français", "francais", "french"],
    [
        "le",
        "la",
        "les",
        "un",
        "une",
        "des",
        "de",
        "du",
        "en",
        "dans",
        "pour",
        "avec",
        "sans",
        "et",
        "ou",
        "mais",
        "que",
        "je",
        "tu",
        "il",
        "elle",
        "nous",
        "vous",
        "ils",
        "elles",
    ],
    ["salut", "bonjour", "bonsoir"],
    ["?", "pourquoi", "comment", "quand", "où", "ou", "qui", "quel"],
    ["oui", "bien sûr"],
    ["non", "jamais"],
    ["fais", "faire", "montre", "liste"],
)

_build_profile(
    "it",
    ["it", "italiano", "italian"],
    [
        "il",
        "lo",
        "la",
        "i",
        "gli",
        "le",
        "un",
        "una",
        "di",
        "del",
        "della",
        "in",
        "su",
        "per",
        "con",
        "senza",
        "e",
        "o",
        "ma",
        "che",
        "io",
        "tu",
        "lui",
        "lei",
        "noi",
        "voi",
        "loro",
    ],
    ["ciao", "buongiorno", "buonasera"],
    ["?", "perché", "perche", "come", "quando", "dove", "chi"],
    ["sì", "si", "certo"],
    ["no", "mai"],
    ["esegui", "fai", "crea", "mostra", "lista"],
)

_build_profile(
    "de",
    ["de", "deutsch", "german"],
    [
        "der",
        "die",
        "das",
        "ein",
        "eine",
        "von",
        "zu",
        "in",
        "auf",
        "mit",
        "ohne",
        "für",
        "und",
        "oder",
        "aber",
        "dass",
        "ich",
        "du",
        "er",
        "sie",
        "es",
        "wir",
        "ihr",
        "sie",
    ],
    ["hallo", "guten tag", "guten morgen", "guten abend"],
    ["?", "warum", "wie", "wann", "wo", "wer"],
    ["ja", "doch"],
    ["nein", "niemals"],
    ["mach", "ausführen", "liste", "zeige"],
)


def detect_language(text: str) -> LanguageGuess:
    tokens = _tokenize(text)
    if not tokens:
        return LanguageGuess(code=LanguageCode.UNKNOWN.value, confidence=0.0, scores={})

    lowered_full = text.lower()
    if "¿" in text or "¡" in text:
        return LanguageGuess(code="es", confidence=1.0, scores={"es": 1.0})
    if any(ch in lowered_full for ch in "ãõáéíóúâêôç"):
        # forte indicativo de PT
        return LanguageGuess(code="pt", confidence=0.9, scores={"pt": 1.0})

    scores: Dict[str, float] = {}
    lowered = " ".join(tokens)
    for code, profile in PROFILES.items():
        score = 0.0
        for token in tokens:
            if token in profile.stopwords:
                score += 1.0
        for greet in profile.greetings:
            if greet in lowered:
                score += 2.5
        for qm in profile.question_markers:
            if qm in lowered:
                score += 1.5
        scores[code] = score

    best_code, best_score = max(scores.items(), key=lambda item: item[1])
    confidence = 0.0 if best_score <= 0 else best_score / (best_score + 5.0)
    return LanguageGuess(code=best_code if best_score > 0 else LanguageCode.UNKNOWN.value, confidence=confidence, scores=scores)


def normalize_for_language(text: str, lang_code: Optional[str] = None) -> List[str]:
    tokens = _tokenize(text)
    if not tokens:
        return []
    code = lang_code or detect_language(text).code
    profile = PROFILES.get(code)
    if profile is None:
        return tokens
    return [tok for tok in tokens if tok not in profile.stopwords]


@dataclass(frozen=True)
class LanguageFeatures:
    lang: str
    confidence: float
    tokens: List[str]
    has_question_mark: bool
    is_greeting_like: bool
    is_yes_like: bool
    is_no_like: bool
    raw_scores: Dict[str, float]


def extract_language_features(text: str) -> LanguageFeatures:
    guess = detect_language(text)
    profile = PROFILES.get(guess.code)
    tokens = normalize_for_language(text, guess.code)
    joined = " ".join(tokens)

    def contains(words: Iterable[str]) -> bool:
        for word in words:
            if word in joined:
                return True
        return False

    has_q = "?" in text
    is_greeting = contains(profile.greetings) if profile else False
    is_yes = contains(profile.yes_words) if profile else False
    is_no = contains(profile.no_words) if profile else False

    return LanguageFeatures(
        lang=guess.code,
        confidence=guess.confidence,
        tokens=tokens,
        has_question_mark=has_q,
        is_greeting_like=is_greeting,
        is_yes_like=is_yes,
        is_no_like=is_no,
        raw_scores=guess.scores,
    )


__all__ = [
    "LanguageProfile",
    "LanguageGuess",
    "LanguageFeatures",
    "LanguageCode",
    "extract_language_features",
    "normalize_for_language",
    "detect_language",
]
