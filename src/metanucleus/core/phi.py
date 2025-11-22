"""
Operadores Φ determinísticos (versão mínima).
"""

from __future__ import annotations

import ast
import operator
from typing import Tuple

from .liu import Node, NodeKind, struct, text, op, number
from .state import MetaState


def apply_phi(state: MetaState, operator: Node) -> None:
    """
    Despacha a operação Φ apropriada.
    """

    if operator.kind is not NodeKind.OP:
        return
    label = (operator.label or "").upper()
    args = tuple(operator.args)

    if label == "NORMALIZE":
        phi_normalize(state, args)
    elif label == "INTENT":
        phi_intent(state, args)
    elif label == "STRUCTURE":
        phi_structure(state, args)
    elif label == "SEMANTICS":
        phi_semantics(state, args)
    elif label == "CALCULUS":
        phi_calculus(state, args)
    elif label == "ANSWER":
        phi_answer(state, args)


def phi_normalize(state: MetaState, args: Tuple[Node, ...]) -> None:
    """
    Versão mínima: limita o tamanho do contexto e melhora qualidade.
    """

    isr = state.isr
    max_ctx = 16
    if len(isr.context) > max_ctx:
        isr.context = isr.context[-max_ctx:]
    isr.quality = min(1.0, isr.quality + 0.05)


def phi_intent(state: MetaState, args: Tuple[Node, ...]) -> None:
    """
    Clasifica a intenção básica da utterance (saudação, pergunta, etc.).
    """

    if not args:
        return
    msg = args[0]
    if msg.kind is not NodeKind.STRUCT:
        return
    intent = _classify_intent(_content_text(msg))
    msg.fields["intent"] = text(intent)
    state.isr.quality = min(1.0, state.isr.quality + 0.1)
    # garantir pipeline: STRUCTURE -> SEMANTICS antes do ANSWER restante
    isr = state.isr
    isr.ops_queue.insert(0, op("SEMANTICS", msg))
    isr.ops_queue.insert(0, op("STRUCTURE", msg))


def phi_answer(state: MetaState, args: Tuple[Node, ...]) -> None:
    """
    Produz uma resposta textual determinística baseada no último input.
    """

    msg = args[0] if args else None
    preview = _extract_preview(msg) if msg is not None else "entrada desconhecida"
    intent = ""
    semantic_kind = ""
    semantic_cost = 0.0
    calc_result = None
    calc_expr = ""
    if msg and msg.kind is NodeKind.STRUCT:
        intent_node = msg.fields.get("intent")
        if intent_node and intent_node.kind is NodeKind.TEXT:
            intent = intent_node.label or ""
        semantics = msg.fields.get("semantics")
        if semantics and semantics.kind is NodeKind.STRUCT:
            sk = semantics.fields.get("semantic_kind")
            if sk and sk.kind is NodeKind.TEXT and sk.label:
                semantic_kind = sk.label
            cost_node = semantics.fields.get("semantic_cost")
            if cost_node and cost_node.kind is NodeKind.NUMBER and cost_node.value_num is not None:
                semantic_cost = float(cost_node.value_num)
        calculus = msg.fields.get("calculus")
        if calculus and calculus.kind is NodeKind.STRUCT:
            res = calculus.fields.get("result")
            expr_node = calculus.fields.get("expression")
            if res and res.kind is NodeKind.NUMBER and res.value_num is not None:
                calc_result = res.value_num
                calc_expr = expr_node.label if expr_node and expr_node.kind is NodeKind.TEXT else ""

    isr = state.isr

    if calc_result is not None:
        ans_text = f"{calc_expr} = {calc_result}" if calc_expr else f"O resultado é {calc_result}"
    elif intent == "greeting":
        ans_text = "Olá! Sou o Metanúcleo determinístico. Prazer em te ouvir."
    elif semantic_kind == "question" or intent == "question":
        if semantic_cost >= 15:
            ans_text = f"Pergunta complexa registrada: {preview}"
        else:
            ans_text = f"Pergunta registrada: {preview}"
    else:
        ans_text = f"[META] Recebi: {preview}. Estou processando simbolicamente."

    response = struct(answer=text(ans_text))
    isr.answer = response
    isr.quality = min(1.0, isr.quality + 0.2)


def _extract_preview(msg: Node | None) -> str:
    text_value = _content_text(msg)
    if not text_value:
        return "entrada desconhecida"
    return text_value if len(text_value) <= 60 else text_value[:57] + "..."


def _content_text(msg: Node | None) -> str:
    if msg is None:
        return ""
    if msg.kind is NodeKind.STRUCT:
        content = msg.fields.get("content") or msg.fields.get("raw")
        if content and content.kind is NodeKind.TEXT and content.label:
            return content.label
    if msg.kind is NodeKind.TEXT and msg.label:
        return msg.label
    if msg.label:
        return msg.label
    return ""


def _classify_intent(text_value: str) -> str:
    normalized = text_value.lower().strip()
    if not normalized:
        return "statement"
    greetings = {"oi", "olá", "ola", "hello", "hi", "hey", "bom dia", "boa tarde", "boa noite"}
    for greet in greetings:
        if normalized.startswith(greet):
            return "greeting"
    if "?" in normalized:
        return "question"
    return "statement"


