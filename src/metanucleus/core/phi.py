"""
Operadores Φ determinísticos (versão mínima).
"""

from __future__ import annotations

from typing import Tuple

from .liu import Node, NodeKind, struct, text
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


def phi_answer(state: MetaState, args: Tuple[Node, ...]) -> None:
    """
    Produz uma resposta textual determinística baseada no último input.
    """

    msg = args[0] if args else None
    preview = _extract_preview(msg) if msg is not None else "entrada desconhecida"
    intent = ""
    if msg and msg.kind is NodeKind.STRUCT:
        intent_node = msg.fields.get("intent")
        if intent_node and intent_node.kind is NodeKind.TEXT:
            intent = intent_node.label or ""
    isr = state.isr

    if intent == "greeting":
        ans_text = "Olá! Sou o Metanúcleo determinístico. Prazer em te ouvir."
    elif intent == "question":
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
