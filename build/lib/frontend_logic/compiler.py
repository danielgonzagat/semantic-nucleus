"""Frontend lógico (Prolog-like) → LIU."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

from liu import entity, relation, var, Node

FACT_RE = re.compile(r"\s*([a-zA-Z_][\w]*)\(([^)]*)\)\s*\.")
RULE_RE = re.compile(r"\s*([a-zA-Z_][\w]*)\(([^)]*)\)\s*:-\s*(.*)\.")


@dataclass(frozen=True)
class LogicRule:
    premises: Tuple[Node, ...]
    conclusion: Node


def compile_logic(text: str) -> tuple[List[Node], List[LogicRule]]:
    facts: List[Node] = []
    rules: List[LogicRule] = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        rule_match = RULE_RE.fullmatch(line)
        if rule_match:
            head = _parse_atom(rule_match.group(1), rule_match.group(2))
            body_atoms = [_parse_atom(*_split_atom(part)) for part in _split_body(rule_match.group(3))]
            rules.append(LogicRule(tuple(body_atoms), head))
            continue
        fact_match = FACT_RE.fullmatch(line)
        if fact_match:
            facts.append(_parse_atom(fact_match.group(1), fact_match.group(2)))
    return facts, rules


def _split_body(segment: str) -> List[str]:
    parts: List[str] = []
    buffer = ""
    depth = 0
    for ch in segment:
        if ch == "," and depth == 0:
            parts.append(buffer.strip())
            buffer = ""
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        buffer += ch
    if buffer.strip():
        parts.append(buffer.strip())
    return parts


def _split_atom(fragment: str) -> tuple[str, str]:
    name, args = fragment.strip().split("(", 1)
    return name.strip(), args.strip(" )")


def _parse_atom(name: str, raw_args: str) -> Node:
    args = []
    for item in raw_args.split(","):
        token = item.strip()
        if not token:
            continue
        if token.startswith("?"):
            args.append(var(token))
        else:
            args.append(entity(token))
    return relation(name, *args)


__all__ = ["compile_logic", "LogicRule"]