def phi_structure(state: MetaState, args: Tuple[Node, ...]) -> None:
    """
    Garante que a utterance tenha tokens e length.
    Caso o adaptador tenha fornecido, apenas reforça a qualidade.
    """

    if not args:
        return
    msg = args[0]
    if msg.kind is not NodeKind.STRUCT:
        return
    tokens = msg.fields.get("tokens")
    length = msg.fields.get("length")
    if tokens and length:
        state.isr.quality = min(1.0, state.isr.quality + 0.05)
        return
    raw = _content_text(msg)
    from metanucleus.lang.tokenizer import tokenize, tokens_to_struct

    toks = tokenize(raw)
    msg.fields["tokens"] = tokens_to_struct(toks)
    msg.fields["length"] = text(str(len(toks)))
    state.isr.quality = min(1.0, state.isr.quality + 0.05)


def phi_semantics(state: MetaState, args: Tuple[Node, ...]) -> None:
    """
    Deriva rótulos semânticos simples e um custo determinístico.
    """

    if not args:
        return
    msg = args[0]
    if msg.kind is not NodeKind.STRUCT:
        return
    raw = _content_text(msg)
    tokens_struct = msg.fields.get("tokens")
    tokens_list = _flatten_tokens(tokens_struct)
    total_tokens = len(tokens_list)
    unique_tokens = len({tok.lower() for tok in tokens_list})

    has_math = any(ch.isdigit() for ch in raw) and any(op in raw for op in {"+", "-", "*", "/"} )
    intent = msg.fields.get("intent")
    intent_label = intent.label if intent and intent.kind is NodeKind.TEXT else ""

    if has_math and ("?" in raw or intent_label == "question"):
        semantic_kind = "math_question"
    elif intent_label == "question" or "?" in raw:
        semantic_kind = "question"
    elif intent_label == "greeting":
        semantic_kind = "greeting"
    else:
        semantic_kind = "statement"

    semantic_cost = unique_tokens + total_tokens * 0.5
    if has_math:
        semantic_cost += 2

    msg.fields["semantics"] = struct(
        kind=text("semantics"),
        semantic_kind=text(semantic_kind),
        tokens_count=number(float(total_tokens)),
        unique_tokens=number(float(unique_tokens)),
        semantic_cost=number(float(semantic_cost)),
        has_math=text("true" if has_math else "false"),
    )
    state.isr.quality = min(1.0, state.isr.quality + 0.05)
    state.isr.ops_queue.insert(0, op("CALCULUS", msg))


def _flatten_tokens(tokens_struct: Node | None) -> list[str]:
    if tokens_struct is None or tokens_struct.kind is not NodeKind.STRUCT:
        return []
    flattened = []
    for entry in tokens_struct.fields.values():
        if entry.kind is NodeKind.STRUCT:
            surface = entry.fields.get("surface")
            if surface and surface.kind is NodeKind.TEXT and surface.label:
                flattened.append(surface.label)
    return flattened


def phi_calculus(state: MetaState, args: Tuple[Node, ...]) -> None:
    """
    Detecta expressões matemáticas simples e avalia de forma segura.
    """

    if not args:
        return
    msg = args[0]
    if msg.kind is not NodeKind.STRUCT:
        return
    expr = _extract_math_expr(_content_text(msg))
    if not expr:
        return
    try:
        value = _safe_eval(expr)
    except ValueError:
        return
    msg.fields["calculus"] = struct(
        kind=text("calculus"),
        expression=text(expr),
        result=number(value),
    )
    msg.fields["equivalence"] = text(f"{expr} = {value}")
    state.isr.quality = min(1.0, state.isr.quality + 0.08)


def _extract_math_expr(raw: str) -> str:
    digits_seen = any(ch.isdigit() for ch in raw)
    ops_seen = any(op in raw for op in {"+", "-", "*", "/", "%"})
    if not (digits_seen and ops_seen):
        return ""
    # pega substring entre primeiro e último dígito
    first = next((i for i, ch in enumerate(raw) if ch.isdigit()), None)
    last = next((i for i in range(len(raw) - 1, -1, -1) if raw[i].isdigit()), None)
    if first is None or last is None or first >= last:
        return ""
    expr = raw[first : last + 1]
    allowed = set("0123456789+-*/().% ")
    cleaned = "".join(ch for ch in expr if ch in allowed)
    return cleaned.strip()


_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _safe_eval(expr: str) -> float:
    tree = ast.parse(expr, mode="eval")

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Num):  # py<3.8 compat
            return float(node.n)
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in _BIN_OPS:
                raise ValueError("operador não permitido")
            return _BIN_OPS[op_type](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in _UNARY_OPS:
                raise ValueError("operador unário não permitido")
            return _UNARY_OPS[op_type](_eval(node.operand))
        raise ValueError("expressão inválida")

    return _eval(tree.body)  # type: ignore[arg-type]
