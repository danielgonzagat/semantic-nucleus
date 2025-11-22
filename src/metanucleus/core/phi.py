"""
Operadores Φ determinísticos (versão 1.0).
"""

from __future__ import annotations

import ast
import operator
from typing import Iterable, List, Optional

from metanucleus.lang.tokenizer import tokenize, tokens_to_struct

from .liu import Node, NodeKind, struct, text, op, number, rel
from .state import MetaState, _rel_signature


def apply_phi(state: MetaState, operator_node: Node) -> None:
    if operator_node.kind is not NodeKind.OP:
        return
    label = (operator_node.label or "").upper()
    args = tuple(operator_node.args)

    if label == "NORMALIZE":
        phi_normalize(state)
    elif label == "INTENT":
        phi_intent(state, args)
    elif label == "LANGUAGE":
        phi_language(state, args)
    elif label == "STRUCTURE":
        phi_structure(state, args)
    elif label == "SEMANTICS":
        phi_semantics(state, args)
    elif label == "CALCULUS":
        phi_calculus(state, args)
    elif label == "EQUIVALENCE":
        phi_equivalence(state, args)
    elif label == "DETERMINE":
        phi_determine(state, args)
    elif label == "ANSWER":
        phi_answer(state, args)


def phi_normalize(state: MetaState) -> None:
    isr = state.isr
    max_ctx = 32
    if len(isr.context) > max_ctx:
        isr.context = isr.context[-max_ctx:]
    isr.quality = min(1.0, isr.quality + 0.02)


def phi_intent(state: MetaState, args: tuple[Node, ...]) -> None:
    if not args:
        return
    msg = args[0]
    if msg.kind is not NodeKind.STRUCT:
        return

    intent = _as_text(_field(msg, "intent"))
    raw = _content_text(msg)

    if not intent:
        normalized = raw.lower()
        if any(normalized.startswith(greet) for greet in ("oi", "olá", "ola", "hello", "hi", "hey", "bom dia", "boa tarde", "boa noite")):
            intent = "greeting"
        elif "?" in normalized:
            intent = "question"
        elif normalized.split(" ", 1)[0] in {"faça", "faz", "cria", "gera", "show", "do"}:
            intent = "command"
        else:
            intent = "statement"
        msg = _with_field(msg, "intent", text(intent))

    # injeta novamente no contexto para facilitar debug
    state.isr.context.append(msg)

    # pipeline Φ em ordem determinística
    plan = [
        op("LANGUAGE", msg),
        op("STRUCTURE", msg),
        op("SEMANTICS", msg),
        op("CALCULUS", msg),
        op("EQUIVALENCE", msg),
        op("DETERMINE", msg),
        op("ANSWER", msg),
    ]
    for operation in reversed(plan):
        state.isr.ops_queue.insert(0, operation)

    state.isr.quality = min(1.0, state.isr.quality + 0.05)


def phi_language(state: MetaState, args: tuple[Node, ...]) -> None:
    if not args:
        return
    msg = args[0]
    if msg.kind is not NodeKind.STRUCT:
        return

    lang = _guess_lang(msg)
    msg = _with_field(msg, "lang", text(lang))
    msg = _with_field(msg, "lang_code", text(lang))
    state.isr.context.append(msg)
    state.isr.quality = min(1.0, state.isr.quality + 0.02)


def phi_structure(state: MetaState, args: tuple[Node, ...]) -> None:
    if not args:
        return
    msg = args[0]
    if msg.kind is not NodeKind.STRUCT:
        return

    if _is_code_snippet(msg):
        ast_node = _field(msg, "ast")
        if ast_node:
            msg = _with_field(msg, "structure", ast_node)
    else:
        tokens_node = _field(msg, "tokens")
        if tokens_node is None or tokens_node.kind is not NodeKind.STRUCT:
            raw = _content_text(msg)
            toks = tokenize(raw)
            tokens_node = tokens_to_struct(toks)
            msg = _with_field(msg, "tokens", tokens_node)

        token_count = len(tokens_node.fields)
        msg = _with_field(msg, "length", text(str(token_count)))

    state.isr.context.append(msg)
    state.isr.quality = min(1.0, state.isr.quality + 0.03)


