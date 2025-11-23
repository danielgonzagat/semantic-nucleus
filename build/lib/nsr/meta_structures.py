"""
Conversores determinísticos de LC-Ω para estruturas LIU/metacálculo.
"""

from __future__ import annotations

from typing import Iterable, Tuple

from liu import Node, entity, list_node, struct as liu_struct, text

from .lc_omega import LCParseResult, LCTerm, MetaCalculation, lc_parse


def lc_term_to_node(term: LCTerm) -> Node:
    """
    Converte um `LCTerm` em um STRUCT LIU auditável.
    """

    fields: dict[str, Node] = {"kind": entity(term.kind)}
    if term.label:
        fields["label"] = entity(term.label)
    if term.children:
        fields["children"] = list_node(_iter_terms(term.children))
    return liu_struct(**fields)


def meta_calculation_to_node(calc: MetaCalculation) -> Node:
    """
    Serializa `MetaCalculation` para LIU (operador + operandos).
    """

    fields: dict[str, Node] = {
        "tag": entity("meta_calculation"),
        "operator": entity(calc.operator),
    }
    if calc.operands:
        fields["operands"] = list_node(lc_term_to_node(term) for term in calc.operands)
    return liu_struct(**fields)


def build_lc_meta_struct(result: LCParseResult) -> Node:
    """
    Cria STRUCT determinística com tokens, semântica, termo e cálculo LC-Ω.
    """

    fields: dict[str, Node] = {
        "tag": entity("lc_meta"),
        "language": entity(result.language),
        "tokens": list_node(text(token) for token in result.tokens),
        "semantics": list_node(entity(item) for item in result.semantics),
        "term": lc_term_to_node(result.term),
    }
    if result.pattern:
        fields["pattern"] = entity(result.pattern)
    if result.calculus:
        fields["calculus"] = meta_calculation_to_node(result.calculus)
    return liu_struct(**fields)


def maybe_build_lc_meta_struct(language: str, text_value: str) -> Tuple[Node | None, LCParseResult | None]:
    """
    Executa `lc_parse` e devolve o pacote meta pronto para anexar ao contexto.
    """

    try:
        parsed = lc_parse(language, text_value)
    except ValueError:
        return None, None
    return build_lc_meta_struct(parsed), parsed


def _iter_terms(terms: Iterable[LCTerm]):
    for child in terms:
        yield lc_term_to_node(child)


__all__ = [
    "lc_term_to_node",
    "meta_calculation_to_node",
    "build_lc_meta_struct",
    "maybe_build_lc_meta_struct",
]
