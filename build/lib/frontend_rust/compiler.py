"""Frontend Rust → LIU (HIR/MIR simplificado)."""

from __future__ import annotations

from typing import Dict, List

from liu import entity, relation, struct, list_node, text


def compile_items(module: str, hir_items: List[Dict]) -> List:
    relations = []
    for item in hir_items:
        if item.get("kind") == "fn":
            relations.extend(_lower_fn(module, item))
    module_entity = entity(f"code/mod::{module}")
    module_struct = struct(name=entity(module), body=list_node(relations))
    relations.append(relation("code/MODULE", module_entity, module_struct))
    return relations


def _lower_fn(module: str, item: Dict) -> List:
    fn_entity = entity(f"code/fn::{module}::{item['name']}")
    params = [
        struct(name=entity(param["name"]), type=text(param.get("type", "")))
        for param in item.get("params", [])
    ]
    body = text(item.get("body", ""))
    fn_struct = struct(name=entity(item["name"]), params=list_node(params), body=body, ret=text(item.get("ret", "")))
    rels = [relation("code/DEFN", fn_entity, fn_struct)]
    for param in params:
        rels.append(relation("code/PARAM", fn_entity, param))
    if item.get("ret"):
        rels.append(relation("code/RETURNS", fn_entity, entity(item["ret"])))
    return rels


__all__ = ["compile_items"]
