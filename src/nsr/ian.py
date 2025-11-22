"""
Instinto Alfabético Numérico (IAN-Ω) – camada linguística determinística.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Dict, List, Mapping, Sequence, Tuple

from .langpacks import iter_language_packs

# ---------------------------------------------------------------------------
# Alfabeto ↔ código (nascimento alfabetizado)
# ---------------------------------------------------------------------------


def _base_charset() -> Tuple[str, ...]:
    letters = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    accented = (
        "Á",
        "Â",
        "Ã",
        "À",
        "É",
        "Ê",
        "È",
        "Í",
        "Ì",
        "Ó",
        "Ô",
        "Õ",
        "Ò",
        "Ú",
        "Ù",
        "Ç",
    )
    digits = tuple("0123456789")
    punct = (" ", ",", ".", "?", "!", ";", ":")
    return letters + accented + digits + punct


def _build_char_tables(sequence: Sequence[str]) -> Tuple[Dict[str, int], Dict[int, str]]:
    char_to_code: Dict[str, int] = {}
    code_to_char: Dict[int, str] = {}
    for idx, char in enumerate(sequence, start=1):
        if char in char_to_code:
            raise ValueError(f"Duplicate character '{char}' in base charset.")
        char_to_code[char] = idx
        code_to_char[idx] = char
    return char_to_code, code_to_char


CHAR_TO_CODE, CODE_TO_CHAR = _build_char_tables(_base_charset())


CONJUGATION_TABLE: Dict[Tuple[str, str, str, str], str] = {
    ("estar", "pres", "1", "sing"): "estou",
    ("estar", "pres", "2", "sing"): "está",
    ("estar", "pres", "3", "sing"): "está",
    ("estar", "pres", "1", "plur"): "estamos",
    ("estar", "pres", "2", "plur"): "estão",
    ("estar", "pres", "3", "plur"): "estão",
    ("ser", "pres", "1", "sing"): "sou",
    ("ser", "pres", "2", "sing"): "é",
    ("ser", "pres", "3", "sing"): "é",
    ("ser", "pres", "1", "plur"): "somos",
    ("ser", "pres", "2", "plur"): "são",
    ("ser", "pres", "3", "plur"): "são",
    ("falar", "pres", "1", "sing"): "falo",
    ("falar", "pres", "2", "sing"): "fala",
    ("falar", "pres", "3", "sing"): "fala",
    ("falar", "pres", "1", "plur"): "falamos",
    ("falar", "pres", "2", "plur"): "falam",
    ("falar", "pres", "3", "plur"): "falam",
}

DEFAULT_LANGUAGE_CODES: Tuple[str, ...] = ("pt", "en", "es", "fr", "it")


def encode_word(word: str, table: Mapping[str, int] | None = None) -> Tuple[int, ...]:
    """
    Converte uma palavra (string) em uma sequência determinística de códigos inteiros.
    """

    table = table or CHAR_TO_CODE
    normalized = _normalize(word, table)
    codes: List[int] = []
    for char in normalized:
        codes.append(table[char])
    return tuple(codes)


def encode_text(text: str, table: Mapping[str, int] | None = None) -> Tuple[int, ...]:
    """
    Codifica uma frase inteira em uma sequência numérica única.
    """

    table = table or CHAR_TO_CODE
    codes: List[int] = []
    for ch in text:
        normalized = _normalize_char(ch, table)
        if normalized is None:
            continue
        codes.append(table[normalized])
    return tuple(codes)


def decode_codes(codes: Sequence[int], table: Mapping[int, str] | None = None) -> str:
    """
    Decodifica uma sequência numérica para texto (sempre em maiúsculas).
    """

    table = table or CODE_TO_CHAR
    chars = []
    for code in codes:
        if code not in table:
            raise ValueError(f"Code '{code}' is not defined in the IAN table.")
        chars.append(table[code])
    return "".join(chars)


def word_signature(word: str, base: int = 257, table: Mapping[str, int] | None = None) -> int:
    """
    Reduz uma palavra a um único inteiro, preservando ordem dos símbolos (Gödel-like).
    """

    codes = encode_word(word, table=table)
    acc = 0
    for code in codes:
        acc = acc * base + code
    return acc


def _normalize(text: str, table: Mapping[str, int] | None = None) -> str:
    normalized_chars: List[str] = []
    for ch in text:
        normalized = _normalize_char(ch, table)
        if normalized is None:
            raise ValueError(f"Character '{ch}' is not representable in the IAN table.")
        normalized_chars.append(normalized)
    return "".join(normalized_chars)


def _normalize_char(char: str, table: Mapping[str, int] | None = None) -> str | None:
    table = table or CHAR_TO_CODE
    if not char:
        return None
    upper = char.upper()
    return upper if upper in table else None


def conjugate(lemma: str, tense: str = "pres", person: int = 1, number: str = "sing") -> str:
    key = (lemma.lower(), tense.lower(), str(person), number.lower())
    if key not in CONJUGATION_TABLE:
        raise ValueError(f"Conjugation not defined for {key}")
    return CONJUGATION_TABLE[key]


def _register_conjugations(entries) -> None:
    for entry in entries:
        key = (entry.lemma.lower(), entry.tense.lower(), str(entry.person), entry.number.lower())
        CONJUGATION_TABLE.setdefault(key, entry.form)


# ---------------------------------------------------------------------------
# Léxico inato + estrutura de tokens
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Lexeme:
    lemma: str
    semantics: str
    pos: str
    forms: Tuple[str, ...]

    def matches(self, candidate: str) -> bool:
        return candidate in self.forms


def _normalize_forms(forms: Sequence[str]) -> Tuple[str, ...]:
    return tuple(form.upper() for form in forms)


@dataclass(frozen=True)
class IANToken:
    surface: str
    normalized: str
    codes: Tuple[int, ...]
    lexeme: Lexeme | None
    is_punctuation: bool = False


@dataclass(frozen=True)
class Utterance:
    role: str
    semantics: str
    language: str
    tokens: Tuple[IANToken, ...]


@dataclass(frozen=True)
class ReplyPlan:
    role: str
    semantics: str
    tokens: Tuple[str, ...]
    token_codes: Tuple[Tuple[int, ...], ...]
    language: str


@dataclass(frozen=True)
class DialogRule:
    trigger_role: str
    reply_role: str
    reply_semantics: str
    surface_tokens: Tuple[str, ...]
    reply_language: str = "und"

    def matches(self, utterance: Utterance) -> bool:
        return utterance.role == self.trigger_role


TOKEN_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+|[!?.,]")
EN_GREETING_SURFACES = frozenset({"HI", "HELLO", "HEY"})
ES_GREETING_SURFACES = frozenset({"HOLA"})
FR_GREETING_SURFACES = frozenset({"BONJOUR", "SALUT"})
IT_GREETING_SURFACES = frozenset({"CIAO"})
PT_VERBOSE_SEQUENCE = ("QUESTION_HOW", "YOU", "BE_STATE")
EN_VERBOSE_SEQUENCE = ("QUESTION_HOW", "BE_STATE", "YOU")
ES_VERBOSE_SEQUENCE_SHORT = ("QUESTION_HOW", "BE_STATE")
ES_VERBOSE_SEQUENCE_LONG = ("QUESTION_HOW", "BE_STATE", "YOU")
IT_VERBOSE_SEQUENCE_SHORT = ("QUESTION_HOW", "BE_STATE")
IT_VERBOSE_SEQUENCE_LONG = ("QUESTION_HOW", "YOU", "BE_STATE")
FR_VERBOSE_KEYWORDS = frozenset({"COMMENT", "ÇA", "CA"})


@dataclass
class IANInstinct:
    char_to_code: Mapping[str, int] = field(default_factory=lambda: CHAR_TO_CODE)
    code_to_char: Mapping[int, str] = field(default_factory=lambda: CODE_TO_CHAR)
    lexicon: Tuple[Lexeme, ...] = field(default_factory=tuple)
    dialog_rules: Tuple[DialogRule, ...] = field(default_factory=tuple)
    unknown_reply: Tuple[str, ...] = ("não", "sei", ".")

    def __post_init__(self) -> None:
        self._lexeme_index: Dict[str, Lexeme] = {}
        for lex in self.lexicon:
            for form in lex.forms:
                self._lexeme_index[form.upper()] = lex

    # ------------------------------------------------------------------
    # Pipeline principal
    # ------------------------------------------------------------------

    def tokenize(self, text: str) -> Tuple[IANToken, ...]:
        tokens: List[IANToken] = []
        for raw in TOKEN_PATTERN.findall(text):
            is_punct = raw in ",.?!"
            normalized = raw.upper()
            codes = encode_word(raw, self.char_to_code)
            lexeme = self._lexeme_index.get(normalized)
            tokens.append(
                IANToken(
                    surface=raw,
                    normalized=normalized,
                    codes=codes,
                    lexeme=lexeme,
                    is_punctuation=is_punct,
                )
            )
        return tuple(tokens)

    def analyze(self, text: str) -> Utterance:
        tokens = self.tokenize(text)
        role, semantics = self._infer_role(tokens)
        language = self._infer_language(role, tokens)
        return Utterance(role=role, semantics=semantics, language=language, tokens=tokens)

    def reply(self, text: str) -> ReplyPlan:
        utterance = self.analyze(text)
        plan = self.plan_reply(utterance)
        return plan

    def plan_reply(self, utterance: Utterance) -> ReplyPlan:
        for rule in self.dialog_rules:
            if rule.matches(utterance):
                materialized = self._materialize_rule_tokens(rule)
                codes = tuple(self._encode_token_surface(token) for token in materialized)
                return ReplyPlan(
                    role=rule.reply_role,
                    semantics=rule.reply_semantics,
                    tokens=materialized,
                    token_codes=codes,
                    language=rule.reply_language,
                )
        codes = tuple(self._encode_token_surface(token) for token in self.unknown_reply)
        return ReplyPlan(
            role="FALLBACK",
            semantics="UNKNOWN",
            tokens=self.unknown_reply,
            token_codes=codes,
            language=utterance.language or "und",
        )

    def render(self, plan: ReplyPlan) -> str:
        return _render_tokens(plan.tokens)

    def process(self, text: str) -> str:
        return self.render(self.reply(text))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _encode_token_surface(self, token: str) -> Tuple[int, ...]:
        return encode_word(token, self.char_to_code)

    def _infer_role(self, tokens: Sequence[IANToken]) -> Tuple[str, str]:
        content_tokens = tuple(token for token in tokens if not token.is_punctuation)
        semantics_seq = [t.lexeme.semantics if t.lexeme else None for t in content_tokens]
        verbose_role = self._matches_verbose_health_question(tokens, semantics_seq)
        if verbose_role:
            return verbose_role, "STATE_QUERY"
        health_role = self._health_question_role(content_tokens, semantics_seq)
        if health_role:
            return health_role, "STATE_QUERY"
        if self._contains_greeting(semantics_seq):
            return self._greeting_role(content_tokens), "GREETING_SIMPLE"
        state_role = self._detect_state_statement(tokens)
        if state_role == "POSITIVE":
            return "STATE_POSITIVE", "STATE_POSITIVE"
        if state_role == "NEGATIVE":
            return "STATE_NEGATIVE", "STATE_NEGATIVE"
        return "UNKNOWN", "UNKNOWN"

    def _infer_language(self, role: str, tokens: Sequence[IANToken]) -> str:
        lang = self._language_from_role(role)
        if lang != "und":
            return lang
        if self._is_english_greeting(tokens):
            return "en"
        if self._is_spanish_greeting(tokens):
            return "es"
        return "pt"

    @staticmethod
    def _language_from_role(role: str) -> str:
        if role.endswith("_EN") or "_EN_" in role:
            return "en"
        if role.endswith("_ES") or "_ES_" in role:
            return "es"
        if role.endswith("_FR") or "_FR_" in role:
            return "fr"
        if role.endswith("_IT") or "_IT_" in role:
            return "it"
        if role.endswith("_PT") or "_PT_" in role:
            return "pt"
        if role in {"GREETING_SIMPLE", "QUESTION_HEALTH", "QUESTION_HEALTH_VERBOSE", "STATE_POSITIVE", "STATE_NEGATIVE"}:
            return "pt"
        return "und"

    @staticmethod
    def _contains_greeting(semantics_seq: Sequence[str | None]) -> bool:
        return any(item == "GREETING_SIMPLE" for item in semantics_seq)

    def _matches_verbose_health_question(
        self, tokens: Sequence[IANToken], semantics_seq: Sequence[str | None]
    ) -> str | None:
        filtered = [sem for sem in semantics_seq if sem and sem != "GREETING_SIMPLE"]
        has_question_mark = any(token.surface == "?" for token in tokens)
        if not has_question_mark or len(filtered) < 2:
            return None
        head = tuple(filtered[:3])
        if head == PT_VERBOSE_SEQUENCE:
            if self._contains_french_verbose_marker(tokens):
                return "QUESTION_HEALTH_VERBOSE_FR"
            return "QUESTION_HEALTH_VERBOSE"
        if head == EN_VERBOSE_SEQUENCE:
            return "QUESTION_HEALTH_VERBOSE_EN"
        if head[:2] == ES_VERBOSE_SEQUENCE_SHORT or head == ES_VERBOSE_SEQUENCE_LONG:
            first_surface = self._first_surface_with_semantics(tokens, "QUESTION_HOW")
            if first_surface == "COME":
                return "QUESTION_HEALTH_VERBOSE_IT"
            return "QUESTION_HEALTH_VERBOSE_ES"
        if head[:2] == IT_VERBOSE_SEQUENCE_SHORT or head == IT_VERBOSE_SEQUENCE_LONG:
            return "QUESTION_HEALTH_VERBOSE_IT"
        return None

    @staticmethod
    def _is_english_greeting(tokens: Sequence[IANToken]) -> bool:
        return any((not token.is_punctuation) and token.normalized in EN_GREETING_SURFACES for token in tokens)

    @staticmethod
    def _is_spanish_greeting(tokens: Sequence[IANToken]) -> bool:
        return any((not token.is_punctuation) and token.normalized in ES_GREETING_SURFACES for token in tokens)

    @staticmethod
    def _is_french_greeting(tokens: Sequence[IANToken]) -> bool:
        return any((not token.is_punctuation) and token.normalized in FR_GREETING_SURFACES for token in tokens)

    @staticmethod
    def _is_italian_greeting(tokens: Sequence[IANToken]) -> bool:
        return any((not token.is_punctuation) and token.normalized in IT_GREETING_SURFACES for token in tokens)

    @staticmethod
    def _contains_french_verbose_marker(tokens: Sequence[IANToken]) -> bool:
        return any((not token.is_punctuation) and token.normalized in FR_VERBOSE_KEYWORDS for token in tokens)

    def _greeting_role(self, tokens: Sequence[IANToken]) -> str:
        if self._is_english_greeting(tokens):
            return "GREETING_SIMPLE_EN"
        if self._is_spanish_greeting(tokens):
            return "GREETING_SIMPLE_ES"
        if self._is_french_greeting(tokens):
            return "GREETING_SIMPLE_FR"
        if self._is_italian_greeting(tokens):
            return "GREETING_SIMPLE_IT"
        return "GREETING_SIMPLE"

    def _health_question_role(
        self, tokens: Sequence[IANToken], semantics_seq: Sequence[str | None]
    ) -> str | None:
        for idx, semantic in enumerate(semantics_seq):
            if semantic != "ALL_THINGS":
                continue
            next_idx = self._next_semantic_index(semantics_seq, idx + 1)
            if next_idx is None:
                continue
            if semantics_seq[next_idx] != "STATE_GOOD":
                continue
            first_surface = tokens[idx].normalized
            second_surface = tokens[next_idx].normalized
            if first_surface.startswith("TODO"):
                return "QUESTION_HEALTH_ES"
            if first_surface == "TOUT":
                return "QUESTION_HEALTH_FR"
            if first_surface == "TUTTO":
                return "QUESTION_HEALTH_IT"
            return "QUESTION_HEALTH"
        return None

    @staticmethod
    def _next_semantic_index(semantics_seq: Sequence[str | None], start: int) -> int | None:
        for idx in range(start, len(semantics_seq)):
            semantic = semantics_seq[idx]
            if semantic is None or semantic == "BE_STATE":
                continue
            return idx
        return None

    @staticmethod
    def _detect_state_statement(tokens: Sequence[IANToken]) -> str | None:
        semantics = [t.lexeme.semantics if t.lexeme else None for t in tokens]
        if any(sem == "STATE_BAD" for sem in semantics):
            return "NEGATIVE"
        if any(sem == "NEGATE" for sem in semantics) and any(sem == "STATE_GOOD" for sem in semantics):
            return "NEGATIVE"
        if any(sem == "STATE_GOOD" for sem in semantics):
            has_self = any((t.lexeme and t.lexeme.semantics in {"SELF", "BE_STATE"}) for t in tokens)
            if has_self:
                return "POSITIVE"
        return None

    @staticmethod
    def _first_surface_with_semantics(tokens: Sequence[IANToken], semantics: str) -> str | None:
        for token in tokens:
            if token.lexeme and token.lexeme.semantics == semantics:
                return token.normalized
        return None

    def _materialize_rule_tokens(self, rule: DialogRule) -> Tuple[str, ...]:
        resolved: List[str] = []
        for token in rule.surface_tokens:
            if token.startswith(":CONJ:"):
                parts = token.split(":")
                if len(parts) != 6 or parts[1].upper() != "CONJ":
                    raise ValueError(f"Malformed conjugation token '{token}'")
                _, _, lemma, tense, person, number = parts
                resolved.append(conjugate(lemma, tense, int(person), number))
            else:
                resolved.append(token)
        return tuple(resolved)

    # ------------------------------------------------------------------
    # Fábrica de instinto padrão
    # ------------------------------------------------------------------

    @classmethod
    def default(cls) -> "IANInstinct":
        packs = iter_language_packs(DEFAULT_LANGUAGE_CODES)
        lexicon_entries = []
        dialog_entries = []
        for pack in packs:
            lexicon_entries.extend(
                Lexeme(
                    lemma=spec.lemma.upper(),
                    semantics=spec.semantics,
                    pos=spec.pos,
                    forms=_normalize_forms(spec.forms),
                )
                for spec in pack.lexemes
            )
            dialog_entries.extend(
                DialogRule(
                    trigger_role=spec.trigger_role,
                    reply_role=spec.reply_role,
                    reply_semantics=spec.reply_semantics,
                    surface_tokens=spec.surface_tokens,
                    reply_language=spec.language,
                )
                for spec in pack.dialog_rules
            )
            _register_conjugations(pack.conjugations)
        lexicon = tuple(lexicon_entries)
        dialog_rules = tuple(dialog_entries)
        return cls(
            char_to_code=CHAR_TO_CODE,
            code_to_char=CODE_TO_CHAR,
            lexicon=lexicon,
            dialog_rules=dialog_rules,
            unknown_reply=("não", "sei", "."),
        )


DEFAULT_INSTINCT = IANInstinct.default()


def analyze_utterance(text: str, instinct: IANInstinct | None = None) -> Utterance:
    instinct = instinct or DEFAULT_INSTINCT
    return instinct.analyze(text)


def plan_reply(text: str, instinct: IANInstinct | None = None) -> ReplyPlan:
    instinct = instinct or DEFAULT_INSTINCT
    return instinct.reply(text)


def respond(text: str, instinct: IANInstinct | None = None) -> str:
    instinct = instinct or DEFAULT_INSTINCT
    return instinct.process(text)


def _render_tokens(tokens: Sequence[str]) -> str:
    result = ""
    for token in tokens:
        if token in ",.?!;:":
            result = result.rstrip() + token
        else:
            if result and not result.endswith((" ", "\n")) and result[-1] not in ",.?!;:":
                result += " "
            elif result and result[-1] in ",.?!;:":
                result += " "
            result += token
    return result.strip()


__all__ = [
    "IANInstinct",
    "Lexeme",
    "DialogRule",
    "Utterance",
    "ReplyPlan",
    "DEFAULT_INSTINCT",
    "encode_word",
    "encode_text",
    "decode_codes",
    "word_signature",
    "conjugate",
    "analyze_utterance",
    "plan_reply",
    "respond",
]
