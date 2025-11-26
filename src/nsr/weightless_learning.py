"""
Aprendizado Sem Pesos: Sistema de aprendizado baseado em estruturas simbólicas.

Em vez de ajustar pesos numéricos, este sistema:
1. Armazena episódios massivamente
2. Compress padrões frequentes em regras
3. Evolui estruturas de conhecimento
4. Generaliza através de abstração hierárquica
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from hashlib import blake2b
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from liu import Node, NodeKind, entity, fingerprint, relation, struct, text, var

from .state import Rule


@dataclass(frozen=True, slots=True)
class Episode:
    """Episódio completo: entrada → processamento → saída."""
    
    input_text: str
    input_struct: Node
    output_text: str
    output_struct: Node
    relations: Tuple[Node, ...]
    context: Tuple[Node, ...]
    quality: float
    fingerprint: str  # Hash determinístico do episódio


@dataclass(slots=True)
class Pattern:
    """Padrão extraído de múltiplos episódios."""
    
    # Estrutura do padrão (pode conter variáveis ?X, ?Y)
    structure: Node
    # Episódios que contêm este padrão
    episode_fingerprints: Set[str]
    # Frequência
    frequency: int
    # Confiança (baseada em qualidade média dos episódios)
    confidence: float
    # Generalização (quanto do padrão é variável)
    generalization_level: float


@dataclass(slots=True)
class WeightlessLearner:
    """
    Sistema de aprendizado que ajusta estruturas, não pesos.
    
    Parâmetros ajustáveis:
    - Regras (estruturas if-then)
    - Grafos de conhecimento (nós e arestas)
    - Padrões comprimidos
    - Hierarquias taxonômicas
    """
    
    # Memória episódica
    episodes: Dict[str, Episode] = field(default_factory=dict)
    
    # Padrões extraídos
    patterns: Dict[str, Pattern] = field(default_factory=dict)
    
    # Regras aprendidas
    learned_rules: List[Rule] = field(default_factory=list)
    
    # Índices para busca rápida
    input_index: Dict[str, Set[str]] = field(default_factory=dict)  # fingerprint → episode_fps
    relation_index: Dict[str, Set[str]] = field(default_factory=dict)  # rel_fp → episode_fps
    
    # Configuração
    min_pattern_support: int = 3
    min_confidence: float = 0.6
    max_patterns: int = 10000
    
    def add_episode(
        self,
        input_text: str,
        input_struct: Node,
        output_text: str,
        output_struct: Node,
        relations: Tuple[Node, ...],
        context: Tuple[Node, ...],
        quality: float,
    ) -> str:
        """Adiciona um episódio à memória."""
        
        # Cria fingerprint determinístico
        hasher = blake2b(digest_size=16)
        hasher.update(input_text.encode("utf-8"))
        hasher.update(fingerprint(input_struct).encode("utf-8"))
        hasher.update(output_text.encode("utf-8"))
        ep_fp = hasher.hexdigest()
        
        episode = Episode(
            input_text=input_text,
            input_struct=input_struct,
            output_text=output_text,
            output_struct=output_struct,
            relations=relations,
            context=context,
            quality=quality,
            fingerprint=ep_fp,
        )
        
        self.episodes[ep_fp] = episode
        
        # Indexa por input
        input_fp = fingerprint(input_struct)
        if input_fp not in self.input_index:
            self.input_index[input_fp] = set()
        self.input_index[input_fp].add(ep_fp)
        
        # Indexa por relações
        for rel in relations:
            rel_fp = fingerprint(rel)
            if rel_fp not in self.relation_index:
                self.relation_index[rel_fp] = set()
            self.relation_index[rel_fp].add(ep_fp)
        
        return ep_fp
    
    def find_similar_episodes(self, query_struct: Node, k: int = 10) -> List[Episode]:
        """Encontra episódios similares usando índice estrutural."""
        
        query_fp = fingerprint(query_struct)
        candidate_fps = self.input_index.get(query_fp, set())
        
        # Se não encontrou exato, busca por relações comuns
        if not candidate_fps:
            query_rels = self._extract_relations(query_struct)
            for rel in query_rels:
                rel_fp = fingerprint(rel)
                candidate_fps.update(self.relation_index.get(rel_fp, set()))
        
        episodes = [self.episodes[fp] for fp in candidate_fps if fp in self.episodes]
        
        # Ordena por qualidade e retorna top-k
        episodes.sort(key=lambda e: e.quality, reverse=True)
        return episodes[:k]
    
    def extract_patterns(self, min_support: int | None = None) -> List[Pattern]:
        """Extrai padrões frequentes dos episódios."""
        
        if min_support is None:
            min_support = self.min_pattern_support
        
        # Agrupa episódios por estrutura de entrada similar
        structure_groups: Dict[str, List[Episode]] = defaultdict(list)
        for episode in self.episodes.values():
            struct_fp = fingerprint(episode.input_struct)
            structure_groups[struct_fp].append(episode)
        
        patterns: List[Pattern] = []
        
        for struct_fp, group in structure_groups.items():
            if len(group) < min_support:
                continue
            
            # Calcula confiança média
            avg_quality = sum(e.quality for e in group) / len(group)
            if avg_quality < self.min_confidence:
                continue
            
            # Cria padrão
            representative = group[0]
            pattern_fp = f"pattern_{struct_fp}"
            
            # Tenta generalizar (substituir entidades específicas por variáveis)
            generalized = self._generalize_structure(representative.input_struct, group)
            generalization_level = self._calculate_generalization_level(
                representative.input_struct, generalized
            )
            
            pattern = Pattern(
                structure=generalized,
                episode_fingerprints={e.fingerprint for e in group},
                frequency=len(group),
                confidence=avg_quality,
                generalization_level=generalization_level,
            )
            
            patterns.append(pattern)
            self.patterns[pattern_fp] = pattern
        
        # Ordena por frequência e confiança
        patterns.sort(key=lambda p: (p.frequency, p.confidence), reverse=True)
        
        # Limita número de padrões
        if len(patterns) > self.max_patterns:
            patterns = patterns[: self.max_patterns]
        
        return patterns
    
    def learn_rules_from_patterns(self, patterns: List[Pattern] | None = None) -> List[Rule]:
        """Aprende regras a partir de padrões frequentes."""
        
        if patterns is None:
            patterns = list(self.patterns.values())
        
        new_rules: List[Rule] = []
        
        for pattern in patterns:
            if pattern.frequency < self.min_pattern_support:
                continue
            if pattern.confidence < self.min_confidence:
                continue
            
            # Extrai relações do padrão
            relations = self._extract_relations_from_structure(pattern.structure)
            
            if not relations:
                continue
            
            # Cria regra: se estrutura similar, então relações similares
            # Simplificação: assume que primeira relação é consequência
            if len(relations) >= 2:
                # Regra: se R1 então R2
                antecedent = relations[0]
                consequent = relations[1]
                
                # Generaliza usando variáveis
                generalized_antecedent = self._generalize_relation(antecedent)
                generalized_consequent = self._generalize_relation(consequent)
                
                rule = Rule(
                    if_all=(generalized_antecedent,),
                    then=generalized_consequent,
                )
                
                new_rules.append(rule)
        
        # Remove duplicatas
        unique_rules = []
        seen_rule_fps = set()
        for rule in new_rules:
            rule_fp = self._rule_fingerprint(rule)
            if rule_fp not in seen_rule_fps:
                seen_rule_fps.add(rule_fp)
                unique_rules.append(rule)
        
        self.learned_rules.extend(unique_rules)
        return unique_rules
    
    def _extract_relations(self, struct: Node) -> List[Node]:
        """Extrai todas as relações de uma estrutura."""
        relations = []
        
        if struct.kind is NodeKind.REL:
            relations.append(struct)
        
        for arg in struct.args:
            relations.extend(self._extract_relations(arg))
        
        if struct.kind is NodeKind.STRUCT:
            for _, value in struct.fields:
                relations.extend(self._extract_relations(value))
        
        return relations
    
    def _extract_relations_from_structure(self, struct: Node) -> List[Node]:
        """Extrai relações de uma estrutura (helper)."""
        return self._extract_relations(struct)
    
    def _generalize_structure(
        self, struct: Node, episodes: List[Episode]
    ) -> Node:
        """
        Generaliza uma estrutura substituindo entidades específicas por variáveis.
        
        Se múltiplos episódios têm estruturas similares mas com entidades diferentes,
        substitui essas entidades por variáveis.
        """
        # Simplificação: por enquanto retorna a estrutura original
        # Implementação completa exigiria análise de alinhamento estrutural
        return struct
    
    def _generalize_relation(self, rel: Node) -> Node:
        """Generaliza uma relação substituindo entidades por variáveis."""
        if rel.kind is not NodeKind.REL or len(rel.args) < 2:
            return rel
        
        # Substitui argumentos por variáveis
        var_x = var("?X")
        var_y = var("?Y")
        
        return relation(rel.label or "", var_x, var_y)
    
    def _calculate_generalization_level(self, original: Node, generalized: Node) -> float:
        """Calcula o nível de generalização (0=específico, 1=totalmente genérico)."""
        # Simplificação: conta variáveis vs entidades
        original_vars = self._count_variables(original)
        generalized_vars = self._count_variables(generalized)
        total_nodes = self._count_nodes(original)
        
        if total_nodes == 0:
            return 0.0
        
        return generalized_vars / max(1, total_nodes)
    
    def _count_variables(self, node: Node) -> int:
        """Conta variáveis em um nó."""
        count = 0
        if node.kind is NodeKind.VAR:
            count = 1
        for arg in node.args:
            count += self._count_variables(arg)
        if node.kind is NodeKind.STRUCT:
            for _, value in node.fields:
                count += self._count_variables(value)
        return count
    
    def _count_nodes(self, node: Node) -> int:
        """Conta total de nós."""
        count = 1
        for arg in node.args:
            count += self._count_nodes(arg)
        if node.kind is NodeKind.STRUCT:
            for _, value in node.fields:
                count += self._count_nodes(value)
        return count
    
    def _rule_fingerprint(self, rule: Rule) -> str:
        """Cria fingerprint determinístico de uma regra."""
        hasher = blake2b(digest_size=16)
        for antecedent in rule.if_all:
            hasher.update(fingerprint(antecedent).encode("utf-8"))
        hasher.update(fingerprint(rule.then).encode("utf-8"))
        return hasher.hexdigest()
    
    def save(self, path: str) -> None:
        """Salva o estado do aprendizado."""
        # Implementação: serializa episódios, padrões e regras
        # Por enquanto, placeholder
        pass
    
    def load(self, path: str) -> None:
        """Carrega o estado do aprendizado."""
        # Implementação: deserializa
        # Por enquanto, placeholder
        pass


def learn_from_episodes(
    episodes: Iterable[Episode],
    min_support: int = 3,
    min_confidence: float = 0.6,
) -> Tuple[List[Pattern], List[Rule]]:
    """
    Função de alto nível: aprende padrões e regras de episódios.
    
    Esta é a função principal de aprendizado sem pesos.
    Em vez de ajustar números, ajusta estruturas simbólicas.
    """
    learner = WeightlessLearner(
        min_pattern_support=min_support,
        min_confidence=min_confidence,
    )
    
    # Adiciona episódios
    for episode in episodes:
        learner.add_episode(
            episode.input_text,
            episode.input_struct,
            episode.output_text,
            episode.output_struct,
            episode.relations,
            episode.context,
            episode.quality,
        )
    
    # Extrai padrões
    patterns = learner.extract_patterns()
    
    # Aprende regras
    rules = learner.learn_rules_from_patterns(patterns)
    
    return patterns, rules


__all__ = [
    "Episode",
    "Pattern",
    "WeightlessLearner",
    "learn_from_episodes",
]
