"""
Hierarquias de Abstração: Sistema de Generalização Multi-Nível.

Permite generalização através de múltiplos níveis de abstração,
substituindo conceitos específicos por conceitos mais genéricos.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from liu import Node, NodeKind, entity, fingerprint, var


@dataclass(frozen=True)
class AbstractionLevel:
    """Nível de abstração na hierarquia."""
    
    level: int  # 0 = mais específico, maior = mais genérico
    concept: str
    parent: str | None = None
    children: Tuple[str, ...] = tuple()


class AbstractionHierarchy:
    """
    Hierarquia de abstração para generalização.
    
    Exemplo:
    - Nível 0: "carro_vermelho", "carro_azul"
    - Nível 1: "carro"
    - Nível 2: "veiculo"
    - Nível 3: "objeto"
    """
    
    def __init__(self):
        # Mapeia conceito -> nível
        self.concept_levels: Dict[str, int] = {}
        
        # Mapeia conceito -> parent
        self.concept_parents: Dict[str, str | None] = {}
        
        # Mapeia parent -> children
        self.parent_children: Dict[str, List[str]] = defaultdict(list)
        
        # Hierarquia IS_A do grafo semântico
        self._build_from_ontology()
    
    def _build_from_ontology(self) -> None:
        """Constrói hierarquia a partir de relações IS_A na ontologia."""
        # Por enquanto, hierarquia básica
        # Em produção, extrairia do grafo semântico
        
        # Nível 0: específico
        # Nível 1: categoria
        # Nível 2: super-categoria
        # Nível 3: genérico
        
        basic_hierarchy = {
            "coisa": (3, None),
            "objeto": (2, "coisa"),
            "veiculo": (1, "objeto"),
            "carro": (0, "veiculo"),
            "bicicleta": (0, "veiculo"),
            "animal": (1, "objeto"),
            "cachorro": (0, "animal"),
            "gato": (0, "animal"),
        }
        
        for concept, (level, parent) in basic_hierarchy.items():
            self.concept_levels[concept] = level
            self.concept_parents[concept] = parent
            if parent:
                self.parent_children[parent].append(concept)
    
    def generalize(
        self, node: Node, target_level: int = 1
    ) -> Node:
        """
        Generaliza um nó subindo na hierarquia de abstração.
        
        target_level: nível alvo de abstração (0-3)
        """
        if node.kind is NodeKind.ENTITY and node.label:
            concept = node.label.lower()
            current_level = self.concept_levels.get(concept, 0)
            
            if current_level < target_level:
                # Sobe na hierarquia
                parent = self.concept_parents.get(concept)
                if parent:
                    return entity(parent)
                # Se não tem parent, usa variável
                return var("?X")
            
            return node
        
        if node.kind is NodeKind.REL:
            # Generaliza argumentos
            generalized_args = tuple(
                self.generalize(arg, target_level) for arg in node.args
            )
            return Node(
                kind=NodeKind.REL,
                label=node.label,
                args=generalized_args,
                fields=node.fields,
                value=node.value,
            )
        
        if node.kind is NodeKind.STRUCT:
            # Generaliza campos
            generalized_fields = tuple(
                (k, self.generalize(v, target_level)) for k, v in node.fields
            )
            return Node(
                kind=NodeKind.STRUCT,
                label=node.label,
                args=node.args,
                fields=generalized_fields,
                value=node.value,
            )
        
        # Para outros tipos, generaliza argumentos
        generalized_args = tuple(
            self.generalize(arg, target_level) for arg in node.args
        )
        return Node(
            kind=node.kind,
            label=node.label,
            args=generalized_args,
            fields=node.fields,
            value=node.value,
        )
    
    def find_common_ancestor(self, concept1: str, concept2: str) -> str | None:
        """Encontra ancestral comum de dois conceitos."""
        # Sobe hierarquia de ambos até encontrar comum
        path1 = self._get_path_to_root(concept1)
        path2 = self._get_path_to_root(concept2)
        
        # Encontra primeiro comum
        for c1 in path1:
            if c1 in path2:
                return c1
        
        return None
    
    def _get_path_to_root(self, concept: str) -> List[str]:
        """Retorna caminho do conceito até raiz."""
        path = [concept]
        current = concept
        
        while current in self.concept_parents:
            parent = self.concept_parents[current]
            if parent is None:
                break
            path.append(parent)
            current = parent
        
        return path
    
    def add_concept(
        self, concept: str, level: int, parent: str | None = None
    ) -> None:
        """Adiciona novo conceito à hierarquia."""
        self.concept_levels[concept] = level
        self.concept_parents[concept] = parent
        if parent:
            self.parent_children[parent].append(concept)


def build_abstraction_hierarchy_from_graph(graph) -> AbstractionHierarchy:
    """
    Constrói hierarquia de abstração a partir de grafo semântico.
    
    Extrai relações IS_A e constrói hierarquia multi-nível.
    """
    hierarchy = AbstractionHierarchy()
    
    # Por enquanto, usa hierarquia básica
    # Em produção, extrairia do grafo
    
    return hierarchy


__all__ = [
    "AbstractionLevel",
    "AbstractionHierarchy",
    "build_abstraction_hierarchy_from_graph",
]
