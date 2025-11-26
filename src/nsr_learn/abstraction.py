"""
Abstração Hierárquica: Generalização Multinível Sem Pesos Neurais.

Humanos pensam em múltiplos níveis de abstração:
- "Cachorro" é mais específico que "animal"
- "Correr" é mais específico que "mover"
- "2+2=4" é uma instância de "aritmética"

Em LLMs, hierarquias emergem implicitamente nos embeddings.
Aqui, implementamos EXPLICITAMENTE através de:

1. TAXONOMIAS: Hierarquias IS-A (cachorro IS-A animal)
2. PARTONIMIAS: Hierarquias PART-OF (roda PART-OF carro)
3. ABSTRAÇÃO DE PADRÕES: "a+a" → "2a" (compressão)
4. COMPOSIÇÃO DE CONCEITOS: Conceitos complexos de simples

Benefícios:
- Generalização: Transferir conhecimento para novos casos
- Compressão: Representar muito com pouco
- Raciocínio: Herdar propriedades de classes superiores
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any, Callable, Dict, FrozenSet, Iterator, List, 
    Mapping, Set, Tuple, TypeVar, Generic
)


T = TypeVar("T")


class RelationType(Enum):
    """Tipos de relações hierárquicas."""
    
    IS_A = auto()  # Taxonomia: cachorro IS_A animal
    PART_OF = auto()  # Partonimia: roda PART_OF carro
    INSTANCE_OF = auto()  # Instância: Rex INSTANCE_OF cachorro
    CAUSES = auto()  # Causalidade: fogo CAUSES calor
    PRECEDES = auto()  # Temporal: nascer PRECEDES morrer
    SIMILAR_TO = auto()  # Similaridade: gato SIMILAR_TO cachorro


@dataclass(frozen=True, slots=True)
class Concept:
    """Um conceito na hierarquia."""
    
    name: str
    level: int  # 0 = mais abstrato, maior = mais concreto
    properties: FrozenSet[str] = frozenset()
    
    def __str__(self) -> str:
        return f"{self.name}[L{self.level}]"
    
    def has_property(self, prop: str) -> bool:
        return prop in self.properties


@dataclass(frozen=True, slots=True)
class HierarchicalRelation:
    """Uma relação hierárquica entre conceitos."""
    
    source: str  # Nome do conceito fonte
    relation: RelationType
    target: str  # Nome do conceito alvo
    strength: float = 1.0
    
    def __str__(self) -> str:
        return f"{self.source} --{self.relation.name}--> {self.target}"


@dataclass
class ConceptNode:
    """Nó em uma hierarquia de conceitos."""
    
    concept: Concept
    parents: Set[str] = field(default_factory=set)  # Conceitos mais abstratos
    children: Set[str] = field(default_factory=set)  # Conceitos mais concretos
    instances: Set[str] = field(default_factory=set)  # Instâncias concretas
    parts: Set[str] = field(default_factory=set)  # Partes componentes
    
    def all_parents(self) -> Set[str]:
        """Retorna pais diretos."""
        return self.parents.copy()
    
    def all_children(self) -> Set[str]:
        """Retorna filhos diretos."""
        return self.children.copy()


class Taxonomy:
    """
    Taxonomia: Hierarquia IS-A de conceitos.
    
    Exemplo:
        ENTIDADE (L0)
        ├── SER_VIVO (L1)
        │   ├── ANIMAL (L2)
        │   │   ├── MAMIFERO (L3)
        │   │   │   ├── CACHORRO (L4)
        │   │   │   └── GATO (L4)
        │   │   └── AVE (L3)
        │   └── PLANTA (L2)
        └── OBJETO (L1)
    """
    
    def __init__(self):
        self.concepts: Dict[str, Concept] = {}
        self.nodes: Dict[str, ConceptNode] = {}
        self.root_concepts: Set[str] = set()
    
    def add_concept(
        self,
        name: str,
        level: int = 0,
        properties: Set[str] | None = None,
    ) -> Concept:
        """Adiciona um conceito à taxonomia."""
        props = frozenset(properties) if properties else frozenset()
        concept = Concept(name=name, level=level, properties=props)
        
        self.concepts[name] = concept
        self.nodes[name] = ConceptNode(concept=concept)
        
        return concept
    
    def add_relation(
        self,
        child_name: str,
        parent_name: str,
        relation_type: RelationType = RelationType.IS_A,
    ) -> None:
        """Adiciona relação entre conceitos."""
        if child_name not in self.nodes:
            self.add_concept(child_name)
        
        if parent_name not in self.nodes:
            self.add_concept(parent_name)
        
        child_node = self.nodes[child_name]
        parent_node = self.nodes[parent_name]
        
        if relation_type == RelationType.IS_A:
            child_node.parents.add(parent_name)
            parent_node.children.add(child_name)
        elif relation_type == RelationType.PART_OF:
            parent_node.parts.add(child_name)
        elif relation_type == RelationType.INSTANCE_OF:
            parent_node.instances.add(child_name)
    
    def get_ancestors(self, name: str) -> Set[str]:
        """Retorna todos os ancestrais (transitivo)."""
        ancestors = set()
        to_visit = list(self.nodes.get(name, ConceptNode(Concept(name, 0))).parents)
        
        while to_visit:
            current = to_visit.pop()
            if current in ancestors:
                continue
            
            ancestors.add(current)
            
            if current in self.nodes:
                to_visit.extend(self.nodes[current].parents)
        
        return ancestors
    
    def get_descendants(self, name: str) -> Set[str]:
        """Retorna todos os descendentes (transitivo)."""
        descendants = set()
        to_visit = list(self.nodes.get(name, ConceptNode(Concept(name, 0))).children)
        
        while to_visit:
            current = to_visit.pop()
            if current in descendants:
                continue
            
            descendants.add(current)
            
            if current in self.nodes:
                to_visit.extend(self.nodes[current].children)
        
        return descendants
    
    def get_inherited_properties(self, name: str) -> Set[str]:
        """Retorna propriedades herdadas de ancestrais."""
        properties = set()
        
        # Propriedades próprias
        if name in self.concepts:
            properties.update(self.concepts[name].properties)
        
        # Propriedades herdadas
        for ancestor in self.get_ancestors(name):
            if ancestor in self.concepts:
                properties.update(self.concepts[ancestor].properties)
        
        return properties
    
    def lowest_common_ancestor(self, name1: str, name2: str) -> str | None:
        """Encontra o ancestral comum mais baixo."""
        ancestors1 = self.get_ancestors(name1)
        ancestors1.add(name1)
        
        ancestors2 = self.get_ancestors(name2)
        ancestors2.add(name2)
        
        common = ancestors1 & ancestors2
        
        if not common:
            return None
        
        # Encontra o mais específico (maior level)
        best = None
        best_level = -1
        
        for name in common:
            if name in self.concepts:
                level = self.concepts[name].level
                if level > best_level:
                    best = name
                    best_level = level
        
        return best
    
    def is_a(self, specific: str, general: str) -> bool:
        """Verifica se specific IS-A general."""
        if specific == general:
            return True
        return general in self.get_ancestors(specific)
    
    def semantic_distance(self, name1: str, name2: str) -> int:
        """Calcula distância semântica entre conceitos."""
        if name1 == name2:
            return 0
        
        lca = self.lowest_common_ancestor(name1, name2)
        
        if lca is None:
            return -1  # Não conectados
        
        # Distância = passos de name1 até LCA + passos de name2 até LCA
        def steps_to(start: str, target: str) -> int:
            if start == target:
                return 0
            
            visited = {start}
            queue = [(start, 0)]
            
            while queue:
                current, dist = queue.pop(0)
                
                if current in self.nodes:
                    for parent in self.nodes[current].parents:
                        if parent == target:
                            return dist + 1
                        
                        if parent not in visited:
                            visited.add(parent)
                            queue.append((parent, dist + 1))
            
            return -1
        
        d1 = steps_to(name1, lca)
        d2 = steps_to(name2, lca)
        
        if d1 < 0 or d2 < 0:
            return -1
        
        return d1 + d2


class PatternAbstractor:
    """
    Abstrai padrões de sequências de tokens.
    
    Exemplo:
        "cachorro corre", "gato corre", "pássaro corre"
        → "{ANIMAL} corre" (padrão abstrato)
    """
    
    def __init__(self, taxonomy: Taxonomy | None = None):
        self.taxonomy = taxonomy or Taxonomy()
        self.patterns: Dict[str, List[Tuple[str, ...]]] = defaultdict(list)
        self.abstractions: Dict[Tuple[str, ...], str] = {}
    
    def observe(self, sequence: Tuple[str, ...], category: str = "") -> None:
        """Observa uma sequência para abstração."""
        key = category or "_default"
        self.patterns[key].append(sequence)
    
    def abstract(self, min_support: int = 2) -> Dict[str, List[Tuple[str, ...]]]:
        """
        Extrai padrões abstratos das observações.
        
        Retorna mapa de categoria → padrões abstratos.
        """
        result: Dict[str, List[Tuple[str, ...]]] = {}
        
        for category, sequences in self.patterns.items():
            if len(sequences) < min_support:
                continue
            
            # Encontra elementos comuns por posição
            if not sequences:
                continue
            
            min_len = min(len(s) for s in sequences)
            abstract_pattern: List[str] = []
            
            for pos in range(min_len):
                elements = [s[pos] for s in sequences if pos < len(s)]
                unique = set(elements)
                
                if len(unique) == 1:
                    # Elemento constante
                    abstract_pattern.append(elements[0])
                else:
                    # Elemento variável - tenta abstrair via taxonomia
                    lca = self._find_common_abstraction(unique)
                    abstract_pattern.append(f"{{{lca}}}")
            
            if abstract_pattern:
                result[category] = [tuple(abstract_pattern)]
        
        return result
    
    def _find_common_abstraction(self, elements: Set[str]) -> str:
        """Encontra abstração comum para um conjunto de elementos."""
        if len(elements) == 1:
            return next(iter(elements))
        
        # Tenta encontrar LCA na taxonomia
        elements_list = list(elements)
        
        if len(elements_list) < 2:
            return "VAR"
        
        lca = self.taxonomy.lowest_common_ancestor(
            elements_list[0], 
            elements_list[1]
        )
        
        for elem in elements_list[2:]:
            if lca:
                new_lca = self.taxonomy.lowest_common_ancestor(lca, elem)
                if new_lca:
                    lca = new_lca
        
        return lca or "VAR"
    
    def match(
        self,
        sequence: Tuple[str, ...],
        pattern: Tuple[str, ...],
    ) -> Dict[str, str] | None:
        """
        Tenta casar sequência com padrão.
        
        Retorna bindings se casar, None caso contrário.
        """
        if len(sequence) != len(pattern):
            return None
        
        bindings: Dict[str, str] = {}
        
        for i, (elem, pat) in enumerate(zip(sequence, pattern)):
            if pat.startswith("{") and pat.endswith("}"):
                # Slot variável
                var_name = pat[1:-1]
                
                # Verifica se elemento é do tipo esperado
                if var_name != "VAR" and var_name in self.taxonomy.concepts:
                    if not self.taxonomy.is_a(elem, var_name):
                        return None
                
                if var_name in bindings:
                    if bindings[var_name] != elem:
                        return None
                else:
                    bindings[var_name] = elem
            else:
                # Elemento constante
                if elem != pat:
                    return None
        
        return bindings


class ConceptComposer:
    """
    Compõe conceitos complexos a partir de conceitos simples.
    
    Exemplo:
        "CACHORRO" + "RAIVOSO" → "CACHORRO_RAIVOSO"
        "CARRO" + "VERMELHO" + "RÁPIDO" → "CARRO_ESPORTIVO_VERMELHO"
    """
    
    def __init__(self, taxonomy: Taxonomy | None = None):
        self.taxonomy = taxonomy or Taxonomy()
        self.compositions: Dict[FrozenSet[str], str] = {}
        self.decompositions: Dict[str, FrozenSet[str]] = {}
    
    def compose(
        self,
        components: Set[str],
        result_name: str | None = None,
    ) -> str:
        """Compõe conceitos em um conceito complexo."""
        frozen = frozenset(components)
        
        if frozen in self.compositions:
            return self.compositions[frozen]
        
        if result_name is None:
            result_name = "_".join(sorted(components))
        
        self.compositions[frozen] = result_name
        self.decompositions[result_name] = frozen
        
        # Adiciona à taxonomia com propriedades combinadas
        all_props: Set[str] = set()
        max_level = 0
        
        for comp in components:
            if comp in self.taxonomy.concepts:
                all_props.update(self.taxonomy.concepts[comp].properties)
                max_level = max(max_level, self.taxonomy.concepts[comp].level)
        
        self.taxonomy.add_concept(result_name, max_level + 1, all_props)
        
        return result_name
    
    def decompose(self, concept_name: str) -> Set[str]:
        """Decompõe conceito em componentes."""
        return set(self.decompositions.get(concept_name, {concept_name}))
    
    def is_composition(self, concept_name: str) -> bool:
        """Verifica se é um conceito composto."""
        return concept_name in self.decompositions
    
    def shares_component(self, concept1: str, concept2: str) -> Set[str]:
        """Encontra componentes compartilhados."""
        comp1 = self.decompose(concept1)
        comp2 = self.decompose(concept2)
        return comp1 & comp2


def create_default_taxonomy() -> Taxonomy:
    """Cria taxonomia padrão com conceitos básicos."""
    tax = Taxonomy()
    
    # Entidades
    tax.add_concept("ENTIDADE", 0, {"existe"})
    
    # Seres vivos
    tax.add_concept("SER_VIVO", 1, {"nasce", "morre", "reproduz"})
    tax.add_relation("SER_VIVO", "ENTIDADE")
    
    # Animais
    tax.add_concept("ANIMAL", 2, {"move", "sente"})
    tax.add_relation("ANIMAL", "SER_VIVO")
    
    # Mamíferos
    tax.add_concept("MAMIFERO", 3, {"amamenta", "pelos"})
    tax.add_relation("MAMIFERO", "ANIMAL")
    
    # Específicos
    tax.add_concept("CACHORRO", 4, {"late", "faro"})
    tax.add_relation("CACHORRO", "MAMIFERO")
    
    tax.add_concept("GATO", 4, {"mia", "garras"})
    tax.add_relation("GATO", "MAMIFERO")
    
    # Aves
    tax.add_concept("AVE", 3, {"penas", "voa"})
    tax.add_relation("AVE", "ANIMAL")
    
    # Plantas
    tax.add_concept("PLANTA", 2, {"fotossintese"})
    tax.add_relation("PLANTA", "SER_VIVO")
    
    # Objetos
    tax.add_concept("OBJETO", 1, {"inanimado"})
    tax.add_relation("OBJETO", "ENTIDADE")
    
    # Veículos
    tax.add_concept("VEICULO", 2, {"transporte"})
    tax.add_relation("VEICULO", "OBJETO")
    
    tax.add_concept("CARRO", 3, {"rodas", "motor"})
    tax.add_relation("CARRO", "VEICULO")
    
    # Ações
    tax.add_concept("ACAO", 0, {"ocorre"})
    
    tax.add_concept("MOVIMENTO", 1, {"desloca"})
    tax.add_relation("MOVIMENTO", "ACAO")
    
    tax.add_concept("CORRER", 2, {"rapido"})
    tax.add_relation("CORRER", "MOVIMENTO")
    
    tax.add_concept("ANDAR", 2, {"lento"})
    tax.add_relation("ANDAR", "MOVIMENTO")
    
    return tax


__all__ = [
    "RelationType",
    "Concept",
    "HierarchicalRelation",
    "ConceptNode",
    "Taxonomy",
    "PatternAbstractor",
    "ConceptComposer",
    "create_default_taxonomy",
]
