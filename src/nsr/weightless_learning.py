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
from .weightless_types import Episode, Pattern
from .weightless_index import EpisodeIndex
from .structural_alignment import StructuralAligner, find_common_patterns


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
    
    # Índice eficiente para busca rápida
    index: EpisodeIndex = field(default_factory=EpisodeIndex)
    
    # Configuração
    min_pattern_support: int = 3
    min_confidence: float = 0.6
    max_patterns: int = 10000
    auto_learn_interval: int = 50  # Aprende a cada N episódios
    episodes_since_learning: int = 0
    # Sistema de avaliação de regras
    rule_evaluator: "RuleEvaluator | None" = None
    # Sistemas avançados de aprendizado
    structural_aligner: "StructuralAligner | None" = None
    analogical_learner: "AnalogicalLearner | None" = None
    knowledge_compressor: "KnowledgeCompressor | None" = None
    hypothesis_generator: "HypothesisGenerator | None" = None
    causal_learner: "CausalLearner | None" = None
    planning_system: "PlanningSystem | None" = None
    world_simulator: "WorldSimulator | None" = None
    
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
        
        # Adiciona ao índice eficiente
        self.index.add_episode(episode)
        
        # Incrementa contador para aprendizado automático
        self.episodes_since_learning += 1
        
        # Aprende automaticamente se necessário
        if self.episodes_since_learning >= self.auto_learn_interval:
            self._auto_learn()
            self._evolve_rules()
            self.episodes_since_learning = 0
        
        return ep_fp
    
    def find_similar_episodes(
        self,
        query_struct: Node | None = None,
        query_relations: List[Node] | None = None,
        query_keywords: Set[str] | None = None,
        k: int = 10,
    ) -> List[Episode]:
        """Encontra episódios similares usando índice multi-dimensional."""
        
        # Usa índice eficiente
        candidate_fps = self.index.find_similar(
            struct=query_struct,
            relations=query_relations,
            keywords=query_keywords,
            k=k,
        )
        
        episodes = [self.episodes[fp] for fp in candidate_fps if fp in self.episodes]
        return episodes
    
    def _auto_learn(self) -> None:
        """Aprendizado automático: extrai padrões e aprende regras."""
        if len(self.episodes) < self.min_pattern_support:
            return
        
        # Inicializa sistemas avançados se necessário
        if self.structural_aligner is None:
            from .structural_alignment import StructuralAligner
            self.structural_aligner = StructuralAligner()
        
        if self.analogical_learner is None:
            from .analogical_learning import AnalogicalLearner
            self.analogical_learner = AnalogicalLearner()
        
        if self.knowledge_compressor is None:
            from .knowledge_compression import KnowledgeCompressor
            self.knowledge_compressor = KnowledgeCompressor()
        
        if self.hypothesis_generator is None:
            from .hypothesis_generation import HypothesisGenerator
            self.hypothesis_generator = HypothesisGenerator(
                min_support=self.min_pattern_support,
                min_confidence=self.min_confidence,
            )
        
        # 1. Extrai padrões básicos
        patterns = self.extract_patterns()
        
        # 2. Aprende por analogia
        episodes_list = list(self.episodes.values())
        analogical_rules = self.analogical_learner.learn_from_episodes(episodes_list)
        
        # 3. Gera e testa hipóteses
        hypotheses = self.hypothesis_generator.generate_from_episodes(episodes_list)
        for hypothesis in hypotheses:
            tested = self.hypothesis_generator.test_hypothesis(hypothesis, episodes_list)
            if self.hypothesis_generator.accept_or_reject(tested):
                # Adiciona regra aceita
                if tested.rule not in self.learned_rules:
                    self.learned_rules.append(tested.rule)
        
        # 4. Aprende regras de padrões
        new_rules = self.learn_rules_from_patterns(patterns)
        
        # 5. Comprime conhecimento (opcional, para otimização)
        if len(episodes_list) > 100:
            compressed = self.knowledge_compressor.compress(episodes_list, min_episodes=5)
            # Usa conhecimento comprimido para melhorar busca
        
        # Log (pode ser removido em produção)
        total_new = len(new_rules) + len(self.hypothesis_generator.accepted_rules)
        if total_new > 0:
            print(f"[WeightlessLearning] Aprendidas {total_new} novas regras de {len(self.episodes)} episódios")
            print(f"  - Padrões: {len(new_rules)}")
            print(f"  - Hipóteses aceitas: {len(self.hypothesis_generator.accepted_rules)}")
    
    def _evolve_rules(self) -> None:
        """Evolui regras: avalia e remove regras ruins."""
        if not self.learned_rules:
            return
        
        if self.rule_evaluator is None:
            from .rule_evaluator import RuleEvaluator
            self.rule_evaluator = RuleEvaluator()
        
        # Pega amostra de episódios para avaliação
        episodes_list = list(self.episodes.values())
        sample_size = min(100, len(episodes_list))
        sample_episodes = episodes_list[:sample_size]
        
        # Evolui regras
        good_rules, removed_rules = self.rule_evaluator.evolve_rules(
            self.learned_rules, sample_episodes, self
        )
        
        # Atualiza lista de regras
        self.learned_rules = good_rules
        
        if removed_rules:
            print(f"[WeightlessLearning] Removidas {len(removed_rules)} regras com baixo fitness")
    
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
        """Salva o estado do aprendizado em JSON."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        
        # Serializa episódios (simplificado - apenas metadados)
        episodes_data = []
        for ep_fp, episode in self.episodes.items():
            episodes_data.append({
                "fingerprint": ep_fp,
                "input_text": episode.input_text,
                "output_text": episode.output_text,
                "quality": episode.quality,
                "input_struct_fp": fingerprint(episode.input_struct),
                "output_struct_fp": fingerprint(episode.output_struct),
            })
        
        # Serializa padrões
        patterns_data = []
        for pattern_fp, pattern in self.patterns.items():
            patterns_data.append({
                "fingerprint": pattern_fp,
                "structure_fp": fingerprint(pattern.structure),
                "frequency": pattern.frequency,
                "confidence": pattern.confidence,
                "generalization_level": pattern.generalization_level,
            })
        
        # Serializa regras
        rules_data = []
        for rule in self.learned_rules:
            rules_data.append({
                "if_all": [fingerprint(ant) for ant in rule.if_all],
                "then": fingerprint(rule.then),
            })
        
        payload = {
            "episodes": episodes_data,
            "patterns": patterns_data,
            "rules": rules_data,
            "config": {
                "min_pattern_support": self.min_pattern_support,
                "min_confidence": self.min_confidence,
                "max_patterns": self.max_patterns,
            },
        }
        
        with target.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    
    def load(self, path: str) -> None:
        """Carrega o estado do aprendizado de JSON."""
        target = Path(path)
        if not target.exists():
            return
        
        with target.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        
        # Carrega configuração
        config = payload.get("config", {})
        self.min_pattern_support = config.get("min_pattern_support", 3)
        self.min_confidence = config.get("min_confidence", 0.6)
        self.max_patterns = config.get("max_patterns", 10000)
        
        # Nota: Para carregar episódios completos, precisaria reconstruir estruturas LIU
        # Por enquanto, apenas carrega metadados
        # Em produção, salvaria estruturas LIU serializadas


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
