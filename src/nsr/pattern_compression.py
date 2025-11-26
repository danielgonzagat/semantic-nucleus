"""
Compressão de Padrões: Encontra e comprime padrões frequentes em estruturas mínimas.

Este módulo implementa algoritmos de mineração de padrões frequentes adaptados
para estruturas simbólicas LIU, sem usar pesos numéricos.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from liu import Node, NodeKind, fingerprint, var

from .weightless_types import Episode, Pattern
from .abstraction_hierarchy import AbstractionHierarchy


@dataclass(frozen=True, slots=True)
class CompressedPattern:
    """Padrão comprimido: estrutura mínima que captura múltiplos episódios."""
    
    # Estrutura generalizada (com variáveis)
    structure: Node
    # Episódios que este padrão representa
    episode_count: int
    # Redução de tamanho (original vs comprimido)
    compression_ratio: float
    # Confiança (baseada em qualidade dos episódios)
    confidence: float


class PatternCompressor:
    """
    Compress padrões frequentes em estruturas mínimas.
    
    Algoritmo:
    1. Encontra subestruturas comuns
    2. Generaliza substituindo entidades por variáveis
    3. Agrupa episódios similares
    4. Cria representação comprimida
    """
    
    def __init__(self, min_support: int = 3, hierarchy: AbstractionHierarchy | None = None):
        self.min_support = min_support
        self.hierarchy = hierarchy or AbstractionHierarchy()
    
    def compress_episodes(
        self, episodes: List[Episode]
    ) -> List[CompressedPattern]:
        """Compress uma lista de episódios em padrões mínimos."""
        
        # 1. Agrupa por estrutura de entrada similar
        structure_groups = self._group_by_structure(episodes)
        
        # 2. Para cada grupo, encontra subestruturas comuns
        compressed: List[CompressedPattern] = []
        
        for struct_fp, group in structure_groups.items():
            if len(group) < self.min_support:
                continue
            
            # Encontra subestruturas comuns
            common_substructures = self._find_common_substructures(group)
            
            # Generaliza usando hierarquia de abstração
            generalized = self._generalize_substructures(common_substructures)
            # Aplica hierarquia de abstração
            generalized = self.hierarchy.generalize(generalized, target_level=1)
            
            # Calcula compressão
            original_size = sum(self._structure_size(e.input_struct) for e in group)
            compressed_size = self._structure_size(generalized)
            compression_ratio = 1.0 - (compressed_size / max(1, original_size))
            
            # Confiança média
            avg_confidence = sum(e.quality for e in group) / len(group)
            
            pattern = CompressedPattern(
                structure=generalized,
                episode_count=len(group),
                compression_ratio=compression_ratio,
                confidence=avg_confidence,
            )
            
            compressed.append(pattern)
        
        # Ordena por compressão e confiança
        compressed.sort(
            key=lambda p: (p.compression_ratio, p.confidence), reverse=True
        )
        
        return compressed
    
    def _group_by_structure(
        self, episodes: List[Episode]
    ) -> Dict[str, List[Episode]]:
        """Agrupa episódios por estrutura de entrada similar."""
        groups: Dict[str, List[Episode]] = defaultdict(list)
        
        for episode in episodes:
            struct_fp = fingerprint(episode.input_struct)
            groups[struct_fp].append(episode)
        
        return dict(groups)
    
    def _find_common_substructures(
        self, episodes: List[Episode]
    ) -> List[Node]:
        """Encontra subestruturas comuns a múltiplos episódios."""
        
        if not episodes:
            return []
        
        # Extrai todas as subestruturas do primeiro episódio
        reference = episodes[0].input_struct
        reference_subs = self._extract_all_substructures(reference)
        
        # Para cada subestrutura, verifica se aparece em outros episódios
        common: List[Node] = []
        sub_counts: Counter[Node] = Counter()
        
        for episode in episodes:
            episode_subs = self._extract_all_substructures(episode.input_struct)
            for sub in episode_subs:
                sub_counts[sub] += 1
        
        # Retorna subestruturas que aparecem em pelo menos min_support episódios
        for sub, count in sub_counts.items():
            if count >= self.min_support:
                common.append(sub)
        
        return common
    
    def _extract_all_substructures(self, struct: Node) -> List[Node]:
        """Extrai todas as subestruturas de um nó."""
        substructures = [struct]
        
        for arg in struct.args:
            substructures.extend(self._extract_all_substructures(arg))
        
        if struct.kind is NodeKind.STRUCT:
            for _, value in struct.fields:
                substructures.extend(self._extract_all_substructures(value))
        
        return substructures
    
    def _generalize_substructures(
        self, substructures: List[Node]
    ) -> Node:
        """Generaliza subestruturas substituindo entidades por variáveis."""
        
        if not substructures:
            return struct()  # Nó vazio
        
        # Encontra a subestrutura mais comum
        most_common = max(
            substructures, key=lambda s: substructures.count(s)
        )
        
        # Generaliza substituindo entidades específicas por variáveis
        return self._generalize_node(most_common)
    
    def _generalize_node(self, node: Node) -> Node:
        """Generaliza um nó substituindo entidades por variáveis."""
        
        if node.kind is NodeKind.ENTITY:
            # Substitui por variável
            return var("?X")
        
        if node.kind is NodeKind.REL:
            # Mantém relação, generaliza argumentos
            generalized_args = tuple(
                self._generalize_node(arg) for arg in node.args
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
                (k, self._generalize_node(v)) for k, v in node.fields
            )
            return Node(
                kind=NodeKind.STRUCT,
                label=node.label,
                args=node.args,
                fields=generalized_fields,
                value=node.value,
            )
        
        # Para outros tipos, mantém como está
        generalized_args = tuple(
            self._generalize_node(arg) for arg in node.args
        )
        return Node(
            kind=node.kind,
            label=node.label,
            args=generalized_args,
            fields=node.fields,
            value=node.value,
        )
    
    def _structure_size(self, struct: Node) -> int:
        """Calcula tamanho de uma estrutura (número de nós)."""
        size = 1
        for arg in struct.args:
            size += self._structure_size(arg)
        if struct.kind is NodeKind.STRUCT:
            for _, value in struct.fields:
                size += self._structure_size(value)
        return size


__all__ = ["CompressedPattern", "PatternCompressor"]
