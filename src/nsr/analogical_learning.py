"""
Aprendizado por Analogia: Aprende novos padrões por analogia com padrões conhecidos.

Se A é como B, e sabemos que B tem propriedade X, então A provavelmente tem X também.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from liu import Node, NodeKind, fingerprint, relation

from .structural_alignment import StructuralAligner, Alignment
from .weightless_types import Episode


@dataclass(frozen=True, slots=True)
class Analogy:
    """Analogia entre dois pares de conceitos."""
    
    source_pair: Tuple[Node, Node]  # (A, B)
    target_pair: Tuple[Node, Node]  # (C, D)
    similarity: float
    mapping: Dict[str, str]  # Mapeia A→C, B→D


class AnalogicalLearner:
    """
    Aprende por analogia: se A:B então C:D.
    
    Exemplo:
    - Conhece: "carro tem rodas"
    - Vê: "bicicleta tem pedais"
    - Aprende analogia: veiculo tem parte
    - Aplica: "avião tem asas" (novo veiculo, nova parte)
    """
    
    def __init__(self):
        self.aligner = StructuralAligner()
        self.analogies: List[Analogy] = []
    
    def find_analogy(
        self, known_pair: Tuple[Node, Node], new_pair: Tuple[Node, Node]
    ) -> Analogy | None:
        """Encontra analogia entre dois pares."""
        
        # Alinha primeiro elemento
        align1 = self.aligner.align(known_pair[0], new_pair[0])
        if not align1 or align1.similarity < 0.5:
            return None
        
        # Alinha segundo elemento
        align2 = self.aligner.align(known_pair[1], new_pair[1])
        if not align2 or align2.similarity < 0.5:
            return None
        
        # Similaridade média
        similarity = (align1.similarity + align2.similarity) / 2.0
        
        # Combina mapeamentos
        mapping = {**align1.mappings, **align2.mappings}
        
        analogy = Analogy(
            source_pair=known_pair,
            target_pair=new_pair,
            similarity=similarity,
            mapping=mapping,
        )
        
        self.analogies.append(analogy)
        return analogy
    
    def apply_analogy(
        self, analogy: Analogy, new_concept: Node
    ) -> List[Node] | None:
        """
        Aplica analogia para inferir propriedades de novo conceito.
        
        Se sabemos que A tem propriedade X, e C é análogo a A,
        então C provavelmente tem propriedade análoga a X.
        """
        
        # Encontra conceito análogo na analogia
        source_A, source_B = analogy.source_pair
        
        # Verifica se new_concept é análogo a source_A
        alignment = self.aligner.align(source_A, new_concept)
        if not alignment or alignment.similarity < 0.5:
            return None
        
        # Se source_A tem propriedade source_B, new_concept deve ter propriedade análoga
        # Retorna propriedade inferida
        # Simplificação: retorna estrutura similar a source_B
        return [source_B]  # Em produção, generalizaria baseado no mapeamento
    
    def learn_from_episodes(self, episodes: List[Episode]) -> List[Node]:
        """
        Aprende analogias de uma lista de episódios.
        
        Encontra pares de episódios que formam analogias.
        """
        learned_relations: List[Node] = []
        
        # Compara todos os pares de episódios
        for i in range(len(episodes)):
            for j in range(i + 1, len(episodes)):
                ep1 = episodes[i]
                ep2 = episodes[j]
                
                # Extrai relações principais
                rel1 = ep1.relations[0] if ep1.relations else None
                rel2 = ep2.relations[0] if ep2.relations else None
                
                if not rel1 or not rel2:
                    continue
                
                # Se relações têm mesma estrutura mas entidades diferentes
                if rel1.label == rel2.label and len(rel1.args) == 2 and len(rel2.args) == 2:
                    # Cria par de analogia
                    pair1 = (rel1.args[0], rel1.args[1])
                    pair2 = (rel2.args[0], rel2.args[1])
                    
                    analogy = self.find_analogy(pair1, pair2)
                    if analogy and analogy.similarity > 0.6:
                        # Aprende relação generalizada
                        # Se carro:rodas e bicicleta:pedais, aprende veiculo:parte
                        generalized = self._generalize_from_analogy(analogy)
                        if generalized:
                            learned_relations.append(generalized)
        
        return learned_relations
    
    def _generalize_from_analogy(self, analogy: Analogy) -> Node | None:
        """Generaliza analogia em relação."""
        from liu import var
        
        # Simplificação: cria relação generalizada
        # Em produção, usaria hierarquia de abstração
        source_A, source_B = analogy.source_pair
        
        # Cria relação generalizada: ?X tem ?Y
        return relation("HAS", var("?X"), var("?Y"))


__all__ = ["Analogy", "AnalogicalLearner"]
