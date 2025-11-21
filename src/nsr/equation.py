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


def _truncate(text: str, limit: int = 160) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _format_section(label: str, nodes: Tuple[Node, ...], max_items: int) -> str:
    total = len(nodes)
    if total == 0:
        return f"{label}[0]: —"
    max_items = max(1, max_items)
    preview = [_truncate(to_sexpr(node)) for node in nodes[:max_items]]
    if total > max_items:
        preview.append(f"...(+{total - max_items})")
    joined = "; ".join(preview)
    return f"{label}[{total}]: {joined}"


@dataclass(slots=True)
class SectionStats:
    count: int
    digest: str

    def to_dict(self) -> Dict[str, object]:
        return {"count": self.count, "digest": self.digest}


@dataclass(slots=True)
class EquationSnapshotStats:
    input_digest: str
    ontology: SectionStats
    relations: SectionStats
    context: SectionStats
    goals: SectionStats
    ops_queue: SectionStats
    answer_digest: str
    quality: float
    equation_digest: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "input_digest": self.input_digest,
            "ontology": self.ontology.to_dict(),
            "relations": self.relations.to_dict(),
            "context": self.context.to_dict(),
            "goals": self.goals.to_dict(),
            "ops_queue": self.ops_queue.to_dict(),
            "answer_digest": self.answer_digest,
            "quality": self.quality,
            "equation_digest": self.equation_digest,
        }


def _section_stats(nodes: Tuple[Node, ...]) -> SectionStats:
    return SectionStats(count=len(nodes), digest=_nodes_digest(nodes))


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

    def to_text_report(self, *, max_items: int = 6) -> str:
        """
        Converte a equação LIU em um relatório textual determinístico.

        O relatório resume cada componente (ontologia, relações, fila Φ, etc.)
        usando S-expr truncadas para inspeção humana rápida.
        """

        max_items = max(1, max_items)
        lines = [
            "Equação LIU — relatório determinístico",
            f"Entrada: {to_sexpr(self.input_struct)}",
            f"Resposta: {to_sexpr(self.answer)}",
            f"Qualidade: {self.quality:.4f}",
            _format_section("Ontologia", self.ontology, max_items),
            _format_section("Relações", self.relations, max_items),
            _format_section("Contexto", self.context, max_items),
            _format_section("Goals", self.goals, max_items),
            _format_section("FilaΦ", self.ops_queue, max_items),
        ]
        return "\n".join(lines)

    def stats(self) -> EquationSnapshotStats:
        """
        Retorna contagens e digests determinísticos para auditoria estrutural.
        """

        return EquationSnapshotStats(
            input_digest=fingerprint(self.input_struct),
            ontology=_section_stats(self.ontology),
            relations=_section_stats(self.relations),
            context=_section_stats(self.context),
            goals=_section_stats(self.goals),
            ops_queue=_section_stats(self.ops_queue),
            answer_digest=fingerprint(self.answer),
            quality=self.quality,
            equation_digest=self.digest(),
        )


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


__all__ = ["EquationSnapshot", "EquationSnapshotStats", "snapshot_equation"]
