"""
Motor Principal de Aprendizado Simbólico.

Integra todos os componentes:
- Compressor MDL
- Grafo de Co-ocorrência
- Indutor de Regras
- Memória Associativa

Para criar um sistema que APRENDE de dados sem usar pesos neurais.

O "treinamento" consiste em:
1. Comprimir o corpus (extrai padrões frequentes)
2. Construir grafo de co-ocorrência (captura semântica local)
3. Induzir regras simbólicas (generaliza padrões)
4. Popular memória associativa (indexa conhecimento)

A "inferência" consiste em:
1. Recuperar memórias relevantes
2. Aplicar regras aprendidas
3. Usar grafo para expansão semântica
4. Compor resposta

Hipótese central: Se conseguimos COMPRIMIR bem os dados,
conseguimos GENERALIZAR para novos dados.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from hashlib import blake2b
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Sequence, Set, Tuple

from .compressor import CompressionResult, MDLCompressor
from .graph import CooccurrenceGraph
from .inductor import Condition, RuleInductor, RuleSet, SymbolicRule
from .memory import AssociativeMemory, MemoryTrace, RetrievalResult


# Tokenização simples
TOKEN_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+|[!?.,;:]")


def tokenize(text: str) -> List[str]:
    """Tokeniza texto em palavras e pontuação."""
    return [m.group(0).lower() for m in TOKEN_PATTERN.finditer(text)]


@dataclass(frozen=True, slots=True)
class LearningConfig:
    """Configuração do motor de aprendizado."""
    
    # Compressor
    min_pattern_freq: int = 2
    max_pattern_length: int = 16
    max_dictionary_size: int = 10000
    
    # Grafo
    cooc_window_size: int = 5
    
    # Indução de regras
    min_rule_support: int = 2
    min_rule_confidence: float = 0.5
    max_rule_antecedents: int = 4
    max_rules: int = 1000
    
    # Memória
    max_memory_traces: int = 10000
    memory_decay_rate: float = 0.999
    
    # Geral
    max_response_tokens: int = 100


@dataclass(slots=True)
class LearningState:
    """Estado atual do sistema de aprendizado."""
    
    # Componentes
    compressor: MDLCompressor = field(default_factory=MDLCompressor)
    graph: CooccurrenceGraph = field(default_factory=CooccurrenceGraph)
    inductor: RuleInductor = field(default_factory=RuleInductor)
    memory: AssociativeMemory = field(default_factory=AssociativeMemory)
    rules: RuleSet = field(default_factory=RuleSet)
    
    # Estatísticas
    documents_seen: int = 0
    tokens_seen: int = 0
    queries_processed: int = 0
    
    # Vocabulário
    vocabulary: Set[str] = field(default_factory=set)
    
    def digest(self) -> str:
        """Hash do estado atual."""
        hasher = blake2b(digest_size=16)
        hasher.update(f"docs:{self.documents_seen}".encode())
        hasher.update(f"tokens:{self.tokens_seen}".encode())
        hasher.update(f"vocab:{len(self.vocabulary)}".encode())
        hasher.update(f"rules:{len(self.rules)}".encode())
        hasher.update(f"memory:{len(self.memory)}".encode())
        return hasher.hexdigest()


@dataclass(slots=True)
class QueryResult:
    """Resultado de uma query ao sistema."""
    
    query: str
    response: str
    confidence: float
    reasoning: List[str]  # Passos de raciocínio (interpretável!)
    retrieved_memories: List[RetrievalResult]
    applied_rules: List[SymbolicRule]
    similar_patterns: List[Tuple[str, float]]


class LearningEngine:
    """
    Motor de aprendizado simbólico sem pesos neurais.
    
    Este é o componente central que orquestra todos os outros.
    
    Fluxo de "treinamento":
        1. Recebe corpus de textos
        2. Tokeniza e indexa
        3. Comprime (aprende padrões)
        4. Constrói grafo (aprende associações)
        5. Induz regras (aprende generalizações)
        6. Popula memória (armazena conhecimento)
    
    Fluxo de "inferência":
        1. Recebe query
        2. Recupera memórias relevantes
        3. Aplica regras
        4. Expande via grafo
        5. Compõe resposta
        6. Explica raciocínio
    """
    
    def __init__(self, config: LearningConfig | None = None):
        self.config = config or LearningConfig()
        self.state = LearningState()
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Inicializa componentes com configuração."""
        self.state.compressor = MDLCompressor(
            min_pattern_freq=self.config.min_pattern_freq,
            max_pattern_length=self.config.max_pattern_length,
            max_dictionary_size=self.config.max_dictionary_size,
        )
        
        self.state.inductor = RuleInductor(
            min_support=self.config.min_rule_support,
            min_confidence=self.config.min_rule_confidence,
            max_antecedents=self.config.max_rule_antecedents,
            max_rules=self.config.max_rules,
        )
        
        self.state.memory = AssociativeMemory(
            max_traces=self.config.max_memory_traces,
            decay_rate=self.config.memory_decay_rate,
        )
    
    # =========================================================================
    # APRENDIZADO (equivalente a "treinamento")
    # =========================================================================
    
    def learn(self, corpus: Sequence[str]) -> Dict[str, Any]:
        """
        Aprende de um corpus de textos.
        
        Este é o equivalente ao "treinamento" de um modelo neural,
        mas sem gradientes, pesos, ou backpropagation.
        
        Retorna estatísticas do aprendizado.
        """
        if not corpus:
            return {"status": "empty_corpus"}
        
        # 1. Tokeniza todos os documentos
        tokenized = [tokenize(doc) for doc in corpus]
        
        # 2. Atualiza vocabulário
        for doc_tokens in tokenized:
            self.state.vocabulary.update(doc_tokens)
            self.state.tokens_seen += len(doc_tokens)
        
        self.state.documents_seen += len(corpus)
        
        # 3. Comprime (aprende padrões frequentes)
        compression_result = self.state.compressor.learn(tokenized)
        
        # 4. Constrói grafo de co-ocorrência (aprende associações)
        self.state.graph.add_corpus(tokenized, window_size=self.config.cooc_window_size)
        
        # 5. Induz regras simbólicas (aprende generalizações)
        self.state.rules = self.state.inductor.induce_from_sequences(tokenized)
        
        # 6. Popula memória com padrões importantes
        self._populate_memory(tokenized, compression_result)
        
        # 7. Cria associações entre tokens co-ocorrentes
        self._create_associations(tokenized)
        
        return {
            "status": "learned",
            "documents": len(corpus),
            "tokens": self.state.tokens_seen,
            "vocabulary_size": len(self.state.vocabulary),
            "patterns_found": len(compression_result.patterns),
            "compression_ratio": compression_result.compression_ratio,
            "rules_induced": len(self.state.rules),
            "memory_traces": len(self.state.memory),
            "state_digest": self.state.digest(),
        }
    
    def learn_document(self, text: str) -> Dict[str, Any]:
        """Aprende de um único documento (aprendizado incremental)."""
        return self.learn([text])
    
    def learn_pair(self, question: str, answer: str) -> Dict[str, Any]:
        """
        Aprende um par pergunta-resposta.
        
        Isso é similar a supervised learning, mas sem gradientes.
        Armazena a associação diretamente na memória.
        """
        q_tokens = tokenize(question)
        a_tokens = tokenize(answer)
        
        # Armazena na memória
        self.state.memory.store(
            key=tuple(q_tokens),
            value=answer,
            context=tuple(a_tokens[:5]),  # Contexto = início da resposta
            strength=2.0,  # Força maior para pares explícitos
        )
        
        # Também armazena tokens da resposta
        self.state.memory.store(
            key=tuple(a_tokens),
            value=question,
            context=tuple(q_tokens[:5]),
            strength=1.5,
        )
        
        # Atualiza vocabulário e grafo
        self.state.vocabulary.update(q_tokens)
        self.state.vocabulary.update(a_tokens)
        
        combined = q_tokens + ["<SEP>"] + a_tokens
        self.state.graph.add_document(combined)
        
        return {
            "status": "learned_pair",
            "question_tokens": len(q_tokens),
            "answer_tokens": len(a_tokens),
        }
    
    def _populate_memory(
        self,
        tokenized: Sequence[Sequence[str]],
        compression: CompressionResult,
    ) -> None:
        """Popula memória com padrões aprendidos."""
        # Armazena padrões frequentes
        for pattern in compression.patterns[:100]:  # Top 100
            self.state.memory.store(
                key=pattern.tokens,
                value={"type": "pattern", "count": pattern.count},
                strength=math.log1p(pattern.count),
            )
        
        # Armazena n-grams frequentes de cada documento
        for doc_tokens in tokenized:
            for n in range(2, 6):
                for i in range(len(doc_tokens) - n + 1):
                    ngram = tuple(doc_tokens[i:i + n])
                    self.state.memory.store(
                        key=ngram,
                        value={"type": "ngram", "n": n},
                        context=tuple(doc_tokens[max(0, i - 2):i]),
                        strength=0.5,
                    )
    
    def _create_associations(self, tokenized: Sequence[Sequence[str]]) -> None:
        """Cria associações entre tokens que co-ocorrem."""
        for doc_tokens in tokenized:
            # Associa tokens adjacentes
            for i in range(len(doc_tokens) - 1):
                self.state.memory.associate(
                    (doc_tokens[i],),
                    (doc_tokens[i + 1],),
                    strength=0.5,
                )
    
    # =========================================================================
    # INFERÊNCIA (equivalente a "predição")
    # =========================================================================
    
    def query(self, text: str, context: str = "") -> QueryResult:
        """
        Processa uma query e gera resposta.
        
        Este é o equivalente a "inferência" em modelos neurais,
        mas totalmente interpretável.
        """
        self.state.queries_processed += 1
        
        q_tokens = tokenize(text)
        ctx_tokens = tokenize(context) if context else []
        
        reasoning = []
        
        # 1. Recupera memórias relevantes
        retrieved = self.state.memory.retrieve(
            query=q_tokens,
            context=tuple(ctx_tokens),
            top_k=10,
        )
        reasoning.append(f"Retrieved {len(retrieved)} relevant memories")
        
        # 2. Verifica se há resposta direta na memória
        direct_answer = self._find_direct_answer(q_tokens, retrieved)
        if direct_answer:
            reasoning.append(f"Found direct answer in memory")
            return QueryResult(
                query=text,
                response=direct_answer,
                confidence=0.9,
                reasoning=reasoning,
                retrieved_memories=retrieved,
                applied_rules=[],
                similar_patterns=[],
            )
        
        # 3. Expande query via grafo semântico
        expanded_terms = self._expand_via_graph(q_tokens)
        reasoning.append(f"Expanded query with {len(expanded_terms)} related terms")
        
        # 4. Aplica regras para derivar novos fatos
        facts = self._tokens_to_facts(q_tokens + list(expanded_terms))
        derived = self.state.rules.derive_all(facts, max_iterations=5)
        applied_rules = self._find_applicable_rules(facts)
        reasoning.append(f"Applied {len(applied_rules)} rules, derived {len(derived)} facts")
        
        # 5. Compõe resposta
        response = self._compose_response(
            q_tokens,
            retrieved,
            expanded_terms,
            derived,
        )
        reasoning.append(f"Composed response with {len(tokenize(response))} tokens")
        
        # 6. Calcula confiança
        confidence = self._compute_confidence(retrieved, applied_rules)
        
        # 7. Encontra padrões similares
        similar = self._find_similar_patterns(q_tokens)
        
        return QueryResult(
            query=text,
            response=response,
            confidence=confidence,
            reasoning=reasoning,
            retrieved_memories=retrieved,
            applied_rules=applied_rules,
            similar_patterns=similar,
        )
    
    def complete(self, partial: str) -> str:
        """
        Completa um texto parcial.
        
        Similar a language model completion, mas via retrieval.
        """
        tokens = tokenize(partial)
        
        # Tenta completar via memória
        completion = self.state.memory.complete(tokens)
        if completion:
            return partial + " " + " ".join(completion)
        
        # Tenta via grafo (próximo token mais provável)
        if tokens:
            last_token = tokens[-1]
            neighbors = self.state.graph.neighbors(last_token, top_k=3)
            if neighbors:
                next_token = neighbors[0][0]
                return partial + " " + next_token
        
        return partial
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        Calcula similaridade entre dois textos.
        
        Usa compressão (NCD) em vez de cosseno de embeddings.
        """
        tokens1 = tokenize(text1)
        tokens2 = tokenize(text2)
        
        return self.state.compressor.similarity(tokens1, tokens2)
    
    def _find_direct_answer(
        self,
        query_tokens: Sequence[str],
        retrieved: List[RetrievalResult],
    ) -> str | None:
        """Verifica se há resposta direta na memória."""
        for result in retrieved:
            if result.match_score > 0.8:
                value = result.trace.value
                if isinstance(value, str):
                    return value
        return None
    
    def _expand_via_graph(self, tokens: Sequence[str]) -> Set[str]:
        """Expande tokens via grafo semântico."""
        expanded = set()
        
        for token in tokens:
            neighbors = self.state.graph.neighbors(token, top_k=3, min_cooc=2)
            for neighbor, score in neighbors:
                if score > 0.5:
                    expanded.add(neighbor)
        
        return expanded
    
    def _tokens_to_facts(self, tokens: Sequence[str]) -> List[Condition]:
        """Converte tokens em fatos para raciocínio."""
        facts = []
        
        for token in tokens:
            facts.append(Condition("exists", (token,)))
        
        for i in range(len(tokens) - 1):
            facts.append(Condition("follows", (tokens[i], tokens[i + 1])))
        
        return facts
    
    def _find_applicable_rules(self, facts: Sequence[Condition]) -> List[SymbolicRule]:
        """Encontra regras aplicáveis aos fatos."""
        applicable = []
        
        for rule in self.state.rules:
            if rule.applies(facts):
                applicable.append(rule)
        
        return applicable
    
    def _compose_response(
        self,
        query_tokens: Sequence[str],
        retrieved: List[RetrievalResult],
        expanded: Set[str],
        derived: Set[Condition],
    ) -> str:
        """Compõe resposta a partir de evidências."""
        # Coleta fragmentos relevantes
        fragments = []
        
        # De memórias recuperadas
        for result in retrieved[:3]:
            value = result.trace.value
            if isinstance(value, str):
                fragments.append(value)
            elif isinstance(value, (list, tuple)):
                fragments.append(" ".join(str(v) for v in value))
        
        # De fatos derivados
        for fact in list(derived)[:5]:
            if fact.predicate == "exists":
                fragments.append(fact.args[0])
        
        # De expansão semântica
        fragments.extend(list(expanded)[:5])
        
        if not fragments:
            return "Não encontrei informação suficiente para responder."
        
        # Compõe resposta (simples concatenação por ora)
        # Em uma versão mais avançada, usaríamos as regras para estruturar
        unique_fragments = list(dict.fromkeys(fragments))
        response = " ".join(unique_fragments[:self.config.max_response_tokens])
        
        return response
    
    def _compute_confidence(
        self,
        retrieved: List[RetrievalResult],
        applied_rules: List[SymbolicRule],
    ) -> float:
        """Computa confiança na resposta."""
        if not retrieved and not applied_rules:
            return 0.1
        
        # Média das relevâncias das memórias recuperadas
        mem_conf = sum(r.relevance for r in retrieved) / len(retrieved) if retrieved else 0.0
        
        # Média das confianças das regras aplicadas
        rule_conf = sum(r.confidence for r in applied_rules) / len(applied_rules) if applied_rules else 0.0
        
        # Combina
        return min(1.0, (mem_conf + rule_conf) / 2 + 0.1)
    
    def _find_similar_patterns(self, tokens: Sequence[str]) -> List[Tuple[str, float]]:
        """Encontra padrões similares no corpus."""
        similar = []
        
        for symbol, pattern, freq in self.state.compressor.get_patterns():
            # Calcula overlap
            pattern_set = set(pattern)
            query_set = set(tokens)
            
            if not pattern_set or not query_set:
                continue
            
            overlap = len(pattern_set & query_set) / len(pattern_set | query_set)
            
            if overlap > 0.3:
                similar.append((" ".join(pattern), overlap))
        
        return sorted(similar, key=lambda x: -x[1])[:5]
    
    # =========================================================================
    # PERSISTÊNCIA
    # =========================================================================
    
    def save(self, path: str | Path) -> None:
        """Salva o estado aprendido."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        # Salva estatísticas e configuração
        meta = {
            "documents_seen": self.state.documents_seen,
            "tokens_seen": self.state.tokens_seen,
            "queries_processed": self.state.queries_processed,
            "vocabulary_size": len(self.state.vocabulary),
            "rules_count": len(self.state.rules),
            "memory_traces": len(self.state.memory),
            "config": {
                "min_pattern_freq": self.config.min_pattern_freq,
                "max_pattern_length": self.config.max_pattern_length,
                "cooc_window_size": self.config.cooc_window_size,
                "min_rule_support": self.config.min_rule_support,
                "min_rule_confidence": self.config.min_rule_confidence,
            },
        }
        
        (path / "meta.json").write_text(json.dumps(meta, indent=2))
        
        # Salva vocabulário
        (path / "vocabulary.txt").write_text("\n".join(sorted(self.state.vocabulary)))
        
        # Salva padrões do compressor
        patterns = []
        for symbol, pattern, freq in self.state.compressor.get_patterns():
            patterns.append({"symbol": symbol, "pattern": list(pattern), "freq": freq})
        (path / "patterns.json").write_text(json.dumps(patterns, indent=2))
        
        # Salva regras
        rules = []
        for rule in self.state.rules:
            rules.append({
                "antecedents": [str(a) for a in rule.antecedents],
                "consequent": str(rule.consequent),
                "support": rule.support,
                "confidence": rule.confidence,
                "lift": rule.lift,
            })
        (path / "rules.json").write_text(json.dumps(rules, indent=2))
    
    def stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do sistema."""
        return {
            "documents_seen": self.state.documents_seen,
            "tokens_seen": self.state.tokens_seen,
            "queries_processed": self.state.queries_processed,
            "vocabulary_size": len(self.state.vocabulary),
            "rules_count": len(self.state.rules),
            "memory_traces": len(self.state.memory),
            "graph_stats": self.state.graph.stats(),
            "memory_stats": self.state.memory.stats(),
            "state_digest": self.state.digest(),
        }


__all__ = ["LearningEngine", "LearningConfig", "LearningState", "QueryResult", "tokenize"]
