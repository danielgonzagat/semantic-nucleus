"""
Índices Eficientes para Busca Rápida em Memória Episódica Massiva.

Implementa múltiplos índices especializados para busca rápida de episódios similares.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from hashlib import blake2b
from typing import Dict, List, Set, Tuple

from liu import Node, NodeKind, fingerprint

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .weightless_types import Episode


@dataclass(slots=True)
class EpisodeIndex:
    """
    Sistema de índices multi-dimensional para busca rápida de episódios.
    
    Índices:
    - Por estrutura de entrada (exato)
    - Por relações (invertido)
    - Por contexto (semântico)
    - Por qualidade (ordenado)
    """
    
    # Índice estrutural: fingerprint(struct) -> {episode_fp}
    structure_index: Dict[str, Set[str]] = field(default_factory=dict)
    
    # Índice invertido de relações: fingerprint(rel) -> {episode_fp}
    relation_index: Dict[str, Set[str]] = field(default_factory=dict)
    
    # Índice de contexto: palavras-chave -> {episode_fp}
    context_index: Dict[str, Set[str]] = field(default_factory=dict)
    
    # Índice por qualidade: episode_fp -> quality (para ordenação)
    quality_index: Dict[str, float] = field(default_factory=dict)
    
    # Cache de buscas recentes
    search_cache: Dict[str, List[str]] = field(default_factory=dict)
    cache_size: int = 100
    
    def add_episode(self, episode: "Episode") -> None:
        """Adiciona episódio a todos os índices."""
        ep_fp = episode.fingerprint
        
        # Índice estrutural
        struct_fp = fingerprint(episode.input_struct)
        if struct_fp not in self.structure_index:
            self.structure_index[struct_fp] = set()
        self.structure_index[struct_fp].add(ep_fp)
        
        # Índice de relações
        for rel in episode.relations:
            rel_fp = fingerprint(rel)
            if rel_fp not in self.relation_index:
                self.relation_index[rel_fp] = set()
            self.relation_index[rel_fp].add(ep_fp)
        
        # Índice de contexto (extrai palavras-chave)
        keywords = self._extract_keywords(episode)
        for keyword in keywords:
            if keyword not in self.context_index:
                self.context_index[keyword] = set()
            self.context_index[keyword].add(ep_fp)
        
        # Índice de qualidade
        self.quality_index[ep_fp] = episode.quality
        
        # Limpa cache se necessário
        if len(self.search_cache) > self.cache_size:
            # Remove 20% mais antigos
            keys_to_remove = list(self.search_cache.keys())[: self.cache_size // 5]
            for key in keys_to_remove:
                del self.search_cache[key]
    
    def find_by_structure(self, struct: Node, k: int = 10) -> List[str]:
        """Busca episódios por estrutura exata."""
        struct_fp = fingerprint(struct)
        cache_key = f"struct:{struct_fp}:{k}"
        
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        
        candidates = self.structure_index.get(struct_fp, set())
        results = self._rank_by_quality(list(candidates), k)
        
        self.search_cache[cache_key] = results
        return results
    
    def find_by_relations(
        self, relations: List[Node], k: int = 10, min_match: int = 1
    ) -> List[str]:
        """Busca episódios que contêm pelo menos min_match relações."""
        cache_key = f"rels:{len(relations)}:{min_match}:{k}"
        
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        
        # Conta quantas relações cada episódio tem em comum
        episode_scores: Dict[str, int] = defaultdict(int)
        
        for rel in relations:
            rel_fp = fingerprint(rel)
            if rel_fp in self.relation_index:
                for ep_fp in self.relation_index[rel_fp]:
                    episode_scores[ep_fp] += 1
        
        # Filtra por min_match
        candidates = [
            ep_fp for ep_fp, score in episode_scores.items() if score >= min_match
        ]
        
        results = self._rank_by_quality(candidates, k)
        self.search_cache[cache_key] = results
        return results
    
    def find_by_context(self, keywords: Set[str], k: int = 10) -> List[str]:
        """Busca episódios por palavras-chave no contexto."""
        cache_key = f"ctx:{len(keywords)}:{k}"
        
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        
        # Episódios que contêm pelo menos uma palavra-chave
        candidates: Set[str] = set()
        for keyword in keywords:
            if keyword in self.context_index:
                candidates.update(self.context_index[keyword])
        
        results = self._rank_by_quality(list(candidates), k)
        self.search_cache[cache_key] = results
        return results
    
    def find_similar(
        self,
        struct: Node | None = None,
        relations: List[Node] | None = None,
        keywords: Set[str] | None = None,
        k: int = 10,
    ) -> List[str]:
        """
        Busca híbrida: combina múltiplos índices para encontrar episódios similares.
        """
        all_candidates: Set[str] = set()
        
        # Busca estrutural
        if struct is not None:
            struct_results = self.find_by_structure(struct, k * 2)
            all_candidates.update(struct_results)
            
            # Se não houver keywords, extrai do struct
            if not keywords:
                keywords = self._extract_entity_labels(struct)
        
        # Busca por relações
        if relations:
            rel_results = self.find_by_relations(relations, k * 2, min_match=1)
            all_candidates.update(rel_results)
        
        # Busca por contexto
        if keywords:
            ctx_results = self.find_by_context(keywords, k * 2)
            all_candidates.update(ctx_results)
        
        # Rankeia todos os candidatos por qualidade
        return self._rank_by_quality(list(all_candidates), k)
    
    def _rank_by_quality(self, candidates: List[str], k: int) -> List[str]:
        """Rankeia candidatos por qualidade e retorna top-k."""
        scored = [
            (ep_fp, self.quality_index.get(ep_fp, 0.0)) for ep_fp in candidates
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [ep_fp for ep_fp, _ in scored[:k]]
    
    def _extract_keywords(self, episode: Episode) -> Set[str]:
        """Extrai palavras-chave de um episódio."""
        keywords: Set[str] = set()
        
        # Extrai do texto de entrada
        words = episode.input_text.lower().split()
        keywords.update(w for w in words if len(w) > 3)
        
        # Extrai labels de entidades
        keywords.update(self._extract_entity_labels(episode.input_struct))
        
        return keywords
    
    def _extract_entity_labels(self, node: Node) -> Set[str]:
        """Extrai labels de entidades de um nó."""
        labels: Set[str] = set()
        
        if node.kind is NodeKind.ENTITY and node.label:
            labels.add(node.label.lower())
        
        for arg in node.args:
            labels.update(self._extract_entity_labels(arg))
        
        if node.kind is NodeKind.STRUCT:
            for _, value in node.fields:
                labels.update(self._extract_entity_labels(value))
        
        return labels
    
    def remove_episode(self, episode_fp: str) -> None:
        """Remove episódio de todos os índices."""
        # Remove de índices (implementação simplificada)
        # Em produção, manteria referências reversas
        pass
    
    def clear_cache(self) -> None:
        """Limpa cache de buscas."""
        self.search_cache.clear()


__all__ = ["EpisodeIndex"]