def phi_semantics(state: MetaState, args: tuple[Node, ...]) -> None:
    if not args:
        return
    msg = args[0]
    if msg.kind is not NodeKind.STRUCT:
        return

    tokens = _token_list(_field(msg, "tokens"))
    lang = _guess_lang(msg)
    if _is_code_snippet(msg):
        has_math = False
    else:
        has_math = any(ch.isdigit() for ch in _content_text(msg)) and any(op in _content_text(msg) for op in "+-*/")
    logic_ops = _detect_logic_ops(tokens, lang)
    unique_tokens = len(set(token.lower() for token in tokens if token))
    semantic_cost = unique_tokens + len(tokens) * 0.5 + len(logic_ops) * 2 + (2 if has_math else 0)

    intent = _as_text(_field(msg, "intent"))
    raw = _content_text(msg)
    if _is_code_snippet(msg):
        semantic_kind = "code_snippet"
    elif has_math and ("?" in raw or intent == "question"):
        semantic_kind = "math_question"
    elif intent == "greeting":
        semantic_kind = "greeting"
    elif intent == "command":
        semantic_kind = "command"
    elif intent == "question" or "?" in raw:
        semantic_kind = "question"
    else:
        semantic_kind = "statement"

    semantics_struct = struct(
        kind=text("semantics"),
        semantic_kind=text(semantic_kind),
        semantic_cost=number(float(semantic_cost)),
        tokens_count=number(float(len(tokens))),
        unique_tokens=number(float(unique_tokens)),
        has_math=text("true" if has_math else "false"),
        logic_ops=_list_node(text(op_name) for op_name in logic_ops),
    )
    msg = _with_field(msg, "semantics", semantics_struct)
    state.isr.context.append(msg)
    state.isr.quality = min(1.0, state.isr.quality + 0.04)


def phi_calculus(state: MetaState, args: tuple[Node, ...]) -> None:
    if not args:
        return
    msg = args[0]
    if msg.kind is not NodeKind.STRUCT:
        return

    if _is_code_snippet(msg):
        structure = _field(msg, "structure") or _field(msg, "ast")
        if structure:
            complexity = float(_node_complexity(structure))
            calculus_struct = struct(
                kind=text("code_structure"),
                cost_struct=number(complexity),
                solved=text("false"),
            )
            msg = _with_field(msg, "calculus", calculus_struct)
            state.isr.context.append(msg)
            state.isr.quality = min(1.0, state.isr.quality + 0.02)
        return

    raw = _content_text(msg)
    expr = _extract_math_expr(raw)
    solved = False
    result_node = struct(kind=text("empty"))
    cost_expr = 0

    if expr:
        try:
            value = _safe_eval_math(expr)
            result_node = number(float(value))
            solved = True
            try:
                tree = ast.parse(expr, mode="eval")
                cost_expr = sum(1 for _ in ast.walk(tree))
            except Exception:
                cost_expr = 0
            fact = rel("EQUALS", text(expr), number(float(value)))
            state.isr.relations.add(_rel_signature(fact))
        except ValueError:
            solved = False

    calculus_struct = struct(
        kind=text("meta_calculus"),
        has_math=text("true" if expr else "false"),
        expression=text(expr),
        result=result_node if solved else text(""),
        cost_expr=number(float(cost_expr)),
        cost_struct=number(float(_node_complexity(msg))),
        solved=text("true" if solved else "false"),
    )
    msg = _with_field(msg, "calculus", calculus_struct)
    state.isr.context.append(msg)
    state.isr.quality = min(1.0, state.isr.quality + (0.08 if solved else 0.02))


def phi_equivalence(state: MetaState, args: tuple[Node, ...]) -> None:
    if not args:
        return
    msg = args[0]
    if msg.kind is not NodeKind.STRUCT:
        return

    if _is_code_snippet(msg):
        return

    calculus = _field(msg, "calculus")
    if calculus is None or calculus.kind is not NodeKind.STRUCT:
        return

    expr = _as_text(calculus.fields.get("expression"))
    result = calculus.fields.get("result")
    solved = _as_text(calculus.fields.get("solved")) == "true"

    if expr and result and result.kind is NodeKind.NUMBER and solved:
        equivalence_text = f"{expr} = {result.value_num}"
        msg = _with_field(msg, "equivalence", text(equivalence_text))
        state.isr.context.append(msg)
        state.isr.quality = min(1.0, state.isr.quality + 0.03)


