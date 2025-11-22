"""
Operadores Φ determinísticos (versão mínima).
"""

from __future__ import annotations

from typing import Tuple

from .liu import Node, NodeKind, op, struct, text
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


def phi_answer(state: MetaState, args: Tuple[Node, ...]) -> None:
    """
    Produz uma resposta textual determinística baseada no último input.
    """

    if not args:
        preview = "entrada desconhecida"
    else:
        msg = args[0]
        preview = _extract_preview(msg)
    isr = state.isr
    response = struct(
        answer=text(f"[META] Recebi: {preview}. Estou processando simbolicamente."),
    )
    isr.answer = response
    isr.quality = min(1.0, isr.quality + 0.2)


def _extract_preview(msg: Node) -> str:
    if msg.kind is NodeKind.STRUCT:
        content = msg.fields.get("content") or msg.fields.get("raw")
        if content and content.kind is NodeKind.TEXT and content.label:
            return content.label if len(content.label) <= 60 else content.label[:57] + "..."
    if msg.kind is NodeKind.TEXT and msg.label:
        return msg.label if len(msg.label) <= 60 else msg.label[:57] + "..."
    if msg.label:
        return msg.label
    return msg.kind.name.lower()
