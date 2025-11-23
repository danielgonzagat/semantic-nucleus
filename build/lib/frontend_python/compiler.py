"""
Frontend Python → LIU (subset determinístico).
"""

from __future__ import annotations

import ast
from typing import List

from liu import Node, entity, relation, struct, list_node, number, text


def compile_source(source: str, module: str = "main") -> List[Node]:
    tree = ast.parse(source)
    lowerer = _Lowerer(module)
    lowerer.visit(tree)
    relations = list(lowerer.relations)
    module_entity = entity(f"code/mod::{module}")
    module_struct = struct(name=entity(module), body=list_node(relations))
    relations.append(relation("code/MODULE", module_entity, module_struct))
    return relations


class _Lowerer(ast.NodeVisitor):
    def __init__(self, module: str):
        self.module = module
        self.relations: List[Node] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        fn_symbol = entity(f"code/fn::{self.module}::{node.name}")
        params = [struct(name=entity(arg.arg)) for arg in node.args.args]
        body_nodes = list_node([self._lower_stmt(stmt) for stmt in node.body])
        fn_struct = struct(name=entity(node.name), params=list_node(params), body=body_nodes)
        self.relations.append(relation("code/DEFN", fn_symbol, fn_struct))
        for param in params:
            self.relations.append(relation("code/PARAM", fn_symbol, param))

    def _lower_stmt(self, stmt: ast.stmt) -> Node:
        if isinstance(stmt, ast.Return):
            expr = self._lower_expr(stmt.value)
            return struct(return_=expr)
        if isinstance(stmt, ast.Assign):
            target = self._lower_expr(stmt.targets[0])
            value = self._lower_expr(stmt.value)
            return struct(assign=struct(target=target, value=value))
        return struct(raw=text(ast.dump(stmt)))

    def _lower_expr(self, expr: ast.AST) -> Node:
        if isinstance(expr, ast.Constant):
            if isinstance(expr.value, (int, float)):
                return number(expr.value)
            if isinstance(expr.value, str):
                return text(expr.value)
        if isinstance(expr, ast.Name):
            return entity(expr.id)
        if isinstance(expr, ast.BinOp):
            return struct(
                binop=struct(
                    op=text(expr.op.__class__.__name__),
                    left=self._lower_expr(expr.left),
                    right=self._lower_expr(expr.right),
                )
            )
        return struct(raw=text(ast.dump(expr)))


__all__ = ["compile_source"]
