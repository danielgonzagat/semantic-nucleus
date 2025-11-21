"""
Estruturas auxiliares para expor a equação LIU produzida pelo NSR.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import blake2b
from typing import Dict, Iterable, Tuple

from liu import Node, struct
from liu.hash import fingerprint
from liu.serialize import to_json, to_sexpr

from .state import ISR


def _node_json(node: Node) -> Dict:
    return json.loads(to_json(node))


def _nodes_digest(nodes: Iterable[Node]) -> str:
    fingerprints = [fingerprint(node) for node in nodes]
    return ",".join(fingerprints) or "-"


@dataclass(slots=True)
class EquationSnapshot:
    """
    Representa a “equação semântica” corrente do NSR.

    - `input_struct`: LIU derivado do texto de entrada.
    - `ontology`: fatos estáticos carregados para o ISR.
    - `relations`: fatos e inferências que compõem o grafo dinâmico.
    - `context`: pilha de focos atuais.
    - `goals`: fila de objetivos determinísticos.
    - `ops_queue`: fila de operadores Φ prontos para execução.
    - `answer`: struct com o campo `answer`.
    - `quality`: escalar ∈ [0,1] indicando convergência atual.
    """

    input_struct: Node
    ontology: Tuple[Node, ...]
    relations: Tuple[Node, ...]
    context: Tuple[Node, ...]
    goals: Tuple[Node, ...]
    ops_queue: Tuple[Node, ...]
    answer: Node
    quality: float

    def digest(self) -> str:
        """
        Retorna o hash determinístico dos componentes (128 bits, Blake2b).
        """

        payload = "|".join(
            (
                f"in:{fingerprint(self.input_struct)}",
                f"ont:{_nodes_digest(self.ontology)}",
                f"rels:{_nodes_digest(self.relations)}",
                f"ctx:{_nodes_digest(self.context)}",
                f"goals:{_nodes_digest(self.goals)}",
                f"ops:{_nodes_digest(self.ops_queue)}",
                f"ans:{fingerprint(self.answer)}",
                f"q:{self.quality:.6f}",
            )
        )
        return blake2b(payload.encode("utf-8"), digest_size=16).hexdigest()

    def to_sexpr_bundle(self) -> Dict[str, object]:
        """Serializa cada componente em S-expr para auditoria humana."""

        return {
            "input": to_sexpr(self.input_struct),
            "ontology": [to_sexpr(node) for node in self.ontology],
            "relations": [to_sexpr(node) for node in self.relations],
            "context": [to_sexpr(node) for node in self.context],
            "goals": [to_sexpr(node) for node in self.goals],
            "ops_queue": [to_sexpr(node) for node in self.ops_queue],
            "answer": to_sexpr(self.answer),
            "quality": f"{self.quality:.6f}",
        }

    def to_json_bundle(self) -> Dict[str, object]:
        """Serializa componentes em JSON determinístico para consumo de máquinas."""

        return {
            "input": _node_json(self.input_struct),
            "ontology": [_node_json(node) for node in self.ontology],
            "relations": [_node_json(node) for node in self.relations],
            "context": [_node_json(node) for node in self.context],
            "goals": [_node_json(node) for node in self.goals],
            "ops_queue": [_node_json(node) for node in self.ops_queue],
            "answer": _node_json(self.answer),
            "quality": self.quality,
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
        ontology=isr.ontology,
        relations=isr.relations,
        context=isr.context,
        goals=tuple(isr.goals),
        ops_queue=tuple(isr.ops_queue),
        answer=isr.answer,
        quality=isr.quality,
    )


__all__ = ["EquationSnapshot", "snapshot_equation"]
