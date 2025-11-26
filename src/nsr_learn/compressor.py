"""
Compressor MDL (Minimum Description Length).

Princípio: A melhor hipótese é aquela que minimiza:
    L(H) + L(D|H)
    
Onde:
- L(H) = comprimento da descrição do modelo/hipótese
- L(D|H) = comprimento da descrição dos dados dado o modelo

Isso é uma aproximação computável de Solomonoff Induction.

Em vez de pesos neurais, aprendemos:
- Um dicionário de padrões frequentes
- Regras de substituição
- Estrutura hierárquica

A "inteligência" emerge da compressão: padrões que se repetem
são capturados e podem ser reutilizados para generalização.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from hashlib import blake2b
from typing import Dict, FrozenSet, Iterator, List, Mapping, Sequence, Tuple


@dataclass(frozen=True)
class Pattern:
    """Um padrão extraído dos dados."""
    
    tokens: Tuple[str, ...]
    count: int
    savings: float  # Bits economizados ao usar este padrão
    
    @property
    def length(self) -> int:
        return len(self.tokens)
    
    @property
    def id(self) -> str:
        hasher = blake2b(digest_size=8)
        for token in self.tokens:
            hasher.update(token.encode("utf-8"))
        return f"P{hasher.hexdigest()[:8]}"


@dataclass(frozen=True)
class CompressionResult:
    """Resultado de uma compressão."""
    
    original_bits: float
    compressed_bits: float
    model_bits: float
    patterns: Tuple[Pattern, ...]
    compression_ratio: float
    
    @property
    def total_bits(self) -> float:
        return self.compressed_bits + self.model_bits
    
    @property
    def mdl_score(self) -> float:
        """Quanto menor, melhor a compressão (e o 'entendimento')."""
        return self.total_bits


@dataclass(frozen=True)
class Substitution:
    """Uma regra de substituição: sequência → símbolo."""
    
    pattern: Tuple[str, ...]
    symbol: str
    frequency: int


@dataclass()
class Dictionary:
    """Dicionário de padrões aprendidos."""
    
    entries: Dict[str, Tuple[str, ...]] = field(default_factory=dict)
    frequencies: Dict[str, int] = field(default_factory=dict)
    
    def add(self, symbol: str, pattern: Tuple[str, ...], freq: int = 1) -> None:
        self.entries[symbol] = pattern
        self.frequencies[symbol] = self.frequencies.get(symbol, 0) + freq
    
    def lookup(self, symbol: str) -> Tuple[str, ...] | None:
        return self.entries.get(symbol)
    
    def contains(self, pattern: Tuple[str, ...]) -> str | None:
        """Retorna o símbolo se o padrão já existe no dicionário."""
        for sym, pat in self.entries.items():
            if pat == pattern:
                return sym
        return None
    
    def size_in_bits(self) -> float:
        """Custo em bits para descrever o dicionário (parte do L(H))."""
        if not self.entries:
            return 0.0
        total = 0.0
        for symbol, pattern in self.entries.items():
            # Custo de cada entrada: símbolo + separador + tokens do padrão
            total += _symbol_bits(symbol)
            total += sum(_symbol_bits(tok) for tok in pattern)
            total += 8  # Overhead de estrutura
        return total
    
    def __len__(self) -> int:
        return len(self.entries)


class MDLCompressor:
    """
    Compressor baseado em MDL (Minimum Description Length).
    
    Aprende padrões dos dados sem usar pesos neurais.
    Usa apenas contagens discretas e substituições simbólicas.
    
    Algoritmo (inspirado em Sequitur/Re-Pair):
    1. Conta pares de símbolos adjacentes
    2. Substitui o par mais frequente por um novo símbolo
    3. Adiciona a regra ao dicionário
    4. Repete até não haver economia
    
    A "generalização" emerge porque padrões frequentes são
    capturados e podem ser reconhecidos em novos dados.
    """
    
    def __init__(
        self,
        min_pattern_freq: int = 2,
        min_pattern_length: int = 2,
        max_pattern_length: int = 16,
        max_dictionary_size: int = 10000,
    ):
        self.min_pattern_freq = min_pattern_freq
        self.min_pattern_length = min_pattern_length
        self.max_pattern_length = max_pattern_length
        self.max_dictionary_size = max_dictionary_size
        self.dictionary = Dictionary()
        self._symbol_counter = 0
    
    def learn(self, corpus: Sequence[Sequence[str]]) -> CompressionResult:
        """
        Aprende padrões de um corpus de sequências de tokens.
        
        Este é o processo de "treinamento" — mas sem gradientes ou pesos.
        Apenas contagem e substituição simbólica.
        """
        # Concatena todas as sequências com separadores
        all_tokens: List[str] = []
        for seq in corpus:
            all_tokens.extend(seq)
            all_tokens.append("<SEP>")
        
        if not all_tokens:
            return CompressionResult(
                original_bits=0.0,
                compressed_bits=0.0,
                model_bits=0.0,
                patterns=tuple(),
                compression_ratio=1.0,
            )
        
        original_bits = self._compute_bits(all_tokens)
        current_sequence = list(all_tokens)
        patterns_found: List[Pattern] = []
        
        # Iterativamente encontra e substitui padrões
        iteration = 0
        max_iterations = self.max_dictionary_size
        
        while iteration < max_iterations:
            iteration += 1
            
            # Encontra o melhor par para substituir
            best_pair, best_freq = self._find_best_pair(current_sequence)
            
            if best_pair is None or best_freq < self.min_pattern_freq:
                break
            
            # Calcula economia
            old_bits = self._compute_bits(current_sequence)
            
            # Cria novo símbolo
            new_symbol = self._new_symbol()
            
            # Substitui todas as ocorrências
            current_sequence = self._substitute(current_sequence, best_pair, new_symbol)
            
            # Adiciona ao dicionário
            self.dictionary.add(new_symbol, best_pair, best_freq)
            
            new_bits = self._compute_bits(current_sequence)
            dict_cost = self.dictionary.size_in_bits()
            
            # Verifica se houve economia real (MDL criterion)
            num_patterns = len(patterns_found) + 1  # +1 para evitar divisão por zero
            savings = old_bits - (new_bits + dict_cost / num_patterns + 1)
            
            if savings <= 0:
                # Reverte se não houve economia
                self.dictionary.entries.pop(new_symbol, None)
                self.dictionary.frequencies.pop(new_symbol, None)
                break
            
            patterns_found.append(Pattern(
                tokens=best_pair,
                count=best_freq,
                savings=savings,
            ))
        
        # Tenta encontrar padrões maiores (n-grams)
        patterns_found.extend(self._find_ngram_patterns(current_sequence))
        
        compressed_bits = self._compute_bits(current_sequence)
        model_bits = self.dictionary.size_in_bits()
        
        ratio = (compressed_bits + model_bits) / original_bits if original_bits > 0 else 1.0
        
        return CompressionResult(
            original_bits=original_bits,
            compressed_bits=compressed_bits,
            model_bits=model_bits,
            patterns=tuple(sorted(patterns_found, key=lambda p: -p.savings)),
            compression_ratio=ratio,
        )
    
    def compress(self, tokens: Sequence[str]) -> Tuple[List[str], float]:
        """
        Comprime uma sequência usando o dicionário aprendido.
        Retorna a sequência comprimida e a taxa de compressão.
        """
        if not tokens:
            return [], 1.0
        
        original_bits = self._compute_bits(tokens)
        current = list(tokens)
        
        # Aplica substituições do dicionário (do mais frequente ao menos)
        sorted_entries = sorted(
            self.dictionary.entries.items(),
            key=lambda x: -self.dictionary.frequencies.get(x[0], 0),
        )
        
        for symbol, pattern in sorted_entries:
            current = self._substitute(current, pattern, symbol)
        
        compressed_bits = self._compute_bits(current)
        ratio = compressed_bits / original_bits if original_bits > 0 else 1.0
        
        return current, ratio
    
    def decompress(self, compressed: Sequence[str]) -> List[str]:
        """Descomprime uma sequência usando o dicionário."""
        result = list(compressed)
        changed = True
        max_iterations = 1000
        iteration = 0
        
        while changed and iteration < max_iterations:
            changed = False
            iteration += 1
            new_result = []
            
            for symbol in result:
                expansion = self.dictionary.lookup(symbol)
                if expansion is not None:
                    new_result.extend(expansion)
                    changed = True
                else:
                    new_result.append(symbol)
            
            result = new_result
        
        return result
    
    def get_patterns(self) -> Iterator[Tuple[str, Tuple[str, ...], int]]:
        """Retorna todos os padrões aprendidos."""
        for symbol, pattern in self.dictionary.entries.items():
            freq = self.dictionary.frequencies.get(symbol, 0)
            yield symbol, pattern, freq
    
    def similarity(self, seq1: Sequence[str], seq2: Sequence[str]) -> float:
        """
        Calcula similaridade entre duas sequências baseado em compressão.
        
        Usa NCD (Normalized Compression Distance):
        NCD(x,y) = (C(xy) - min(C(x), C(y))) / max(C(x), C(y))
        
        Similaridade = 1 - NCD
        
        Também usa Jaccard como fallback para casos simples.
        """
        if not seq1 and not seq2:
            return 1.0
        if not seq1 or not seq2:
            return 0.0
        
        # Jaccard como baseline (sempre funciona)
        set1 = set(seq1)
        set2 = set(seq2)
        jaccard = len(set1 & set2) / len(set1 | set2) if (set1 | set2) else 0.0
        
        # NCD via compressão
        c1, _ = self.compress(seq1)
        c2, _ = self.compress(seq2)
        
        # Comprime a concatenação
        combined = list(seq1) + ["<JOIN>"] + list(seq2)
        c12, _ = self.compress(combined)
        
        bits1 = self._compute_bits(c1)
        bits2 = self._compute_bits(c2)
        bits12 = self._compute_bits(c12)
        
        min_bits = min(bits1, bits2)
        max_bits = max(bits1, bits2)
        
        if max_bits == 0:
            return jaccard
        
        ncd = (bits12 - min_bits) / max_bits
        compression_sim = max(0.0, 1.0 - ncd)
        
        # Combina Jaccard e NCD
        return max(jaccard, compression_sim)
    
    def _find_best_pair(self, sequence: Sequence[str]) -> Tuple[Tuple[str, str] | None, int]:
        """Encontra o par mais frequente na sequência."""
        if len(sequence) < 2:
            return None, 0
        
        pair_counts: Counter[Tuple[str, str]] = Counter()
        
        for i in range(len(sequence) - 1):
            pair = (sequence[i], sequence[i + 1])
            # Ignora pares com separadores
            if "<SEP>" not in pair and "<JOIN>" not in pair:
                pair_counts[pair] += 1
        
        if not pair_counts:
            return None, 0
        
        best_pair, best_count = pair_counts.most_common(1)[0]
        return best_pair, best_count
    
    def _find_ngram_patterns(self, sequence: Sequence[str]) -> List[Pattern]:
        """Encontra padrões de n-grams (n > 2)."""
        patterns = []
        
        for n in range(3, min(self.max_pattern_length + 1, len(sequence) // 2 + 1)):
            ngram_counts: Counter[Tuple[str, ...]] = Counter()
            
            for i in range(len(sequence) - n + 1):
                ngram = tuple(sequence[i:i + n])
                # Ignora n-grams com separadores
                if not any(tok in ("<SEP>", "<JOIN>") for tok in ngram):
                    ngram_counts[ngram] += 1
            
            for ngram, count in ngram_counts.items():
                if count >= self.min_pattern_freq:
                    # Calcula economia potencial
                    ngram_bits = sum(_symbol_bits(tok) for tok in ngram)
                    symbol_bits = _symbol_bits(f"N{n}")
                    savings = count * (ngram_bits - symbol_bits)
                    
                    if savings > 0:
                        patterns.append(Pattern(
                            tokens=ngram,
                            count=count,
                            savings=savings,
                        ))
        
        return patterns
    
    def _substitute(
        self,
        sequence: List[str],
        pattern: Tuple[str, ...],
        symbol: str,
    ) -> List[str]:
        """Substitui todas as ocorrências de um padrão por um símbolo."""
        if len(pattern) == 0:
            return sequence
        
        result = []
        i = 0
        pattern_len = len(pattern)
        
        while i < len(sequence):
            # Verifica se encontrou o padrão
            if i + pattern_len <= len(sequence):
                match = True
                for j, tok in enumerate(pattern):
                    if sequence[i + j] != tok:
                        match = False
                        break
                
                if match:
                    result.append(symbol)
                    i += pattern_len
                    continue
            
            result.append(sequence[i])
            i += 1
        
        return result
    
    def _new_symbol(self) -> str:
        """Gera um novo símbolo único."""
        self._symbol_counter += 1
        return f"§{self._symbol_counter}"
    
    def _compute_bits(self, sequence: Sequence[str]) -> float:
        """Calcula o número de bits para codificar uma sequência."""
        if not sequence:
            return 0.0
        
        # Conta frequência de cada símbolo
        counts = Counter(sequence)
        total = len(sequence)
        
        # Entropia de Shannon
        entropy = 0.0
        for count in counts.values():
            if count > 0:
                prob = count / total
                entropy -= prob * math.log2(prob)
        
        return entropy * total


def _symbol_bits(symbol: str) -> float:
    """Estima bits necessários para codificar um símbolo."""
    # Aproximação: log2 do número de símbolos possíveis
    # Para simplificar, usamos o comprimento * 5 bits por caractere
    return len(symbol) * 5.0


__all__ = ["MDLCompressor", "CompressionResult", "Pattern", "Dictionary"]