def phi_determine(state: MetaState, args: tuple[Node, ...]) -> None:
    if not args:
        return
    msg = args[0]
    if msg.kind is not NodeKind.STRUCT:
        return

    semantics = _field(msg, "semantics")
    semantic_kind = _as_text(semantics.fields.get("semantic_kind")) if semantics else ""

    intent = _as_text(_field(msg, "intent"))
    if semantic_kind == "code_snippet":
        mode = "explain_code"
    elif semantic_kind == "math_question":
        mode = "math_answer"
    elif intent == "greeting":
        mode = "greeting"
    elif intent == "command":
        mode = "command"
    elif intent == "question":
        mode = "qa"
    else:
        mode = "ack"

    msg = _with_field(msg, "response_mode", text(mode))
    state.isr.context.append(msg)
    state.isr.quality = min(1.0, state.isr.quality + 0.02)


def phi_answer(state: MetaState, args: tuple[Node, ...]) -> None:
    msg = args[0] if args else None
    if msg is None or msg.kind is not NodeKind.STRUCT:
        state.isr.answer = struct(answer=text("[META] Entrada desconhecida."))
        return

    lang = _guess_lang(msg)
    semantics = _field(msg, "semantics")
    semantic_kind = _as_text(semantics.fields.get("semantic_kind")) if semantics else ""
    semantic_cost = 0.0
    if semantics:
        cost_node = semantics.fields.get("semantic_cost")
        if cost_node and cost_node.kind is NodeKind.NUMBER and cost_node.value_num is not None:
            semantic_cost = float(cost_node.value_num)

    response_mode = _as_text(_field(msg, "response_mode"))
    intent = _as_text(_field(msg, "intent"))
    preview = _preview_text(msg)
    calculus = _field(msg, "calculus")

    if _is_code_snippet(msg):
        ast_node = _field(msg, "structure") or _field(msg, "ast")
        if ast_node:
            ans_text = (
                "Recebi um trecho de código e o representei em LIU. Posso compará-lo ou otimizá-lo em seguida."
                if lang == "pt"
                else "I received a code snippet and mapped it into LIU. I can compare or optimize it next."
            )
        else:
            ans_text = (
                "Recebi um código, mas não consegui analisá-lo completamente."
                if lang == "pt"
                else "I received code, but could not fully analyse it."
            )
        state.isr.answer = struct(answer=text(ans_text))
        state.isr.quality = min(1.0, state.isr.quality + 0.05)
        return

    if calculus is not None and calculus.kind is NodeKind.STRUCT:
        solved = _as_text(calculus.fields.get("solved")) == "true"
        expr = _as_text(calculus.fields.get("expression"))
        result = calculus.fields.get("result")
        if solved and result and result.kind is NodeKind.NUMBER and result.value_num is not None:
            value = float(result.value_num)
            value_str = str(int(value)) if value.is_integer() else str(value)
            if lang == "pt":
                ans_text = f"O resultado é {value_str} para {expr}."
            else:
                ans_text = f"The result is {value_str} for {expr}."
            state.isr.answer = struct(answer=text(ans_text))
            state.isr.quality = min(1.0, state.isr.quality + 0.15)
            return

    if response_mode == "greeting":
        ans_text = "Olá! Sou o Metanúcleo determinístico. Prazer em te ouvir."
    elif response_mode == "command":
        ans_text = (
            "Entendi isso como um comando. Vou tratar a instrução de forma determinística."
            if lang == "pt"
            else "I understood that as a command. I'll treat the instruction deterministically."
        )
    elif intent == "question" or response_mode == "qa":
        short = " ".join(_token_list(_field(msg, "tokens"))[:10])
        if semantic_kind == "math_question":
            ans_text = (
                f"Entendi que é uma pergunta matemática sobre \"{short}\". Estou analisando a expressão."
                if lang == "pt"
                else f"I see this is a math question about \"{short}\". I'm analysing the expression."
            )
        elif semantic_cost >= 20:
            ans_text = (
                f"Pergunta complexa registrada: \"{short}\". Vou decompô-la em partes menores."
                if lang == "pt"
                else f"Complex question captured: \"{short}\". I'll decompose it internally."
            )
        else:
            ans_text = (
                f"Pergunta registrada: \"{short}\"."
                if lang == "pt"
                else f"Question registered: \"{short}\"."
            )
    elif intent == "greeting":
        ans_text = "Olá! Sou o Metanúcleo determinístico. Prazer em te ouvir."
    else:
        ans_text = f"[META] Recebi: {preview}. Estou processando simbolicamente."

    state.isr.answer = struct(answer=text(ans_text))
    state.isr.quality = min(1.0, state.isr.quality + 0.08)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _field(node: Node, name: str) -> Optional[Node]:
    if node.kind is NodeKind.STRUCT:
        return node.fields.get(name)
    return None


