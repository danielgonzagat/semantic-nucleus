"""
Renderizador determinístico de respostas.
"""

from __future__ import annotations

from dataclasses import dataclass

from metanucleus.core.liu import NodeKind
from metanucleus.core.state import MetaState


@dataclass()
class OutputRenderer:
    def render(self, state: MetaState) -> str:
        answer = state.isr.answer
        if answer.kind is NodeKind.STRUCT and "answer" in answer.fields:
            node = answer.fields["answer"]
            if node.kind is NodeKind.TEXT and node.label:
                return node.label
        if answer.kind is NodeKind.TEXT and answer.label:
            return answer.label
        return "[META] Ainda sem resposta simbólica."
