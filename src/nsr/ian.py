"""
Instinto Alfabético Numérico (IAN-Ω) – camada linguística determinística.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Dict, List, Mapping, Sequence, Tuple

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
        "Í",
        "Ó",
        "Ô",
        "Õ",
        "Ú",
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
    tokens: Tuple[IANToken, ...]


@dataclass(frozen=True)
class ReplyPlan:
    role: str
    semantics: str
    tokens: Tuple[str, ...]
    token_codes: Tuple[Tuple[int, ...], ...]


@dataclass(frozen=True)
class DialogRule:
    trigger_role: str
    reply_role: str
    reply_semantics: str
    surface_tokens: Tuple[str, ...]

    def matches(self, utterance: Utterance) -> bool:
        return utterance.role == self.trigger_role


TOKEN_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+|[!?.,]")


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
        return Utterance(role=role, semantics=semantics, tokens=tokens)

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
                )
        codes = tuple(self._encode_token_surface(token) for token in self.unknown_reply)
        return ReplyPlan(
            role="FALLBACK",
            semantics="UNKNOWN",
            tokens=self.unknown_reply,
            token_codes=codes,
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
        semantics_seq = [t.lexeme.semantics if t.lexeme else None for t in tokens if not t.is_punctuation]
        if self._matches_verbose_health_question(tokens, semantics_seq):
            return "QUESTION_HEALTH_VERBOSE", "STATE_QUERY"
        if self._contains_greeting(semantics_seq):
            # if a health question is also present, prefer the more specific intent
            if self._contains_health_question(tokens, semantics_seq):
                return "QUESTION_HEALTH", "STATE_QUERY"
            return "GREETING_SIMPLE", "GREETING_SIMPLE"
        if self._contains_health_question(tokens, semantics_seq):
            return "QUESTION_HEALTH", "STATE_QUERY"
        state_role = self._detect_state_statement(tokens)
        if state_role == "POSITIVE":
            return "STATE_POSITIVE", "STATE_POSITIVE"
        if state_role == "NEGATIVE":
            return "STATE_NEGATIVE", "STATE_NEGATIVE"
        return "UNKNOWN", "UNKNOWN"

    @staticmethod
    def _contains_greeting(semantics_seq: Sequence[str | None]) -> bool:
        return any(item == "GREETING_SIMPLE" for item in semantics_seq)

    @staticmethod
    def _contains_health_question(tokens: Sequence[IANToken], semantics_seq: Sequence[str | None]) -> bool:
        for idx in range(len(semantics_seq) - 1):
            if semantics_seq[idx] == "ALL_THINGS" and semantics_seq[idx + 1] == "STATE_GOOD":
                has_question_mark = any(tok.surface == "?" for tok in tokens)
                return has_question_mark or True
        return False

    @staticmethod
    def _matches_verbose_health_question(tokens: Sequence[IANToken], semantics_seq: Sequence[str | None]) -> bool:
        filtered = [sem for sem in semantics_seq if sem]
        pattern = ("QUESTION_HOW", "YOU", "BE_STATE")
        return tuple(filtered[:3]) == pattern and any(tok.surface == "?" for tok in tokens)

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
        lexicon = (
            Lexeme(lemma="OI", semantics="GREETING_SIMPLE", pos="INTERJ", forms=("OI", "OLÁ", "OLA")),
            Lexeme(lemma="TUDO", semantics="ALL_THINGS", pos="PRON_INDEF", forms=("TUDO",)),
            Lexeme(lemma="BEM", semantics="STATE_GOOD", pos="ADV", forms=("BEM",)),
            Lexeme(lemma="E", semantics="CONJ_AND", pos="CONJ", forms=("E",)),
            Lexeme(lemma="VOCÊ", semantics="YOU", pos="PRON", forms=("VOCÊ", "VOCE")),
            Lexeme(lemma="EU", semantics="SELF", pos="PRON", forms=("EU",)),
            Lexeme(lemma="SIM", semantics="AFFIRM", pos="ADV", forms=("SIM",)),
            Lexeme(lemma="NÃO", semantics="NEGATE", pos="ADV", forms=("NÃO", "NAO")),
            Lexeme(lemma="COMO", semantics="QUESTION_HOW", pos="ADV", forms=("COMO",)),
            Lexeme(lemma="ESTAR", semantics="BE_STATE", pos="VERB", forms=("ESTÁ", "ESTA", "ESTOU", "ESTAS")),
            Lexeme(lemma="MAL", semantics="STATE_BAD", pos="ADV", forms=("MAL",)),
            Lexeme(lemma="RUIM", semantics="STATE_BAD", pos="ADJ", forms=("RUIM",)),
            Lexeme(lemma="TRISTE", semantics="STATE_BAD", pos="ADJ", forms=("TRISTE",)),
        )
        dialog_rules = (
            DialogRule(
                trigger_role="QUESTION_HEALTH",
                reply_role="ANSWER_HEALTH_AND_RETURN",
                reply_semantics="STATE_GOOD_AND_RETURN",
                surface_tokens=("tudo", "bem", ",", "e", "você", "?"),
            ),
            DialogRule(
                trigger_role="GREETING_SIMPLE",
                reply_role="GREETING_SIMPLE_REPLY",
                reply_semantics="GREETING_SIMPLE",
                surface_tokens=("oi",),
            ),
            DialogRule(
                trigger_role="QUESTION_HEALTH_VERBOSE",
                reply_role="ANSWER_HEALTH_VERBOSE",
                reply_semantics="STATE_GOOD_AND_RETURN",
                surface_tokens=(":CONJ:estar:pres:1:sing", "bem", ",", "e", "você", "?"),
            ),
            DialogRule(
                trigger_role="STATE_POSITIVE",
                reply_role="ACK_POSITIVE",
                reply_semantics="STATE_POSITIVE_ACK",
                surface_tokens=("que", "bom", "!"),
            ),
            DialogRule(
                trigger_role="STATE_NEGATIVE",
                reply_role="CARE_NEGATIVE",
                reply_semantics="STATE_NEGATIVE_SUPPORT",
                surface_tokens=("sinto", "muito", ".", "posso", "ajudar", "?"),
            ),
        )
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
