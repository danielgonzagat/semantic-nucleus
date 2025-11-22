"""
Logic bridge – interpreta comandos textuais simples (PT/EN/ES/FR/IT) em fatos e regras para o Logic-Engine.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Tuple

from liu import entity, number, struct as liu_struct, text as liu_text, Node

from .logic_engine import LogicEngine, negate, normalize_statement
from .logic_persistence import serialize_logic_engine

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
    original_text: str


@dataclass(frozen=True)
class LogicHook:
    result: LogicBridgeResult
    struct_node: Node
    answer_node: Node
    context_nodes: Tuple[Node, ...]
    quality: float
    trace_label: str
    snapshot: str


def maybe_route_logic(text: str, engine: LogicEngine | None = None) -> LogicHook | None:
    result = interpret_logic_command(text, engine=engine)
    if result is None:
        return None
    return _build_hook(result)


def interpret_logic_command(text: str, engine: LogicEngine | None = None) -> LogicBridgeResult | None:
    engine = engine or LogicEngine()
    normalized = _normalize_upper(text)

    rule_payload = _parse_rule(normalized)
    if rule_payload:
        premises, conclusion = rule_payload
        logic_rule = engine.add_rule(premises, conclusion)
        new_facts = tuple(sorted(engine.infer()))
        return LogicBridgeResult(
            action="rule",
            statement=None,
            truth=None,
            premises=logic_rule.premises,
            conclusion=logic_rule.conclusion,
            new_facts=new_facts,
            engine=engine,
            original_text=text,
        )

    fact_statement = _parse_fact(normalized)
    if fact_statement:
        engine.add_fact(fact_statement)
        new_facts = tuple(sorted(engine.infer()))
        return LogicBridgeResult(
            action="fact",
            statement=fact_statement,
            truth=True,
            premises=(),
            conclusion=None,
            new_facts=new_facts,
            engine=engine,
            original_text=text,
        )

    query_statement = _parse_query(normalized)
    if query_statement:
        truth = engine.facts.get(query_statement)
        truth_value = True if truth else False if truth is not None else None
        return LogicBridgeResult(
            action="query",
            statement=query_statement,
            truth=truth_value,
            premises=(),
            conclusion=None,
            new_facts=(),
            engine=engine,
            original_text=text,
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


def _build_hook(result: LogicBridgeResult) -> LogicHook:
    struct_node = liu_struct(
        tag=entity("logic_input"),
        action=entity(result.action.upper()),
        original=liu_text(result.original_text),
        statement=liu_text(result.statement or ""),
    )
    answer_text, truth_label = _answer_text(result)
    answer_node = liu_struct(
        tag=entity("logic_answer"),
        answer=liu_text(answer_text),
        truth=entity(truth_label),
    )
    context_nodes = _context_from_result(result)
    quality = 0.96 if result.action == "query" else 0.9
    trace_label = f"LOGIC[{result.action.upper()}]"
    snapshot_blob = serialize_logic_engine(result.engine)
    return LogicHook(
        result=result,
        struct_node=struct_node,
        answer_node=answer_node,
        context_nodes=context_nodes,
        quality=quality,
        trace_label=trace_label,
        snapshot=snapshot_blob,
    )


def _answer_text(result: LogicBridgeResult) -> Tuple[str, str]:
    if result.action == "fact":
        return (f"FACT OK: {result.statement}", "ACK")
    if result.action == "rule":
        premises = " ∧ ".join(result.premises)
        conclusion = result.conclusion or ""
        return (f"RULE OK: {premises} ⇒ {conclusion}", "ACK")
    if result.action == "query":
        if result.truth is True:
            return (f"TRUE: {result.statement}", "TRUE")
        if result.truth is False:
            return (f"FALSE: {result.statement}", "FALSE")
        return (f"UNKNOWN: {result.statement}", "UNKNOWN")
    return ("NO ACTION", "UNKNOWN")


def _context_from_result(result: LogicBridgeResult) -> Tuple[Node, ...]:
    context = []
    if result.statement:
        context.append(
            liu_struct(tag=entity("logic_statement"), value=liu_text(result.statement), action=entity(result.action.upper()))
        )
    if result.premises:
        context.append(
            liu_struct(
                tag=entity("logic_rule"),
                premises=liu_text(" ∧ ".join(result.premises)),
                conclusion=liu_text(result.conclusion or ""),
            )
        )
    for fact in result.new_facts:
        context.append(liu_struct(tag=entity("logic_fact"), value=liu_text(fact), status=entity("DERIVED")))
    context.append(
        liu_struct(
            tag=entity("logic_state"),
            facts=number(len(result.engine.facts)),
            rules=number(len(result.engine.rules)),
        )
    )
    return tuple(context)


__all__ = ["LogicBridgeResult", "LogicHook", "maybe_route_logic", "interpret_logic_command"]
