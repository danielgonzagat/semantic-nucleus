"""Frontend Elixir → LIU baseado em AST macroexpandido."""

from __future__ import annotations

from typing import Dict, List

from liu import entity, relation, struct, list_node, text


def compile_module(module: str, ast_data: Dict) -> List:
    functions = ast_data.get("functions", [])
    relations = []
    for fn in functions:
        name = fn["name"]
        params = [struct(name=entity(p)) for p in fn.get("params", [])]
        body = text(fn.get("body", ""))
        clause_struct = struct(name=entity(name), body=body, params=list_node(params))
        fn_entity = entity(f"code/fn::{module}::{name}")
        relations.append(relation("code/DEFN", fn_entity, clause_struct))
    module_entity = entity(f"code/mod::{module}")
    module_struct = struct(name=entity(module), body=list_node(relations))
    relations.append(relation("code/MODULE", module_entity, module_struct))
    return relations


__all__ = ["compile_module"]
