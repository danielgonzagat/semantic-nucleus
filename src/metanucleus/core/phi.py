"""
Operadores Φ determinísticos (versão mínima).
"""

from __future__ import annotations

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

    isr = state.isr

    if semantic_kind == "math_question":
        ans_text = f"Analisei sua expressão; trata-se de uma questão matemática: {preview}"
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
