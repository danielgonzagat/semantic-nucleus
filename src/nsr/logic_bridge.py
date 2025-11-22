"""
Logic bridge – interpreta comandos textuais simples (PT/EN/ES/FR/IT) em fatos e regras para o Logic-Engine.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Tuple

from .logic_engine import LogicEngine, negate, normalize_statement

RULE_START_WORDS = ("IF", "SE", "SI")
RULE_THEN_WORDS = ("THEN", "ENTAO", "ENTONCES", "ALORS")
CONJUNCTION_PATTERN = re.compile(r"\b(?:AND|E|Y|ET|I)\b")
FACT_PREFIXES = ("FACT", "ASSERT", "ASSUME", "GIVEN", "AFIRME", "AFIRMA", "CONSIDER")
QUERY_PREFIXES = ("QUERY", "ASK", "IS IT TRUE THAT", "E VERDADE QUE", "ES VERDAD QUE")
NEGATION_PREFIXES = ("NOT", "NAO", "NO", "NON", "NE", "NES")
PUNCT_STRIP = " .,:;!?\"'"


@dataclass(frozen=True)
class LogicBridgeResult:
    action: str
    statement: str | None
    truth: bool | None
    premises: Tuple[str, ...]
    conclusion: str | None
    new_facts: Tuple[str, ...]
    engine: LogicEngine


def maybe_route_logic(text: str, engine: LogicEngine | None = None) -> LogicBridgeResult | None:
    engine = engine or LogicEngine()
    normalized = _normalize_upper(text)

    rule_payload = _parse_rule(normalized)
    if rule_payload:
        premises, conclusion = rule_payload
        logic_rule = engine.add_rule(premises, conclusion)
        new_facts = tuple(engine.infer())
        return LogicBridgeResult(
            action="rule",
            statement=None,
            truth=None,
            premises=logic_rule.premises,
            conclusion=logic_rule.conclusion,
            new_facts=new_facts,
            engine=engine,
        )

    fact_statement = _parse_fact(normalized)
    if fact_statement:
        engine.add_fact(fact_statement)
        new_facts = tuple(engine.infer())
        return LogicBridgeResult(
            action="fact",
            statement=fact_statement,
            truth=True,
            premises=(),
            conclusion=None,
            new_facts=new_facts,
            engine=engine,
        )

    query_statement = _parse_query(normalized)
    if query_statement:
        truth = engine.facts.get(query_statement)
        return LogicBridgeResult(
            action="query",
            statement=query_statement,
            truth=True if truth else False if truth is not None else None,
            premises=(),
            conclusion=None,
            new_facts=(),
            engine=engine,
        )

    return None


def _parse_rule(normalized_text: str) -> Tuple[Tuple[str, ...], str] | None:
    for start in RULE_START_WORDS:
        prefix = f"{start} "
        if normalized_text.startswith(prefix):
            remainder = normalized_text[len(prefix) :]
            for then_word in RULE_THEN_WORDS:
                marker = f" {then_word} "
                if marker in remainder:
                    antecedent, consequent = remainder.split(marker, 1)
                    premises = _split_premises(antecedent)
                    conclusion = _canonical_statement(consequent)
                    if premises and conclusion:
                        return premises, conclusion
    return None


def _parse_fact(normalized_text: str) -> str | None:
    for prefix in FACT_PREFIXES:
        token = f"{prefix} "
        if normalized_text.startswith(token):
            statement = normalized_text[len(token) :]
            canonical = _canonical_statement(statement)
            return canonical
    return None


def _parse_query(normalized_text: str) -> str | None:
    for prefix in QUERY_PREFIXES:
        token = f"{prefix} "
        if normalized_text.startswith(token):
            statement = normalized_text[len(token) :]
            canonical = _canonical_statement(statement)
            return canonical
    return None


def _split_premises(segment: str) -> Tuple[str, ...]:
    parts = CONJUNCTION_PATTERN.split(segment)
    canonical = tuple(filter(None, (_canonical_statement(part) for part in parts)))
    return canonical


def _canonical_statement(segment: str) -> str:
    segment = segment.strip(PUNCT_STRIP)
    if not segment:
        return ""
    for neg_prefix in NEGATION_PREFIXES:
        token = f"{neg_prefix} "
        if segment.startswith(token):
            inner = segment[len(token) :]
            return negate(inner)
    return normalize_statement(segment)


def _normalize_upper(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    upper = stripped.upper()
    return " ".join(upper.split())


__all__ = ["LogicBridgeResult", "maybe_route_logic"]
