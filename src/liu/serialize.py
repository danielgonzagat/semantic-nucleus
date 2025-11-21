"""
Serialização determinística em S-expr e JSON.
"""

from __future__ import annotations

import json
import re
from typing import Iterator, List, Tuple

from .kinds import NodeKind
from .nodes import (
    Node,
    list_node,
    number,
    boolean,
    entity,
    relation,
    operation,
    struct,
    text,
    var,
)
from .arena import canonical

class ParseError(ValueError):
    ...


def to_sexpr(node: Node) -> str:
    kind = node.kind
    if kind in (NodeKind.ENTITY, NodeKind.VAR, NodeKind.OP, NodeKind.REL):
        args = " ".join(to_sexpr(arg) for arg in node.args)
        suffix = f" {args}" if args else ""
        return f"({kind.value}:{node.label}{suffix})"

    if kind is NodeKind.STRUCT:
        fields = " ".join(f"({k} {to_sexpr(v)})" for k, v in node.fields)
        return f"(STRUCT {fields})"

    if kind is NodeKind.LIST:
        items = " ".join(to_sexpr(arg) for arg in node.args)
        return f"[{items}]"

    if kind is NodeKind.TEXT:
        literal = json.dumps(node.label or "", ensure_ascii=False)
        return f"(TEXT:{literal})"

    if kind is NodeKind.NUMBER:
        value = node.value
        if value is None:
            raise ParseError("NUMBER node missing value")
        return f"(NUMBER:{value})"

    if kind is NodeKind.BOOL:
        value = "true" if node.value else "false"
        return f"(BOOL:{value})"

    if kind is NodeKind.NIL:
        return "NIL"

    raise ParseError(f"Unsupported node kind {kind}")


def to_json(node: Node) -> str:
    return json.dumps(_to_json_obj(node), ensure_ascii=True, separators=(",", ":"))


def _to_json_obj(node: Node):
    kind = node.kind.value
    base = {"kind": kind}
    if node.label is not None:
        base["label"] = node.label
    if node.value is not None:
        base["value"] = node.value
    if node.args:
        base["args"] = [_to_json_obj(arg) for arg in node.args]
    if node.fields:
        base["fields"] = {k: _to_json_obj(v) for k, v in node.fields}
    return base


def from_json(data: str) -> Node:
    return _from_json_obj(json.loads(data))


def _from_json_obj(obj) -> Node:
    kind = NodeKind(obj["kind"])
    label = obj.get("label")
    args = tuple(_from_json_obj(arg) for arg in obj.get("args", ()))
    value = obj.get("value")
    fields = tuple(sorted(((k, _from_json_obj(v)) for k, v in obj.get("fields", {}).items()), key=lambda x: x[0]))
    return canonical(Node(kind=kind, label=label, args=args, fields=fields, value=value))


def parse_sexpr(source: str) -> Node:
    tokens = _tokenize(source)
    node, rest = _parse_expr(tokens)
    if rest:
        raise ParseError("Extra tokens at end")
    return canonical(node)


def _tokenize(source: str) -> List[str]:
    tokens: List[str] = []
    buf: List[str] = []
    i = 0
    length = len(source)
    while i < length:
        ch = source[i]
        if ch.isspace():
            if buf:
                tokens.append("".join(buf))
                buf.clear()
            i += 1
            continue
        if ch in "()[]":
            if buf:
                tokens.append("".join(buf))
                buf.clear()
            tokens.append(ch)
            i += 1
            continue
        if ch == '"':
            if buf:
                tokens.append("".join(buf))
                buf.clear()
            j = i + 1
            lit = ['"']
            while j < length:
                current = source[j]
                lit.append(current)
                if current == "\\":
                    j += 1
                    if j >= length:
                        break
                    lit.append(source[j])
                elif current == '"':
                    break
                j += 1
            if j >= length or source[j] != '"':
                raise ParseError("Unclosed string literal")
            tokens.append("".join(lit))
            i = j + 1
            continue
        buf.append(ch)
        i += 1
    if buf:
        tokens.append("".join(buf))
    return tokens


def _parse_expr(tokens: List[str], start: int = 0) -> Tuple[Node, List[str]]:
    if not tokens:
        raise ParseError("empty input")
    token = tokens.pop(0)
    if token == "NIL":
        from .nodes import NIL

        return NIL, tokens
    if token == "(":
        head = tokens.pop(0)
        if ":" in head:
            prefix, label = head.split(":", 1)
            args: List[Node] = []
            while tokens and tokens[0] != ")":
                arg, tokens = _parse_expr(tokens)
                args.append(arg)
            if not tokens or tokens.pop(0) != ")":
                raise ParseError("Missing )")
            if prefix == "ENTITY":
                return entity(label), tokens
            if prefix == "REL":
                return relation(label, *args), tokens
            if prefix == "OP":
                return operation(label, *args), tokens
            if prefix == "VAR":
                return var(label), tokens
            if prefix == "NUMBER":
                if not label:
                    raise ParseError("NUMBER literal missing payload")
                return number(float(label)), tokens
            if prefix == "BOOL":
                if not label:
                    raise ParseError("BOOL literal missing payload")
                return boolean(label.lower() == "true"), tokens
            if prefix == "TEXT":
                if label:
                    try:
                        text_value = json.loads(label)
                    except json.JSONDecodeError as exc:
                        raise ParseError("invalid TEXT literal") from exc
                    return text(text_value), tokens
                if len(args) == 1 and args[0].kind is NodeKind.TEXT:
                    return args[0], tokens
                raise ParseError("TEXT literal missing value")
            raise ParseError(f"Unknown prefix {prefix}")

        if head == "STRUCT":
            fields = {}
            while tokens and tokens[0] == "(":
                tokens.pop(0)
                key = tokens.pop(0)
                value, tokens = _parse_expr(tokens)
                if not tokens or tokens.pop(0) != ")":
                    raise ParseError("Missing ) in struct field")
                fields[key] = value
            if not tokens or tokens.pop(0) != ")":
                raise ParseError("Missing ) after struct")
            return struct(**fields), tokens
    if token == "[":
        items = []
        while tokens and tokens[0] != "]":
            item, tokens = _parse_expr(tokens)
            items.append(item)
        if not tokens or tokens.pop(0) != "]":
            raise ParseError("Missing ]")
        return list_node(items), tokens
    if token.startswith('"'):
        try:
            return text(json.loads(token)), tokens
        except json.JSONDecodeError as exc:
            raise ParseError("invalid string literal") from exc
    raise ParseError(f"Unexpected token {token}")


__all__ = ["to_sexpr", "parse_sexpr", "to_json", "from_json", "ParseError"]
