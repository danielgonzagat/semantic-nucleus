"""
Parser Semântico Estrutural (PSE).
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from liu import Node, boolean, entity, list_node, relation, struct, text

from .grammar import GrammarProfile, PronounInfo, get_grammar_profile
from .langpacks import VERB_METADATA
from .state import Token


def build_struct(tokens: List[Token], *, language: str | None = "pt", text_input: str | None = None) -> Node:
    """
    Constrói uma estrutura LIU determinística a partir dos tokens do LxU.

    Parameters
    ----------
    tokens:
        Sequência normalizada de tokens produzidos por `tokenize`.
    language:
        Código ISO (pt, en, es, fr, it) usado para aplicar regras morfossintáticas.
    text_input:
        Texto original, usado para heurísticas (pergunta, imperativo).
    """

    analyzer = _ClauseAnalyzer(tokens, language or "pt", text_input or "")
    return analyzer.to_struct()


class _ClauseAnalyzer:
    def __init__(self, tokens: List[Token], language: str, text_input: str) -> None:
        self.tokens = tokens
        self.language = language.lower()
        self.profile: GrammarProfile = get_grammar_profile(self.language)
        self.text_input = text_input or ""
        self.lower_text = self.text_input.strip().lower()
        self.verb_index, self.verb_token = self._find_primary_verb()
        self.relations = self._collect_relations()
        self.negation_markers = self._collect_negations()
        self.modifiers = self._collect_modifiers()
        self.question_focus = self._detect_question_focus()
        self.sentence_type = self._detect_sentence_type()

    def to_struct(self) -> Node:
        subject = self._find_subject()
        obj = self._find_object()
        action = self._build_action()

        fields: dict[str, Node] = {}
        if action is not None:
            fields["action"] = action
        if obj is not None:
            fields["object"] = obj
        if subject is not None:
            fields["subject"] = subject
        if self.modifiers:
            fields["modifier"] = list_node(self.modifiers)
        if self.relations:
            fields["relations"] = list_node(self.relations)
        if self.negation_markers:
            fields["negation"] = list_node([entity(marker) for marker in self.negation_markers])
        if self.question_focus is not None:
            fields["question_focus"] = self.question_focus
        fields["sentence_type"] = entity(self.sentence_type)
        fields["language"] = entity(self.language)
        return struct(**fields)

    # region token collectors -------------------------------------------------
    def _collect_relations(self) -> List[Node]:
        rel_nodes: List[Node] = []
        for idx, token in enumerate(self.tokens):
            if token.tag != "RELWORD":
                continue
            rel_node = _build_relation(self.tokens, idx, token.payload)
            if rel_node is not None:
                rel_nodes.append(rel_node)
        return rel_nodes

    def _collect_negations(self) -> List[str]:
        markers: List[str] = []
        for token in self.tokens:
            lemma = token.lemma.lower()
            if lemma in self.profile.negations:
                markers.append(lemma)
        return markers

    def _collect_modifiers(self) -> List[Node]:
        modifiers: List[Node] = []
        for token in self.tokens:
            if token.tag == "QUALIFIER":
                modifiers.append(entity(token.lemma))
        return modifiers

    def _detect_question_focus(self) -> Node | None:
        for token in self.tokens:
            lemma = token.lemma.lower()
            if lemma in self.profile.question_words:
                return entity(lemma)
        return None

    def _detect_sentence_type(self) -> str:
        if self.lower_text.endswith("?") or self.question_focus is not None:
            return "question"
        if self.lower_text.endswith("!") or self._looks_like_command():
            return "command"
        return "statement"

    def _looks_like_command(self) -> bool:
        if self.verb_index == 0:
            return True
        return any(self.lower_text.startswith(marker) for marker in self.profile.imperative_markers)

    # endregion ----------------------------------------------------------------

    # region syntactic roles ---------------------------------------------------
    def _find_primary_verb(self) -> tuple[Optional[int], Optional[Token]]:
        fallback: tuple[Optional[int], Optional[Token]] = (None, None)
        for idx, token in enumerate(self.tokens):
            if token.tag != "ACTION":
                continue
            lemma = (token.lemma or "").lower()
            if fallback[0] is None:
                fallback = (idx, token)
            if lemma not in self.profile.auxiliaries:
                return idx, token
        return fallback

    def _find_subject(self) -> Node | None:
        if not self.tokens:
            return None
        if self.verb_index is not None:
            indices: Iterable[int] = range(self.verb_index - 1, -1, -1)
        else:
            indices = range(len(self.tokens) - 1, -1, -1)
        pron = self._scan_pronouns(indices, {"subject", "both"})
        if pron is not None:
            return pron
        for idx in indices:
            token = self.tokens[idx]
            if token.tag == "ENTITY":
                return entity(token.lemma)
        # fallback: first entity anywhere
        for token in self.tokens:
            if token.tag == "ENTITY":
                return entity(token.lemma)
        return None

    def _find_object(self) -> Node | None:
        if not self.tokens:
            return None
        start = self.verb_index + 1 if self.verb_index is not None else 0
        indices: Iterable[int] = range(start, len(self.tokens))
        pron = self._scan_pronouns(indices, {"object", "both"})
        if pron is not None:
            return pron
        for idx in indices:
            token = self.tokens[idx]
            if token.tag == "ENTITY":
                return entity(token.lemma)
        return None

    def _scan_pronouns(self, indices: Iterable[int], allowed_roles: set[str]) -> Node | None:
        for idx in indices:
            token = self.tokens[idx]
            info = self.profile.pronoun_for(token.lemma)
            if info and info.role in allowed_roles:
                return self._pronoun_struct(info, token)
        return None

    def _pronoun_struct(self, info: PronounInfo, token: Token) -> Node:
        fields: dict[str, Node] = {"lemma": entity(info.lemma)}
        if info.person:
            fields["person"] = entity(info.person)
        if info.number:
            fields["number"] = entity(info.number)
        fields["role"] = entity(info.role)
        if token.surface:
            fields["surface"] = text(token.surface)
        return struct(**fields)

    def _build_action(self) -> Node | None:
        if self.verb_token is None:
            return None
        fields: dict[str, Node] = {
            "lemma": entity(self.verb_token.lemma),
            "mood": entity(self._action_mood()),
            "negated": boolean(bool(self.negation_markers)),
        }
        if self.verb_token.surface:
            fields["surface"] = text(self.verb_token.surface)
        metadata = self._resolve_verb_metadata()
        if metadata:
            fields["tense"] = entity(metadata.get("tense", "unknown"))
            person = metadata.get("person")
            number = metadata.get("number")
            lemma = metadata.get("lemma")
            if person:
                fields["person"] = entity(str(person))
            if number:
                fields["number"] = entity(str(number))
            if lemma:
                fields["canonical"] = entity(lemma.lower())
        return struct(**fields)

    def _action_mood(self) -> str:
        match self.sentence_type:
            case "question":
                return "interrogative"
            case "command":
                return "imperative"
            case _:
                return "indicative"

    def _resolve_verb_metadata(self) -> dict | None:
        metadata_table = VERB_METADATA.get(self.language)
        if not metadata_table or self.verb_token is None:
            return None
        for key in (self.verb_token.surface, self.verb_token.lemma):
            if not key:
                continue
            data = metadata_table.get(key.upper())
            if data:
                return data
        return None

    # endregion ----------------------------------------------------------------


def _find_entity(tokens: List[Token], pivot: int, reverse: bool) -> Node | None:
    positions = range(pivot - 1, -1, -1) if reverse else range(pivot + 1, len(tokens))
    for idx in positions:
        token = tokens[idx]
        if token.tag == "ENTITY":
            return entity(token.lemma)
    return None


def _build_relation(tokens: List[Token], pivot: int, rel_label: str | None) -> Node | None:
    if not rel_label:
        return None
    source = _find_entity(tokens, pivot, reverse=True)
    target = _find_entity(tokens, pivot, reverse=False)
    if source is None or target is None:
        return None
    return relation(rel_label, source, target)


__all__ = ["build_struct"]