def _with_field(node: Node, name: str, value: Node) -> Node:
    if node.kind is not NodeKind.STRUCT:
        return node
    node.fields[name] = value
    return node


def _as_text(node: Optional[Node]) -> str:
    if node is None:
        return ""
    if node.kind is NodeKind.TEXT and node.label:
        return node.label
    if node.kind is NodeKind.NUMBER and node.value_num is not None:
        return str(node.value_num)
    return ""


def _content_text(msg: Optional[Node]) -> str:
    if msg is None:
        return ""
    if msg.kind is NodeKind.STRUCT:
        for key in ("content", "raw"):
            candidate = msg.fields.get(key)
            if candidate and candidate.kind is NodeKind.TEXT and candidate.label:
                return candidate.label
    if msg.kind is NodeKind.TEXT and msg.label:
        return msg.label
    if msg.label:
        return msg.label
    return ""


def _guess_lang(msg: Node) -> str:
    lang_field = _field(msg, "lang")
    lang = _as_text(lang_field)
    if lang:
        return lang.lower()
    raw = _content_text(msg).lower()
    if any(ch in raw for ch in "ãõáéíóúâêôç"):
        return "pt"
    return "en"


def _token_list(tokens_node: Optional[Node]) -> List[str]:
    if tokens_node is None or tokens_node.kind is not NodeKind.STRUCT:
        return []
    tokens: List[str] = []
    for entry in tokens_node.fields.values():
        if entry.kind is NodeKind.STRUCT:
            surf = entry.fields.get("surface")
            if surf and surf.kind is NodeKind.TEXT and surf.label:
                tokens.append(surf.label)
    return tokens


def _preview_text(msg: Node, limit: int = 60) -> str:
    text_value = _content_text(msg)
    if not text_value:
        return "entrada desconhecida"
    return text_value if len(text_value) <= limit else text_value[: limit - 3] + "..."


def _detect_logic_ops(tokens: Iterable[str], lang: str) -> List[str]:
    lowered = [tok.lower() for tok in tokens]
    ops = []
    if lang == "en":
        if "and" in lowered:
            ops.append("AND")
        if "or" in lowered:
            ops.append("OR")
        if "not" in lowered:
            ops.append("NOT")
        if "if" in lowered:
            ops.append("IF")
        if "then" in lowered:
            ops.append("THEN")
    else:
        if "e" in lowered:
            ops.append("AND")
        if "ou" in lowered:
            ops.append("OR")
        if "não" in lowered or "nao" in lowered:
            ops.append("NOT")
        if "se" in lowered:
            ops.append("IF")
        if "então" in lowered or "entao" in lowered:
            ops.append("THEN")
    return ops


def _list_node(items: Iterable[Node]) -> Node:
    return Node(kind=NodeKind.LIST, args=list(items))


def _is_code_snippet(msg: Node) -> bool:
    kind_field = _field(msg, "kind")
    return bool(kind_field and kind_field.kind is NodeKind.TEXT and kind_field.label == "code_snippet")


def _node_complexity(node: Node) -> int:
    if node.kind in {NodeKind.TEXT, NodeKind.NUMBER, NodeKind.BOOL, NodeKind.NIL}:
        return 1
    if node.kind in {NodeKind.LIST, NodeKind.REL, NodeKind.OP}:
        return 1 + sum(_node_complexity(child) for child in node.args)
    if node.kind is NodeKind.STRUCT:
        return 1 + sum(_node_complexity(child) for child in node.fields.values())
    return 1


def _extract_math_expr(raw: str) -> str:
    digits = [idx for idx, ch in enumerate(raw) if ch.isdigit()]
    if not digits:
        return ""
    first, last = digits[0], digits[-1]
    if first >= last:
        return ""
    snippet = raw[first : last + 1]
    allowed = set("0123456789+-*/().,% ")
    cleaned = "".join(ch for ch in snippet if ch in allowed)
    return cleaned.strip()


_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _safe_eval_math(expr: str) -> float:
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ValueError("expressão inválida") from exc

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Num):
            return float(node.n)
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in _BIN_OPS:
                raise ValueError("operador não permitido")
            return float(_BIN_OPS[op_type](_eval(node.left), _eval(node.right)))
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in _UNARY_OPS:
                raise ValueError("operador unário não permitido")
            return float(_UNARY_OPS[op_type](_eval(node.operand)))
        raise ValueError("nó não suportado")

    return _eval(tree.body)  # type: ignore[arg-type]
