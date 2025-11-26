"""
NSR-Learn: Aprendizado de Máquina Simbólico Sem Pesos Neurais.

Este módulo implementa uma arquitetura experimental de aprendizado que NÃO usa:
- Redes neurais
- Backpropagation  
- Matrizes de pesos contínuos
- Gradientes

Em vez disso, usa:
- Compressão MDL (Minimum Description Length)
- Grafos de co-ocorrência discretos
- Indução de regras simbólicas
- Memória associativa discreta
- Composição estrutural

A hipótese fundamental: Inteligência = Compressão (Kolmogorov/Solomonoff)
Se conseguimos comprimir bem os dados, conseguimos "entendê-los".
"""

from .compressor import MDLCompressor, CompressionResult
from .graph import CooccurrenceGraph, GraphNode, GraphEdge
from .inductor import RuleInductor, SymbolicRule, RuleSet
from .memory import AssociativeMemory, MemoryTrace, RetrievalResult
from .engine import LearningEngine, LearningConfig, LearningState

__all__ = [
    # Compressor
    "MDLCompressor",
    "CompressionResult",
    # Graph
    "CooccurrenceGraph", 
    "GraphNode",
    "GraphEdge",
    # Inductor
    "RuleInductor",
    "SymbolicRule",
    "RuleSet",
    # Memory
    "AssociativeMemory",
    "MemoryTrace",
    "RetrievalResult",
    # Engine
    "LearningEngine",
    "LearningConfig",
    "LearningState",
]
