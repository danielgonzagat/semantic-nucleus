"""
Grafo de Co-ocorrência Discreto.

Em vez de embeddings (vetores densos aprendidos por redes neurais),
usamos um grafo esparso onde:
- Nós = tokens/conceitos
- Arestas = co-ocorrências com contagem discreta
- Pesos = contagens inteiras, NÃO floats aprendidos

A "semântica" emerge da estrutura do grafo:
- Tokens que co-ocorrem frequentemente estão "próximos"
- Caminhos no grafo representam relações transitivas
- Clusters representam campos semânticos

Isso é similar a word2vec/GloVe, mas SEM:
- Gradientes
- Backpropagation
- Matrizes de embedding
- Treinamento iterativo
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from heapq import nlargest, nsmallest
from typing import Dict, FrozenSet, Iterator, List, Mapping, Sequence, Set, Tuple


@dataclass(frozen=True, slots=True)
class GraphNode:
    """Um nó no grafo de co-ocorrência."""
    
    token: str
    frequency: int
    
    def __hash__(self) -> int:
        return hash(self.token)
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, GraphNode):
            return self.token == other.token
        return False


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """Uma aresta no grafo (co-ocorrência)."""
    
    source: str
    target: str
    count: int  # Contagem discreta, não peso contínuo
    pmi: float  # PMI (Pointwise Mutual Information) - derivado, não aprendido
    
    @property
    def strength(self) -> float:
        """Força da associação baseada em PMI e contagem."""
        return self.pmi * math.log1p(self.count)


@dataclass(slots=True)
class CooccurrenceGraph:
    """
    Grafo de co-ocorrência para representação semântica discreta.
    
    Substitui embeddings neurais por estrutura de grafo explícita.
    Toda a "semântica" vem de contagens e relações estruturais.
    """
    
    # Contagens de tokens
    token_counts: Counter[str] = field(default_factory=Counter)
    
    # Contagens de co-ocorrência (token1, token2) -> count
    cooc_counts: Dict[FrozenSet[str], int] = field(default_factory=lambda: defaultdict(int))
    
    # Contagens direcionais para ordem
    directed_counts: Dict[Tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    
    # Total de tokens vistos
    total_tokens: int = 0
    
    # Total de janelas de co-ocorrência
    total_windows: int = 0
    
    # Cache de PMI
    _pmi_cache: Dict[FrozenSet[str], float] = field(default_factory=dict)
    
    def add_document(
        self,
        tokens: Sequence[str],
        window_size: int = 5,
    ) -> None:
        """
        Adiciona um documento ao grafo.
        
        Usa janela deslizante para capturar co-ocorrências locais.
        """
        if len(tokens) < 2:
            return
        
        # Atualiza contagens de tokens
        for token in tokens:
            self.token_counts[token] += 1
            self.total_tokens += 1
        
        # Atualiza co-ocorrências em janela deslizante
        for i, center in enumerate(tokens):
            start = max(0, i - window_size)
            end = min(len(tokens), i + window_size + 1)
            
            for j in range(start, end):
                if i == j:
                    continue
                
                context = tokens[j]
                pair = frozenset([center, context])
                self.cooc_counts[pair] += 1
                
                # Direção importa para algumas análises
                self.directed_counts[(center, context)] += 1
            
            self.total_windows += 1
        
        # Invalida cache
        self._pmi_cache.clear()
    
    def add_corpus(
        self,
        documents: Sequence[Sequence[str]],
        window_size: int = 5,
    ) -> None:
        """Adiciona múltiplos documentos."""
        for doc in documents:
            self.add_document(doc, window_size)
    
    def pmi(self, token1: str, token2: str) -> float:
        """
        Calcula PMI (Pointwise Mutual Information) entre dois tokens.
        
        PMI(x,y) = log(P(x,y) / (P(x) * P(y)))
        
        PMI positivo = tokens co-ocorrem mais que o esperado
        PMI negativo = tokens co-ocorrem menos que o esperado
        """
        pair = frozenset([token1, token2])
        
        if pair in self._pmi_cache:
            return self._pmi_cache[pair]
        
        count1 = self.token_counts.get(token1, 0)
        count2 = self.token_counts.get(token2, 0)
        cooc = self.cooc_counts.get(pair, 0)
        
        if count1 == 0 or count2 == 0 or cooc == 0 or self.total_tokens == 0:
            return 0.0
        
        # Probabilidades
        p1 = count1 / self.total_tokens
        p2 = count2 / self.total_tokens
        p_cooc = cooc / max(1, self.total_windows)
        
        # PMI
        expected = p1 * p2
        if expected == 0:
            return 0.0
        
        pmi_value = math.log2(p_cooc / expected) if p_cooc > 0 else -10.0
        
        self._pmi_cache[pair] = pmi_value
        return pmi_value
    
    def ppmi(self, token1: str, token2: str) -> float:
        """PMI positivo (trunca valores negativos)."""
        return max(0.0, self.pmi(token1, token2))
    
    def npmi(self, token1: str, token2: str) -> float:
        """
        Normalized PMI (entre -1 e 1).
        
        NPMI = PMI / -log(P(x,y))
        """
        pair = frozenset([token1, token2])
        cooc = self.cooc_counts.get(pair, 0)
        
        if cooc == 0 or self.total_windows == 0:
            return 0.0
        
        p_cooc = cooc / self.total_windows
        pmi_val = self.pmi(token1, token2)
        
        if p_cooc <= 0:
            return 0.0
        
        denominator = -math.log2(p_cooc)
        if denominator == 0:
            return 0.0
        
        return pmi_val / denominator
    
    def neighbors(
        self,
        token: str,
        top_k: int = 10,
        min_cooc: int = 2,
    ) -> List[Tuple[str, float]]:
        """
        Retorna os vizinhos mais fortemente associados a um token.
        
        Usa PPMI como medida de associação.
        """
        if token not in self.token_counts:
            return []
        
        candidates = []
        
        for pair, count in self.cooc_counts.items():
            if count < min_cooc:
                continue
            
            tokens = list(pair)
            if token not in tokens:
                continue
            
            other = tokens[0] if tokens[1] == token else tokens[1]
            ppmi_val = self.ppmi(token, other)
            
            if ppmi_val > 0:
                candidates.append((other, ppmi_val))
        
        # Retorna top-k por PPMI
        return nlargest(top_k, candidates, key=lambda x: x[1])
    
    def similarity(self, token1: str, token2: str) -> float:
        """
        Calcula similaridade entre dois tokens baseado em vizinhança compartilhada.
        
        Usa Jaccard sobre vizinhos com PPMI > 0.
        Isso é análogo a similaridade de cosseno em embeddings,
        mas puramente baseado em estrutura de grafo.
        """
        if token1 == token2:
            return 1.0
        
        if token1 not in self.token_counts or token2 not in self.token_counts:
            return 0.0
        
        # Obtém vizinhos de cada token
        neighbors1 = {n for n, _ in self.neighbors(token1, top_k=50, min_cooc=1)}
        neighbors2 = {n for n, _ in self.neighbors(token2, top_k=50, min_cooc=1)}
        
        if not neighbors1 and not neighbors2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(neighbors1 & neighbors2)
        union = len(neighbors1 | neighbors2)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def semantic_field(
        self,
        seed_tokens: Sequence[str],
        expansion_rounds: int = 2,
        top_k_per_round: int = 5,
        min_similarity: float = 0.1,
    ) -> Set[str]:
        """
        Expande um conjunto de tokens para um campo semântico.
        
        Similar a encontrar um cluster, mas via propagação de vizinhança.
        """
        field = set(seed_tokens)
        frontier = set(seed_tokens)
        
        for _ in range(expansion_rounds):
            new_frontier = set()
            
            for token in frontier:
                for neighbor, score in self.neighbors(token, top_k=top_k_per_round):
                    if neighbor in field:
                        continue
                    
                    # Verifica similaridade média com o campo
                    avg_sim = sum(
                        self.similarity(neighbor, existing)
                        for existing in field
                    ) / len(field)
                    
                    if avg_sim >= min_similarity:
                        new_frontier.add(neighbor)
            
            field.update(new_frontier)
            frontier = new_frontier
            
            if not frontier:
                break
        
        return field
    
    def path_strength(self, source: str, target: str, max_hops: int = 3) -> float:
        """
        Calcula força de conexão entre dois tokens via caminhos.
        
        Isso captura relações transitivas que embeddings capturam
        implicitamente via multiplicação de matrizes.
        """
        if source == target:
            return 1.0
        
        # PMI direto
        direct_pmi = self.ppmi(source, target)
        if direct_pmi > 0:
            return direct_pmi
        
        # BFS para encontrar caminhos
        if max_hops <= 1:
            return 0.0
        
        visited = {source}
        current_level = {source}
        path_scores: List[float] = []
        
        for hop in range(max_hops):
            next_level = set()
            
            for node in current_level:
                for neighbor, score in self.neighbors(node, top_k=10):
                    if neighbor in visited:
                        continue
                    
                    if neighbor == target:
                        # Encontrou caminho
                        path_score = score / (hop + 2)  # Decay por distância
                        path_scores.append(path_score)
                    else:
                        next_level.add(neighbor)
            
            visited.update(next_level)
            current_level = next_level
            
            if not current_level:
                break
        
        if path_scores:
            return max(path_scores)
        return 0.0
    
    def get_edge(self, token1: str, token2: str) -> GraphEdge | None:
        """Retorna a aresta entre dois tokens, se existir."""
        pair = frozenset([token1, token2])
        count = self.cooc_counts.get(pair, 0)
        
        if count == 0:
            return None
        
        return GraphEdge(
            source=token1,
            target=token2,
            count=count,
            pmi=self.pmi(token1, token2),
        )
    
    def get_node(self, token: str) -> GraphNode | None:
        """Retorna um nó do grafo."""
        freq = self.token_counts.get(token, 0)
        if freq == 0:
            return None
        return GraphNode(token=token, frequency=freq)
    
    def most_central(self, top_k: int = 20) -> List[Tuple[str, float]]:
        """
        Retorna os tokens mais centrais (maior soma de PPMI).
        
        Centralidade baseada em conexões semânticas, não apenas frequência.
        """
        centrality: Dict[str, float] = defaultdict(float)
        
        for pair, count in self.cooc_counts.items():
            tokens = list(pair)
            if len(tokens) != 2:
                continue
            
            ppmi_val = self.ppmi(tokens[0], tokens[1])
            centrality[tokens[0]] += ppmi_val
            centrality[tokens[1]] += ppmi_val
        
        return nlargest(top_k, centrality.items(), key=lambda x: x[1])
    
    def stats(self) -> Dict[str, int | float]:
        """Estatísticas do grafo."""
        return {
            "total_tokens": self.total_tokens,
            "unique_tokens": len(self.token_counts),
            "total_edges": len(self.cooc_counts),
            "total_windows": self.total_windows,
            "avg_cooc": (
                sum(self.cooc_counts.values()) / len(self.cooc_counts)
                if self.cooc_counts else 0.0
            ),
        }


__all__ = ["CooccurrenceGraph", "GraphNode", "GraphEdge"]
