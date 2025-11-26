"""
Atenção Simbólica: Foco Dinâmico Sem Pesos Neurais.

Em Transformers, a atenção é computada via:
    Attention(Q, K, V) = softmax(QK^T / sqrt(d)) * V

Isso requer pesos aprendidos para Q, K, V.

Nossa abordagem: Atenção por RELEVÂNCIA EXPLÍCITA

Mecanismos:
1. SALIÊNCIA: O que é importante no contexto atual?
2. RELEVÂNCIA: O que é relevante para a query?
3. RECÊNCIA: O que foi mencionado recentemente?
4. FREQUÊNCIA: O que aparece frequentemente?
5. SURPRESA: O que é inesperado/informativo?

Cada mecanismo produz scores de 0 a 1.
O score final é uma combinação desses fatores.

A atenção é INTERPRETÁVEL:
- Sabemos exatamente por que algo recebe atenção
- Não há "caixa preta" de pesos
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, FrozenSet, Iterator, List, Mapping, Set, Tuple
import math


class AttentionFactor(Enum):
    """Fatores que contribuem para atenção."""
    
    SALIENCE = auto()  # Importância intrínseca
    RELEVANCE = auto()  # Relevância para query
    RECENCY = auto()  # Quão recente
    FREQUENCY = auto()  # Quão frequente
    SURPRISE = auto()  # Quão inesperado
    POSITION = auto()  # Posição no contexto


@dataclass(frozen=True)
class AttentionScore:
    """Score de atenção para um item."""
    
    item: str
    total_score: float
    factors: Mapping[AttentionFactor, float]
    
    def top_factors(self, n: int = 3) -> List[Tuple[AttentionFactor, float]]:
        """Retorna os N fatores mais importantes."""
        sorted_factors = sorted(
            self.factors.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return sorted_factors[:n]
    
    def explain(self) -> str:
        """Explica por que este item recebeu atenção."""
        parts = [f"'{self.item}' (score: {self.total_score:.3f})"]
        
        for factor, score in self.top_factors(3):
            if score > 0.1:
                parts.append(f"  - {factor.name}: {score:.3f}")
        
        return "\n".join(parts)


@dataclass
class AttentionContext:
    """Contexto para computação de atenção."""
    
    query: str = ""
    history: List[str] = field(default_factory=list)
    focus_items: Set[str] = field(default_factory=set)
    position_map: Dict[str, int] = field(default_factory=dict)
    
    def add_to_history(self, item: str, position: int | None = None) -> None:
        self.history.append(item)
        if position is not None:
            self.position_map[item] = position
        else:
            self.position_map[item] = len(self.history) - 1
    
    def set_focus(self, *items: str) -> None:
        self.focus_items = set(items)
    
    def get_recency(self, item: str) -> float:
        """Retorna recência normalizada (1.0 = mais recente)."""
        if not self.history:
            return 0.0
        
        try:
            idx = self.history[::-1].index(item)
            return 1.0 - (idx / len(self.history))
        except ValueError:
            return 0.0


class SalienceComputer:
    """
    Computa saliência (importância intrínseca) de itens.
    
    Baseado em:
    - TF-IDF (mas sem pesos - contagens discretas)
    - Posição (início/fim são mais salientes)
    - Entidades nomeadas (se detectadas)
    """
    
    def __init__(self):
        self.document_frequency: Dict[str, int] = defaultdict(int)
        self.total_documents: int = 0
        self.salient_patterns: Set[str] = set()
    
    def learn_corpus(self, documents: List[List[str]]) -> None:
        """Aprende estatísticas do corpus."""
        for doc in documents:
            self.total_documents += 1
            unique_terms = set(doc)
            
            for term in unique_terms:
                self.document_frequency[term] += 1
    
    def add_salient_pattern(self, pattern: str) -> None:
        """Adiciona padrão reconhecido como saliente."""
        self.salient_patterns.add(pattern.lower())
    
    def compute(self, item: str, document: List[str]) -> float:
        """Computa saliência de um item no documento."""
        item_lower = item.lower()
        
        # Fator 1: IDF-like (quanto mais raro, mais saliente)
        df = self.document_frequency.get(item_lower, 0)
        
        if self.total_documents > 0 and df > 0:
            idf = math.log(self.total_documents / df) / math.log(self.total_documents + 1)
        else:
            idf = 1.0  # Item nunca visto = muito saliente
        
        # Fator 2: Posição no documento
        try:
            position = document.index(item)
            doc_len = len(document)
            
            # Início e fim são mais salientes
            if position < doc_len * 0.1:
                position_score = 1.0
            elif position > doc_len * 0.9:
                position_score = 0.8
            else:
                position_score = 0.5
        except ValueError:
            position_score = 0.0
        
        # Fator 3: Padrão saliente
        pattern_match = 1.0 if any(p in item_lower for p in self.salient_patterns) else 0.0
        
        # Fator 4: Características do token
        char_score = 0.0
        if item[0].isupper():
            char_score += 0.3  # Possível entidade
        if len(item) > 6:
            char_score += 0.2  # Palavras longas são mais específicas
        
        # Combinação (média ponderada)
        return (idf * 0.4 + position_score * 0.2 + pattern_match * 0.2 + char_score * 0.2)


class RelevanceComputer:
    """
    Computa relevância entre query e itens.
    
    Baseado em:
    - Overlap de termos
    - Co-ocorrência no corpus
    - Distância semântica (se taxonomia disponível)
    """
    
    def __init__(self):
        self.cooccurrence: Dict[Tuple[str, str], int] = defaultdict(int)
        self.term_counts: Dict[str, int] = defaultdict(int)
    
    def learn_cooccurrence(
        self,
        documents: List[List[str]],
        window_size: int = 5,
    ) -> None:
        """Aprende co-ocorrências do corpus."""
        for doc in documents:
            for i, term1 in enumerate(doc):
                self.term_counts[term1.lower()] += 1
                
                for j in range(max(0, i - window_size), min(len(doc), i + window_size + 1)):
                    if i != j:
                        term2 = doc[j]
                        pair = tuple(sorted([term1.lower(), term2.lower()]))
                        self.cooccurrence[pair] += 1
    
    def compute(self, query: str, item: str) -> float:
        """Computa relevância de item para query."""
        query_terms = set(query.lower().split())
        item_lower = item.lower()
        
        # Fator 1: Match direto
        if item_lower in query_terms:
            direct_match = 1.0
        elif any(item_lower in qt or qt in item_lower for qt in query_terms):
            direct_match = 0.7
        else:
            direct_match = 0.0
        
        # Fator 2: Co-ocorrência com termos da query
        cooc_score = 0.0
        
        for qt in query_terms:
            pair = tuple(sorted([qt, item_lower]))
            cooc = self.cooccurrence.get(pair, 0)
            
            if cooc > 0:
                # PMI simplificado
                total = sum(self.term_counts.values()) or 1
                p_joint = cooc / total
                p_qt = self.term_counts.get(qt, 1) / total
                p_item = self.term_counts.get(item_lower, 1) / total
                
                pmi = math.log(p_joint / (p_qt * p_item + 1e-10) + 1)
                cooc_score = max(cooc_score, min(1.0, pmi / 5))  # Normaliza
        
        # Combinação
        return direct_match * 0.6 + cooc_score * 0.4


class SurpriseComputer:
    """
    Computa surpresa (valor informacional) de itens.
    
    Baseado em teoria da informação:
    - Surpresa = -log(P(item))
    - Quanto menos provável, mais surpreendente/informativo
    """
    
    def __init__(self):
        self.item_counts: Dict[str, int] = defaultdict(int)
        self.transition_counts: Dict[Tuple[str, str], int] = defaultdict(int)
        self.total_items: int = 0
    
    def learn_distribution(self, sequences: List[List[str]]) -> None:
        """Aprende distribuição de probabilidades."""
        for seq in sequences:
            for i, item in enumerate(seq):
                item_lower = item.lower()
                self.item_counts[item_lower] += 1
                self.total_items += 1
                
                if i > 0:
                    prev = seq[i - 1].lower()
                    self.transition_counts[(prev, item_lower)] += 1
    
    def compute(self, item: str, previous_item: str | None = None) -> float:
        """Computa surpresa de um item."""
        item_lower = item.lower()
        
        if self.total_items == 0:
            return 0.5  # Incerteza total
        
        # Probabilidade marginal
        count = self.item_counts.get(item_lower, 0)
        
        if count == 0:
            # Nunca visto = máxima surpresa
            return 1.0
        
        p_marginal = count / self.total_items
        surprise_marginal = -math.log2(p_marginal) / math.log2(self.total_items + 1)
        
        # Se há contexto, usa probabilidade condicional
        if previous_item is not None:
            prev_lower = previous_item.lower()
            trans_count = self.transition_counts.get((prev_lower, item_lower), 0)
            prev_count = self.item_counts.get(prev_lower, 1)
            
            if trans_count > 0:
                p_conditional = trans_count / prev_count
                surprise_conditional = -math.log2(p_conditional + 0.01)
                
                # Média das duas surpresas
                return min(1.0, (surprise_marginal + surprise_conditional / 10) / 2)
        
        return min(1.0, surprise_marginal)


class SymbolicAttention:
    """
    Motor de atenção simbólica principal.
    
    Combina múltiplos fatores para determinar onde focar.
    Totalmente interpretável e sem pesos neurais.
    """
    
    def __init__(self):
        self.salience = SalienceComputer()
        self.relevance = RelevanceComputer()
        self.surprise = SurpriseComputer()
        
        # Pesos dos fatores (fixos, não aprendidos)
        self.factor_weights = {
            AttentionFactor.SALIENCE: 0.2,
            AttentionFactor.RELEVANCE: 0.35,
            AttentionFactor.RECENCY: 0.15,
            AttentionFactor.FREQUENCY: 0.1,
            AttentionFactor.SURPRISE: 0.1,
            AttentionFactor.POSITION: 0.1,
        }
    
    def learn_corpus(self, documents: List[List[str]]) -> None:
        """Aprende estatísticas do corpus."""
        self.salience.learn_corpus(documents)
        self.relevance.learn_cooccurrence(documents)
        self.surprise.learn_distribution(documents)
    
    def attend(
        self,
        items: List[str],
        context: AttentionContext,
        top_k: int | None = None,
    ) -> List[AttentionScore]:
        """
        Computa atenção sobre uma lista de itens.
        
        Retorna scores ordenados por atenção (maior primeiro).
        """
        scores = []
        
        # Computa frequência local
        freq = defaultdict(int)
        for item in items:
            freq[item.lower()] += 1
        
        max_freq = max(freq.values()) if freq else 1
        
        for i, item in enumerate(items):
            factors = {}
            
            # Saliência
            factors[AttentionFactor.SALIENCE] = self.salience.compute(item, items)
            
            # Relevância
            if context.query:
                factors[AttentionFactor.RELEVANCE] = self.relevance.compute(
                    context.query, item
                )
            else:
                factors[AttentionFactor.RELEVANCE] = 0.0
            
            # Recência
            factors[AttentionFactor.RECENCY] = context.get_recency(item)
            
            # Frequência (normalizada)
            factors[AttentionFactor.FREQUENCY] = freq[item.lower()] / max_freq
            
            # Surpresa
            prev_item = items[i - 1] if i > 0 else None
            factors[AttentionFactor.SURPRISE] = self.surprise.compute(item, prev_item)
            
            # Posição
            pos_score = 1.0 - (i / len(items)) if items else 0.0
            factors[AttentionFactor.POSITION] = pos_score
            
            # Boost para itens em foco
            if item in context.focus_items:
                for f in factors:
                    factors[f] = min(1.0, factors[f] * 1.5)
            
            # Score total (soma ponderada)
            total = sum(
                factors[f] * self.factor_weights[f]
                for f in AttentionFactor
            )
            
            scores.append(AttentionScore(
                item=item,
                total_score=total,
                factors=factors,
            ))
        
        # Ordena por score
        scores.sort(key=lambda x: x.total_score, reverse=True)
        
        if top_k is not None:
            return scores[:top_k]
        
        return scores
    
    def focus(
        self,
        items: List[str],
        context: AttentionContext,
        threshold: float = 0.3,
    ) -> List[str]:
        """Retorna apenas itens acima do threshold de atenção."""
        scores = self.attend(items, context)
        return [s.item for s in scores if s.total_score >= threshold]
    
    def explain_attention(
        self,
        items: List[str],
        context: AttentionContext,
        top_k: int = 5,
    ) -> str:
        """Gera explicação textual da atenção."""
        scores = self.attend(items, context, top_k)
        
        lines = [
            f"Query: '{context.query}'",
            f"Itens analisados: {len(items)}",
            f"Top {top_k} por atenção:",
            "",
        ]
        
        for i, score in enumerate(scores, 1):
            lines.append(f"{i}. {score.explain()}")
            lines.append("")
        
        return "\n".join(lines)


class AttentionHead:
    """
    Um "head" de atenção focado em um tipo de relevância.
    
    Similar a multi-head attention, mas sem pesos.
    Cada head foca em um aspecto diferente.
    """
    
    def __init__(
        self,
        name: str,
        primary_factor: AttentionFactor,
        weight: float = 1.0,
    ):
        self.name = name
        self.primary_factor = primary_factor
        self.weight = weight
        self.attention = SymbolicAttention()
        
        # Ajusta pesos para enfatizar o fator primário
        for f in AttentionFactor:
            if f == primary_factor:
                self.attention.factor_weights[f] = 0.6
            else:
                self.attention.factor_weights[f] = 0.4 / (len(AttentionFactor) - 1)
    
    def attend(
        self,
        items: List[str],
        context: AttentionContext,
    ) -> List[AttentionScore]:
        return self.attention.attend(items, context)


class MultiHeadSymbolicAttention:
    """
    Atenção multi-head simbólica.
    
    Combina múltiplos heads, cada um focando em um aspecto.
    Similar a Transformers, mas sem pesos aprendidos.
    """
    
    def __init__(self):
        self.heads: List[AttentionHead] = [
            AttentionHead("relevance", AttentionFactor.RELEVANCE, 1.0),
            AttentionHead("salience", AttentionFactor.SALIENCE, 0.8),
            AttentionHead("recency", AttentionFactor.RECENCY, 0.6),
            AttentionHead("surprise", AttentionFactor.SURPRISE, 0.4),
        ]
    
    def learn_corpus(self, documents: List[List[str]]) -> None:
        for head in self.heads:
            head.attention.learn_corpus(documents)
    
    def attend(
        self,
        items: List[str],
        context: AttentionContext,
        top_k: int | None = None,
    ) -> List[AttentionScore]:
        """Combina atenção de todos os heads."""
        # Coleta scores de cada head
        all_scores: Dict[str, List[float]] = defaultdict(list)
        all_factors: Dict[str, Dict[AttentionFactor, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        
        for head in self.heads:
            head_scores = head.attend(items, context)
            
            for score in head_scores:
                all_scores[score.item].append(score.total_score * head.weight)
                
                for factor, value in score.factors.items():
                    all_factors[score.item][factor].append(value)
        
        # Combina scores (média ponderada)
        total_weight = sum(h.weight for h in self.heads)
        
        combined = []
        for item in items:
            if item not in all_scores:
                continue
            
            total = sum(all_scores[item]) / total_weight
            
            factors = {
                f: sum(all_factors[item][f]) / len(all_factors[item][f])
                for f in AttentionFactor
                if all_factors[item][f]
            }
            
            combined.append(AttentionScore(
                item=item,
                total_score=total,
                factors=factors,
            ))
        
        combined.sort(key=lambda x: x.total_score, reverse=True)
        
        if top_k is not None:
            return combined[:top_k]
        
        return combined


__all__ = [
    "AttentionFactor",
    "AttentionScore",
    "AttentionContext",
    "SalienceComputer",
    "RelevanceComputer",
    "SurpriseComputer",
    "SymbolicAttention",
    "AttentionHead",
    "MultiHeadSymbolicAttention",
]
