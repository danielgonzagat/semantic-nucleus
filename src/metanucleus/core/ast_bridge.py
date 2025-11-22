"""
Conversor determinístico entre AST Python e LIU.
"""

from __future__ import annotations

import ast
from typing import List

from .liu import Node, NodeKind, struct, text, list_node


# ---------------------------------------------------------------------------
# Python AST ➜ LIU
# ---------------------------------------------------------------------------


def python_code_to_liu(source: str) -> Node:
    """
    Converte código-fonte Python para uma estrutura LIU canônica.
    """
    module = ast.parse(source)
    body_nodes = [ast_to_liu(stmt) for stmt in module.body]
    return struct(kind=text("py_module"), body=list_node(*body_nodes))


def ast_to_liu(node: ast.AST) -> Node:
    if isinstance(node, ast.FunctionDef):
        params = [text(arg.arg) for arg in node.args.args]
        body_nodes = [ast_to_liu(stmt) for stmt in node.body]
        return struct(
            kind=text("py_function"),
            name=text(node.name),
            params=list_node(*params),
            body=list_node(*body_nodes),
        )
    if isinstance(node, ast.Return):
        return struct(kind=text("py_return"), value=ast_to_liu(node.value) if node.value else struct(kind=text("py_none")))
    if isinstance(node, ast.Assign):
        targets = [ast_to_liu(t) for t in node.targets]
        return struct(
            kind=text("py_assign"),
            targets=list_node(*targets),
            value=ast_to_liu(node.value),
        )
    if isinstance(node, ast.Expr):
        return struct(kind=text("py_expr"), value=ast_to_liu(node.value))
    if isinstance(node, ast.Call):
        args = [ast_to_liu(arg) for arg in node.args]
        return struct(
            kind=text("py_call"),
            func=ast_to_liu(node.func),
            args=list_node(*args),
        )
    if isinstance(node, ast.Name):
        return struct(kind=text("py_name"), id=text(node.id))
    if isinstance(node, ast.Constant):
        value = node.value
        if isinstance(value, str):
            return struct(kind=text("py_const_str"), value=text(value))
        if isinstance(value, bool):
            return struct(kind=text("py_const_bool"), value=text("true" if value else "false"))
        if isinstance(value, (int, float)):
            return struct(kind=text("py_const_num"), value=text(str(value)))
        return struct(kind=text("py_const_other"), value=text(repr(value)))
    if isinstance(node, ast.BinOp):
        return struct(
            kind=text("py_binop"),
            op=text(type(node.op).__name__.lower()),
            left=ast_to_liu(node.left),
            right=ast_to_liu(node.right),
        )
    # fallback
    return struct(kind=text("py_unknown"), value=text(ast.dump(node)))


# ---------------------------------------------------------------------------
# LIU ➜ Python AST / código
# ---------------------------------------------------------------------------


def liu_to_python_code(node: Node) -> str:
    module_ast = liu_to_ast_module(node)
    module_ast = ast.fix_missing_locations(module_ast)
    try:
        return ast.unparse(module_ast)  # type: ignore[attr-defined]
    except Exception:
        return ast.dump(module_ast, indent=2)


def liu_to_ast_module(node: Node) -> ast.Module:
    if node.kind is NodeKind.STRUCT and node.fields.get("kind", text("")).label == "py_module":
        body_node = node.fields.get("body")
        stmts: List[ast.stmt] = []
        if body_node and body_node.kind is NodeKind.LIST:
            for item in body_node.args:
                stmts.append(liu_to_ast_stmt(item))
        return ast.Module(body=stmts, type_ignores=[])
    return ast.Module(body=[liu_to_ast_stmt(node)], type_ignores=[])


def liu_to_ast_stmt(node: Node) -> ast.stmt:
    kind = node.fields.get("kind")
    tag = kind.label if kind and kind.kind is NodeKind.TEXT else ""
    if tag == "py_function":
        name = node.fields.get("name")
        params = node.fields.get("params")
        body = node.fields.get("body")
        args = []
        if params and params.kind is NodeKind.LIST:
            for p in params.args:
                args.append(ast.arg(arg=p.label if p.kind is NodeKind.TEXT and p.label else "arg"))
        body_stmts = []
        if body and body.kind is NodeKind.LIST:
            for stmt in body.args:
                body_stmts.append(liu_to_ast_stmt(stmt))
        return ast.FunctionDef(
            name=name.label if name and name.kind is NodeKind.TEXT else "fn",
            args=ast.arguments(
                posonlyargs=[],
                args=args,
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
                vararg=None,
                kwarg=None,
            ),
            body=body_stmts or [ast.Pass()],
            decorator_list=[],
            returns=None,
            type_comment=None,
        )
    if tag == "py_return":
        value = node.fields.get("value")
        return ast.Return(value=liu_to_ast_expr(value) if value else None)
    if tag == "py_assign":
        targets_node = node.fields.get("targets")
        value_node = node.fields.get("value")
        targets = []
        if targets_node and targets_node.kind is NodeKind.LIST:
            for t in targets_node.args:
                targets.append(liu_to_ast_expr(t))
        return ast.Assign(targets=targets or [ast.Name(id="x", ctx=ast.Store())], value=liu_to_ast_expr(value_node))
    if tag == "py_expr":
        value = node.fields.get("value")
        return ast.Expr(value=liu_to_ast_expr(value))
    # fallback
    return ast.Expr(value=liu_to_ast_expr(node))


def liu_to_ast_expr(node: Node | None) -> ast.expr:
    if node is None:
        return ast.Constant(value=None)
    kind = node.fields.get("kind") if node.kind is NodeKind.STRUCT else None
    tag = kind.label if kind and kind.kind is NodeKind.TEXT else ""
    if node.kind is NodeKind.STRUCT and tag == "py_name":
        ident = node.fields.get("id")
        return ast.Name(id=ident.label if ident and ident.kind is NodeKind.TEXT else "x", ctx=ast.Load())
    if node.kind is NodeKind.STRUCT and tag == "py_const_str":
        value = node.fields.get("value")
        return ast.Constant(value=value.label if value else "")
    if node.kind is NodeKind.STRUCT and tag == "py_const_bool":
        value = node.fields.get("value")
        return ast.Constant(value=(value.label == "true") if value else False)
    if node.kind is NodeKind.STRUCT and tag == "py_const_num":
        value = node.fields.get("value")
        try:
            num = float(value.label) if value and value.label else 0.0
        except ValueError:
            num = 0.0
        return ast.Constant(value=int(num) if num.is_integer() else num)
    if node.kind is NodeKind.STRUCT and tag == "py_binop":
        left = liu_to_ast_expr(node.fields.get("left"))
        right = liu_to_ast_expr(node.fields.get("right"))
        op_name = node.fields.get("op")
        op = (op_name.label if op_name and op_name.kind is NodeKind.TEXT else "").lower()
        op_mapping = {
            "add": ast.Add(),
            "sub": ast.Sub(),
            "mult": ast.Mult(),
            "div": ast.Div(),
        }
        return ast.BinOp(left=left, op=op_mapping.get(op, ast.Add()), right=right)
    if node.kind is NodeKind.STRUCT and tag == "py_call":
        func = liu_to_ast_expr(node.fields.get("func"))
        args_node = node.fields.get("args")
        args = []
        if args_node and args_node.kind is NodeKind.LIST:
            for arg in args_node.args:
                args.append(liu_to_ast_expr(arg))
        return ast.Call(func=func, args=args, keywords=[])
    if node.kind is NodeKind.STRUCT and "value" in node.fields:
        return liu_to_ast_expr(node.fields["value"])
    return ast.Constant(value=str(node))
