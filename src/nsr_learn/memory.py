"""
Memória Associativa Discreta.

Substitui o paradigma de "memória como pesos em matrizes" por
um sistema explícito de armazenamento e recuperação.

Em redes neurais, a "memória" está implícita nos pesos:
- Armazenamento = ajuste de pesos via gradiente
- Recuperação = propagação forward

Aqui, a memória é EXPLÍCITA e INTERPRETÁVEL:
- Armazenamento = indexação de estruturas simbólicas
- Recuperação = matching de padrões + ranking

Isso é similar a:
- Hopfield Networks (versão discreta)
- Memory Networks (sem embeddings)
- Retrieval-Augmented Generation (sem neural retriever)

A vantagem: podemos EXPLICAR por que algo foi recuperado.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from hashlib import blake2b
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)


@dataclass(frozen=True)
class MemoryTrace:
    """
    Um traço de memória armazenado.
    
    Contém:
    - Chave: padrão usado para recuperação
    - Valor: conteúdo associado
    - Contexto: metadados sobre quando/como foi armazenado
    - Força: força da memória (decai com tempo, aumenta com reforço)
    """
    
    key: Tuple[str, ...]  # Padrão de acesso
    value: Any  # Conteúdo armazenado
    context: Tuple[str, ...] = ()  # Contexto de armazenamento
    strength: float = 1.0  # Força da memória
    timestamp: int = 0  # Quando foi armazenado
    access_count: int = 0  # Quantas vezes foi acessado
    
    @property
    def id(self) -> str:
        hasher = blake2b(digest_size=8)
        for k in self.key:
            hasher.update(k.encode("utf-8"))
        hasher.update(str(self.value).encode("utf-8"))
        return f"M{hasher.hexdigest()[:8]}"
    
    def with_strength(self, new_strength: float) -> "MemoryTrace":
        return MemoryTrace(
            key=self.key,
            value=self.value,
            context=self.context,
            strength=new_strength,
            timestamp=self.timestamp,
            access_count=self.access_count,
        )
    
    def with_access(self) -> "MemoryTrace":
        return MemoryTrace(
            key=self.key,
            value=self.value,
            context=self.context,
            strength=self.strength,
            timestamp=self.timestamp,
            access_count=self.access_count + 1,
        )


@dataclass(frozen=True)
class RetrievalResult:
    """Resultado de uma recuperação de memória."""
    
    trace: MemoryTrace
    match_score: float  # Quão bem a query casou com a chave
    relevance: float  # Score final considerando força e recência
    matched_terms: Tuple[str, ...]  # Termos que casaram
    
    @property
    def value(self) -> Any:
        return self.trace.value


@dataclass()
class AssociativeMemory:
    """
    Memória associativa discreta com múltiplos índices.
    
    Funciona como uma combinação de:
    - Memória episódica: lembra eventos específicos
    - Memória semântica: generaliza padrões
    - Memória de trabalho: mantém contexto recente
    
    Recuperação é baseada em:
    1. Matching de padrões (interseção de tokens)
    2. Força da memória (recência + frequência)
    3. Contexto atual (boost para memórias relacionadas)
    """
    
    # Armazenamento principal
    traces: Dict[str, MemoryTrace] = field(default_factory=dict)
    
    # Índice invertido: token -> ids das memórias
    token_index: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    
    # Índice de contexto: contexto -> ids das memórias
    context_index: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    
    # Contador de timestamp
    _timestamp: int = 0
    
    # Parâmetros
    max_traces: int = 10000
    decay_rate: float = 0.999  # Decaimento por acesso
    reinforcement_rate: float = 1.5  # Reforço por re-armazenamento
    
    def store(
        self,
        key: Sequence[str],
        value: Any,
        context: Sequence[str] = (),
        strength: float = 1.0,
    ) -> MemoryTrace:
        """
        Armazena um par chave-valor na memória.
        
        Se a chave já existe, reforça a memória existente.
        """
        self._timestamp += 1
        key_tuple = tuple(key)
        context_tuple = tuple(context)
        
        # Verifica se já existe memória similar
        existing = self._find_exact_match(key_tuple, value)
        
        if existing is not None:
            # Reforça memória existente
            old_trace = self.traces[existing]
            new_strength = min(10.0, old_trace.strength * self.reinforcement_rate)
            new_trace = MemoryTrace(
                key=key_tuple,
                value=value,
                context=context_tuple,
                strength=new_strength,
                timestamp=self._timestamp,
                access_count=old_trace.access_count,
            )
            self.traces[existing] = new_trace
            return new_trace
        
        # Cria nova memória
        trace = MemoryTrace(
            key=key_tuple,
            value=value,
            context=context_tuple,
            strength=strength,
            timestamp=self._timestamp,
            access_count=0,
        )
        
        trace_id = trace.id
        
        # Verifica limite de capacidade
        if len(self.traces) >= self.max_traces:
            self._evict_weakest()
        
        # Armazena
        self.traces[trace_id] = trace
        
        # Atualiza índices
        for token in key_tuple:
            self.token_index[token].add(trace_id)
        
        for ctx in context_tuple:
            self.context_index[ctx].add(trace_id)
        
        return trace
    
    def retrieve(
        self,
        query: Sequence[str],
        context: Sequence[str] = (),
        top_k: int = 5,
        min_match: float = 0.1,
    ) -> List[RetrievalResult]:
        """
        Recupera memórias relevantes para uma query.
        
        Usa matching baseado em:
        1. Interseção de tokens (Jaccard)
        2. Força da memória
        3. Contexto atual
        """
        if not query:
            return []
        
        query_set = set(query)
        context_set = set(context)
        
        # Encontra candidatos via índice invertido
        candidate_ids: Set[str] = set()
        for token in query:
            if token in self.token_index:
                candidate_ids.update(self.token_index[token])
        
        # Adiciona candidatos do contexto
        for ctx in context:
            if ctx in self.context_index:
                candidate_ids.update(self.context_index[ctx])
        
        if not candidate_ids:
            return []
        
        # Pontua cada candidato
        results = []
        
        for trace_id in candidate_ids:
            if trace_id not in self.traces:
                continue
            
            trace = self.traces[trace_id]
            
            # Match score: Jaccard entre query e key
            key_set = set(trace.key)
            intersection = len(query_set & key_set)
            union = len(query_set | key_set)
            match_score = intersection / union if union > 0 else 0.0
            
            if match_score < min_match:
                continue
            
            # Context boost
            context_boost = 1.0
            if trace.context and context_set:
                ctx_match = len(set(trace.context) & context_set)
                context_boost = 1.0 + (0.2 * ctx_match)
            
            # Recency boost
            recency = 1.0 / (1.0 + math.log1p(self._timestamp - trace.timestamp))
            
            # Frequência boost
            frequency_boost = 1.0 + (0.1 * trace.access_count)
            
            # Score final
            relevance = (
                match_score
                * trace.strength
                * context_boost
                * recency
                * frequency_boost
            )
            
            matched_terms = tuple(query_set & key_set)
            
            results.append(RetrievalResult(
                trace=trace,
                match_score=match_score,
                relevance=relevance,
                matched_terms=matched_terms,
            ))
        
        # Ordena por relevância e retorna top-k
        results.sort(key=lambda r: -r.relevance)
        
        # Atualiza contadores de acesso para resultados retornados
        for result in results[:top_k]:
            trace_id = result.trace.id
            if trace_id in self.traces:
                updated = self.traces[trace_id].with_access()
                self.traces[trace_id] = updated
        
        return results[:top_k]
    
    def associate(
        self,
        pattern1: Sequence[str],
        pattern2: Sequence[str],
        strength: float = 1.0,
    ) -> None:
        """
        Cria associação bidirecional entre dois padrões.
        
        Similar a aprendizado Hebbiano: "neurons that fire together wire together"
        Mas EXPLÍCITO em vez de via ajuste de pesos.
        """
        # Armazena pattern1 -> pattern2
        self.store(
            key=pattern1,
            value=pattern2,
            context=pattern2,
            strength=strength,
        )
        
        # Armazena pattern2 -> pattern1
        self.store(
            key=pattern2,
            value=pattern1,
            context=pattern1,
            strength=strength,
        )
    
    def complete(
        self,
        partial: Sequence[str],
        context: Sequence[str] = (),
    ) -> Tuple[str, ...] | None:
        """
        Completa um padrão parcial usando memórias armazenadas.
        
        Similar a pattern completion em Hopfield networks,
        mas via retrieval explícito.
        """
        results = self.retrieve(partial, context=context, top_k=1)
        
        if not results:
            return None
        
        best = results[0]
        
        # Se o valor é uma sequência, retorna como completamento
        if isinstance(best.value, (list, tuple)):
            return tuple(best.value)
        
        return (str(best.value),)
    
    def decay_all(self) -> int:
        """
        Aplica decaimento a todas as memórias.
        
        Memórias fracas eventualmente são esquecidas.
        Retorna número de memórias removidas.
        """
        to_remove = []
        
        for trace_id, trace in self.traces.items():
            new_strength = trace.strength * self.decay_rate
            
            if new_strength < 0.01:
                to_remove.append(trace_id)
            else:
                self.traces[trace_id] = trace.with_strength(new_strength)
        
        for trace_id in to_remove:
            self._remove_trace(trace_id)
        
        return len(to_remove)
    
    def consolidate(
        self,
        min_access: int = 2,
        min_strength: float = 0.5,
    ) -> List[Tuple[Tuple[str, ...], Any]]:
        """
        Consolida memórias frequentes em memória de longo prazo.
        
        Retorna padrões consolidados (para possível extração de regras).
        """
        consolidated = []
        
        for trace_id, trace in self.traces.items():
            if trace.access_count >= min_access and trace.strength >= min_strength:
                consolidated.append((trace.key, trace.value))
        
        return consolidated
    
    def _find_exact_match(self, key: Tuple[str, ...], value: Any) -> str | None:
        """Encontra memória com mesma chave e valor."""
        for trace_id, trace in self.traces.items():
            if trace.key == key and trace.value == value:
                return trace_id
        return None
    
    def _evict_weakest(self) -> None:
        """Remove a memória mais fraca."""
        if not self.traces:
            return
        
        weakest_id = min(
            self.traces.keys(),
            key=lambda tid: self.traces[tid].strength,
        )
        
        self._remove_trace(weakest_id)
    
    def _remove_trace(self, trace_id: str) -> None:
        """Remove uma memória e atualiza índices."""
        if trace_id not in self.traces:
            return
        
        trace = self.traces[trace_id]
        
        # Remove dos índices
        for token in trace.key:
            if token in self.token_index:
                self.token_index[token].discard(trace_id)
        
        for ctx in trace.context:
            if ctx in self.context_index:
                self.context_index[ctx].discard(trace_id)
        
        del self.traces[trace_id]
    
    def stats(self) -> Dict[str, int | float]:
        """Estatísticas da memória."""
        if not self.traces:
            return {
                "total_traces": 0,
                "avg_strength": 0.0,
                "avg_access_count": 0.0,
                "unique_tokens": 0,
            }
        
        strengths = [t.strength for t in self.traces.values()]
        accesses = [t.access_count for t in self.traces.values()]
        
        return {
            "total_traces": len(self.traces),
            "avg_strength": sum(strengths) / len(strengths),
            "avg_access_count": sum(accesses) / len(accesses),
            "unique_tokens": len(self.token_index),
            "unique_contexts": len(self.context_index),
        }
    
    def __len__(self) -> int:
        return len(self.traces)
    
    def __contains__(self, key: Sequence[str]) -> bool:
        results = self.retrieve(key, top_k=1, min_match=0.9)
        return len(results) > 0


__all__ = ["AssociativeMemory", "MemoryTrace", "RetrievalResult"]
