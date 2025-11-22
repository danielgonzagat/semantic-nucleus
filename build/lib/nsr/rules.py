"""
Regras e unificação simbólica.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from liu import Node, NodeKind


Binding = Dict[str, Node]


def unify(pattern: Node, fact: Node, bindings: Binding) -> Binding | None:
    if pattern.kind is NodeKind.VAR:
        name = pattern.label or ""
        bound = bindings.get(name)
        if bound is None:
            bindings[name] = fact
            return bindings
        return bindings if bound == fact else None
    if pattern.kind != fact.kind or pattern.label != fact.label:
        return None
    if len(pattern.args) != len(fact.args):
        return None
    new_bindings = dict(bindings)
    for p_arg, f_arg in zip(pattern.args, fact.args):
        result = unify(p_arg, f_arg, new_bindings)
        if result is None:
            return None
        new_bindings = result
    return new_bindings


def substitute(template: Node, bindings: Binding) -> Node:
    if template.kind is NodeKind.VAR:
        value = bindings.get(template.label or "")
        if value is None:
            raise ValueError(f"Unbound variable {template.label}")
        return value
    if template.args:
        new_args = tuple(substitute(arg, bindings) for arg in template.args)
        return Node(kind=template.kind, label=template.label, args=new_args, fields=template.fields, value=template.value)
    if template.kind is NodeKind.STRUCT:
        new_fields = tuple((k, substitute(v, bindings)) for k, v in template.fields)
        return Node(kind=template.kind, label=template.label, args=template.args, fields=new_fields, value=template.value)
    return template


def apply_rules(facts: Iterable[Node], rules: Iterable["Rule"]) -> List[Node]:
    from .state import Rule  # avoid cycle

    produced: List[Node] = []
    fact_list = list(facts)
    for rule in rules:
        matches = _match_rule(rule, fact_list)
        for match in matches:
            produced.append(substitute(rule.then, match))
    return produced


def _match_rule(rule: "Rule", facts: List[Node]) -> List[Binding]:
    results: List[Binding] = []
    _backtrack(rule.if_all, 0, {}, facts, results)
    return results


def _backtrack(patterns: Tuple[Node, ...], idx: int, bindings: Binding, facts: List[Node], out: List[Binding]) -> None:
    if idx >= len(patterns):
        out.append(dict(bindings))
        return
    pat = patterns[idx]
    for fact in facts:
        attempt = unify(pat, fact, dict(bindings))
        if attempt is not None:
            _backtrack(patterns, idx + 1, attempt, facts, out)


__all__ = ["unify", "substitute", "apply_rules"]
