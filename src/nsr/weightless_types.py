"""
Tipos compartilhados para o sistema de aprendizado sem pesos.

Este módulo contém as classes base usadas por múltiplos módulos
para evitar importações circulares.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Set, Tuple

from liu import Node


@dataclass(frozen=True)
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


@dataclass()
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


__all__ = ['Episode', 'Pattern']

