"""
Módulo de Resolução de Ambiguidade Determinística.
Utiliza o Grafo Semântico para calcular a "densidade semântica" de interpretações concorrentes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Dict

from liu import Node, NodeKind, fingerprint, entity, relation, struct, number
from nsr.semantic_graph import SemanticGraph
from nsr.state import ISR


@dataclass(frozen=True)
class Interpretation:
    """Uma interpretação possível para um termo ou estrutura ambígua."""
    label: str
    score: float
    evidence: List[Node]
    meaning_node: Node  # O nó que representa este significado específico


class AmbiguityResolver:
    """
    Resolve ambiguidades medindo a coerência de cada significado candidato
    com o contexto atual (grafo + memória de trabalho).
    """

    def __init__(self, graph: SemanticGraph):
        self.graph = graph

    def resolve(self, ambiguous_term: str, candidates: List[Node], context_nodes: Tuple[Node, ...]) -> List[Interpretation]:
        """
        Dada uma lista de candidatos (nós que representam significados distintos para o mesmo termo),
        calcula um score de coerência para cada um baseada na conectividade com o contexto.
        """
        interpretations = []

        # O contexto relevante são as entidades presentes na memória de trabalho recente
        context_entities = [n for n in context_nodes if n.kind == NodeKind.ENTITY]

        for cand in candidates:
            score = 0.0
            evidence = []

            # 1. Conectividade Direta no Grafo (Densidade Semântica)
            # Se o candidato tem relação direta com algo no contexto, aumenta muito o score.
            neighbors = self.graph.get_neighbors(cand, direction="both")
            neighbor_fps = {fingerprint(n) for n in neighbors}

            for ctx_entity in context_entities:
                if fingerprint(ctx_entity) in neighbor_fps:
                    score += 1.0
                    evidence.append(relation("CONNECTED_TO", cand, ctx_entity))

            # 2. Distância Taxonômica (Coerência de Domínio)
            # Se o candidato compartilha ancestrais comuns (IS_A) com o contexto, aumenta score.
            # Ex: "Banco" (instituição) combina com "Dinheiro" (ambos sob Conceitos Financeiros? ou uso?)
            # Para simplificar e manter determinismo rápido: verificamos se compartilham 'categoria pai' imediata.
            cand_parents = self.graph.get_neighbors(cand, rel_type="IS_A", direction="out")
            cand_parent_fps = {fingerprint(p) for p in cand_parents}
            
            for ctx_entity in context_entities:
                ctx_parents = self.graph.get_neighbors(ctx_entity, rel_type="IS_A", direction="out")
                for p in ctx_parents:
                    if fingerprint(p) in cand_parent_fps:
                        score += 0.5
                        evidence.append(relation("SHARED_CATEGORY", cand, p))

            # 3. Prioridade Base (Heurística Estática)
            # Poderíamos ter um peso "base" na ontologia, mas por enquanto assumimos 0.1 para desempate
            score += 0.1

            interpretations.append(Interpretation(
                label=cand.label or "unknown",
                score=score,
                evidence=evidence,
                meaning_node=cand
            ))

        # Ordenação determinística: Score desc, depois Label asc
        interpretations.sort(key=lambda x: (-x.score, x.label))
        return interpretations


def detect_ambiguity(isr: ISR) -> List[Tuple[str, List[Node]]]:
    """
    Detecta termos no contexto que possuem múltiplos significados conhecidos no grafo
    mas que ainda não foram resolvidos (ancorados).
    
    NOTA: Em um sistema real, isso exigiria um índice reverso de "lexema -> [nós de sentido]".
    Para este passo, simulamos detectando nós especiais marcados como AMBIGUOUS.
    """
    detected = []
    for node in isr.context:
        if node.kind == NodeKind.STRUCT:
            # Procura por structs marcadas como ambiguidade explícita
            # Ex: struct(tag=entity("AMBIGUOUS_TERM"), term="manga", candidates=list(...))
            fields = dict(node.fields)
            tag = fields.get("tag")
            if tag and (tag.label == "AMBIGUOUS_TERM"):
                term = fields.get("term")
                candidates_list = fields.get("candidates")
                if term and candidates_list and candidates_list.kind == NodeKind.LIST:
                    term_str = term.label or ""
                    # Filtra apenas ENTITYs como candidatos
                    cands = [c for c in candidates_list.args if c.kind == NodeKind.ENTITY]
                    if cands:
                        detected.append((term_str, cands))
    return detected
