"""
Compressão de Conhecimento: Comprime conhecimento em estruturas mínimas.

Encontra a representação mais compacta que preserva toda a informação.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from liu import Node, NodeKind, fingerprint, var

from .weightless_learning import Episode


@dataclass(frozen=True, slots=True)
class CompressedKnowledge:
    """Conhecimento comprimido."""
    
    # Estrutura mínima que representa múltiplos episódios
    structure: Node
    # Episódios que esta estrutura representa
    episode_count: int
    # Redução de tamanho
    compression_ratio: float
    # Informação preservada (0.0 a 1.0)
    information_preserved: float


class KnowledgeCompressor:
    """
    Comprime conhecimento encontrando representações mínimas.
    
    Algoritmo:
    1. Agrupa episódios similares
    2. Encontra estrutura comum mínima
    3. Generaliza ao máximo preservando informação
    4. Calcula compressão e informação preservada
    """
    
    def compress(
        self, episodes: List[Episode], min_episodes: int = 3
    ) -> List[CompressedKnowledge]:
        """Comprime lista de episódios em conhecimento mínimo."""
        
        # Agrupa episódios por estrutura similar
        groups = self._group_similar(episodes, min_episodes)
        
        compressed: List[CompressedKnowledge] = []
        
        for group in groups:
            if len(group) < min_episodes:
                continue
            
            # Encontra estrutura comum mínima
            common = self._find_minimal_common_structure(group)
            
            # Calcula compressão
            original_size = sum(self._structure_size(e.input_struct) for e in group)
            compressed_size = self._structure_size(common)
            compression_ratio = 1.0 - (compressed_size / max(1, original_size))
            
            # Calcula informação preservada
            info_preserved = self._calculate_information_preserved(group, common)
            
            knowledge = CompressedKnowledge(
                structure=common,
                episode_count=len(group),
                compression_ratio=compression_ratio,
                information_preserved=info_preserved,
            )
            
            compressed.append(knowledge)
        
        # Ordena por compressão e informação preservada
        compressed.sort(
            key=lambda k: (k.compression_ratio, k.information_preserved),
            reverse=True,
        )
        
        return compressed
    
    def _group_similar(
        self, episodes: List[Episode], min_size: int
    ) -> List[List[Episode]]:
        """Agrupa episódios similares."""
        from .structural_alignment import StructuralAligner
        
        aligner = StructuralAligner()
        groups: List[List[Episode]] = []
        
        for episode in episodes:
            added = False
            for group in groups:
                # Compara com primeiro do grupo
                alignment = aligner.align(group[0].input_struct, episode.input_struct)
                if alignment and alignment.similarity >= 0.6:
                    group.append(episode)
                    added = True
                    break
            
            if not added:
                groups.append([episode])
        
        # Filtra grupos pequenos
        return [g for g in groups if len(g) >= min_size]
    
    def _find_minimal_common_structure(
        self, episodes: List[Episode]
    ) -> Node:
        """Encontra estrutura comum mínima de um grupo."""
        from .structural_alignment import StructuralAligner
        
        if not episodes:
            from liu import struct
            return struct()
        
        aligner = StructuralAligner()
        
        # Começa com primeira estrutura
        common = episodes[0].input_struct
        
        # Alinha com todas as outras e generaliza
        for episode in episodes[1:]:
            alignment = aligner.align(common, episode.input_struct)
            if alignment:
                # Usa estrutura comum do alinhamento
                common = alignment.common_structure
        
        return common
    
    def _structure_size(self, node: Node) -> int:
        """Calcula tamanho de uma estrutura."""
        size = 1
        for arg in node.args:
            size += self._structure_size(arg)
        if node.kind is NodeKind.STRUCT:
            for _, value in node.fields:
                size += self._structure_size(value)
        return size
    
    def _calculate_information_preserved(
        self, episodes: List[Episode], compressed: Node
    ) -> float:
        """
        Calcula quanto da informação original foi preservada.
        
        Baseado em quantas relações/episódios a estrutura comprimida ainda representa.
        """
        # Simplificação: baseado em similaridade estrutural
        from .structural_alignment import StructuralAligner
        
        aligner = StructuralAligner()
        preserved_count = 0
        
        for episode in episodes:
            alignment = aligner.align(compressed, episode.input_struct)
            if alignment and alignment.similarity > 0.5:
                preserved_count += 1
        
        return preserved_count / len(episodes) if episodes else 0.0


__all__ = ["CompressedKnowledge", "KnowledgeCompressor"]
