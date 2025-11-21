"""
Estruturas auxiliares para expor a equação LIU produzida pelo NSR.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import blake2b
from typing import Dict, Tuple

from liu import Node, struct
from liu.hash import fingerprint
from liu.serialize import to_json, to_sexpr

from .state import ISR


def _node_json(node: Node) -> Dict:
    return json.loads(to_json(node))


@dataclass(slots=True)
class EquationSnapshot:
    """
    Representa a “equação semântica” corrente do NSR.

    - `input_struct`: LIU derivado do texto de entrada.
    - `relations`: fatos e inferências que compõem o grafo.
    - `context`: pilha de focos atuais.
    - `answer`: struct com o campo `answer`.
    """

    input_struct: Node
    relations: Tuple[Node, ...]
    context: Tuple[Node, ...]
    answer: Node

    def digest(self) -> str:
        """
        Retorna o hash determinístico dos componentes (128 bits, Blake2b).
        """

        payload = "|".join(
            (
                f"in:{fingerprint(self.input_struct)}",
                f"rels:{','.join(fingerprint(node) for node in self.relations) or '-'}",
                f"ctx:{','.join(fingerprint(node) for node in self.context) or '-'}",
                f"ans:{fingerprint(self.answer)}",
            )
        )
        return blake2b(payload.encode("utf-8"), digest_size=16).hexdigest()

    def to_sexpr_bundle(self) -> Dict[str, object]:
        """Serializa cada componente em S-expr para auditoria humana."""

        return {
            "input": to_sexpr(self.input_struct),
            "relations": [to_sexpr(node) for node in self.relations],
            "context": [to_sexpr(node) for node in self.context],
            "answer": to_sexpr(self.answer),
        }

    def to_json_bundle(self) -> Dict[str, object]:
        """Serializa componentes em JSON determinístico para consumo de máquinas."""

        return {
            "input": _node_json(self.input_struct),
            "relations": [_node_json(node) for node in self.relations],
            "context": [_node_json(node) for node in self.context],
            "answer": _node_json(self.answer),
        }


def snapshot_equation(struct_node: Node | None, isr: ISR) -> EquationSnapshot:
    """
    Constrói um `EquationSnapshot` a partir do estado atual.

    Quando `struct_node` não é informado (por exemplo, execuções iniciadas
    diretamente por `run_struct_full`), usamos um struct vazio para manter
    a consistência da interface.
    """

    base_struct = struct_node if struct_node is not None else struct()
    return EquationSnapshot(
        input_struct=base_struct,
        relations=isr.relations,
        context=isr.context,
        answer=isr.answer,
    )


__all__ = ["EquationSnapshot", "snapshot_equation"]
