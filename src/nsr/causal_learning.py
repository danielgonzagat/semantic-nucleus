"""
Aprendizado Causal: Aprende relações causais entre eventos.

Entende "por quê" algo acontece, não apenas "o quê".
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from liu import Node, NodeKind, relation, var


@dataclass(frozen=True, slots=True)
class CausalRelation:
    """Relação causal entre dois eventos."""
    
    cause: Node
    effect: Node
    strength: float  # Força da relação causal (0.0 a 1.0)
    confidence: float  # Confiança na relação
    evidence_count: int  # Quantas vezes foi observada


@dataclass(slots=True)
class CausalGraph:
    """Grafo causal: representa relações causais."""
    
    # Mapeia causa -> [(efeito, força, confiança)]
    causal_edges: Dict[str, List[Tuple[str, float, float]]] = field(default_factory=dict)
    
    # Mapeia efeito -> [(causa, força, confiança)]
    reverse_edges: Dict[str, List[Tuple[str, float, float]]] = field(default_factory=dict)
    
    # Contadores de coocorrência
    cooccurrence: Dict[Tuple[str, str], int] = field(default_factory=Counter)
    
    # Contadores temporais (causa antes de efeito)
    temporal_order: Dict[Tuple[str, str], int] = field(default_factory=Counter)


class CausalLearner:
    """
    Aprende relações causais observando sequências de eventos.
    
    Métodos:
    1. Observa sequências temporais
    2. Identifica padrões causa-efeito
    3. Testa relações causais
    4. Constrói grafo causal
    """
    
    def __init__(self, min_confidence: float = 0.6):
        self.min_confidence = min_confidence
        self.graph = CausalGraph()
        self.event_sequences: List[List[Node]] = []
    
    def observe_sequence(self, events: List[Node], timestamps: List[float] | None = None) -> None:
        """
        Observa sequência de eventos.
        
        Se timestamps fornecidos, usa ordem temporal.
        Caso contrário, assume ordem da lista.
        """
        self.event_sequences.append(events)
        
        # Se tem timestamps, ordena por tempo
        if timestamps:
            sorted_pairs = sorted(zip(timestamps, events), key=lambda x: x[0])
            events = [e for _, e in sorted_pairs]
        
        # Registra coocorrências e ordem temporal
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                event1 = events[i]
                event2 = events[j]
                
                # Coocorrência
                key = (self._event_key(event1), self._event_key(event2))
                self.graph.cooccurrence[key] += 1
                
                # Ordem temporal (event1 antes de event2)
                self.graph.temporal_order[key] += 1
    
    def learn_causality(self) -> List[CausalRelation]:
        """Aprende relações causais dos eventos observados."""
        
        causal_relations: List[CausalRelation] = []
        
        # Para cada par de eventos
        for (cause_key, effect_key), temporal_count in self.graph.temporal_order.items():
            cooccurrence_count = self.graph.cooccurrence.get((cause_key, effect_key), 0)
            
            if cooccurrence_count < 3:  # Mínimo de observações
                continue
            
            # Força = proporção de vezes que causa precede efeito
            total_cooccurrence = cooccurrence_count
            strength = temporal_count / max(1, total_cooccurrence)
            
            # Confiança = baseada em frequência e consistência
            confidence = min(1.0, strength * (total_cooccurrence / 10.0))
            
            if confidence < self.min_confidence:
                continue
            
            # Cria relação causal
            # Nota: Em produção, reconstruiria nós a partir das keys
            # Simplificação: cria relação genérica
            cause_node = self._key_to_node(cause_key)
            effect_node = self._key_to_node(effect_key)
            
            relation = CausalRelation(
                cause=cause_node,
                effect=effect_node,
                strength=strength,
                confidence=confidence,
                evidence_count=total_cooccurrence,
            )
            
            causal_relations.append(relation)
            
            # Adiciona ao grafo
            if cause_key not in self.graph.causal_edges:
                self.graph.causal_edges[cause_key] = []
            self.graph.causal_edges[cause_key].append((effect_key, strength, confidence))
            
            if effect_key not in self.graph.reverse_edges:
                self.graph.reverse_edges[effect_key] = []
            self.graph.reverse_edges[effect_key].append((cause_key, strength, confidence))
        
        return causal_relations
    
    def predict_effect(self, cause: Node) -> List[Tuple[Node, float]]:
        """
        Prediz efeitos de uma causa.
        
        Retorna lista de (efeito, probabilidade).
        """
        cause_key = self._event_key(cause)
        
        if cause_key not in self.graph.causal_edges:
            return []
        
        predictions = []
        for effect_key, strength, confidence in self.graph.causal_edges[cause_key]:
            effect_node = self._key_to_node(effect_key)
            probability = strength * confidence
            predictions.append((effect_node, probability))
        
        # Ordena por probabilidade
        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions
    
    def explain_cause(self, effect: Node) -> List[Tuple[Node, float]]:
        """
        Explica causas de um efeito.
        
        Retorna lista de (causa, probabilidade).
        """
        effect_key = self._event_key(effect)
        
        if effect_key not in self.graph.reverse_edges:
            return []
        
        explanations = []
        for cause_key, strength, confidence in self.graph.reverse_edges[effect_key]:
            cause_node = self._key_to_node(cause_key)
            probability = strength * confidence
            explanations.append((cause_node, probability))
        
        # Ordena por probabilidade
        explanations.sort(key=lambda x: x[1], reverse=True)
        return explanations
    
    def _event_key(self, event: Node) -> str:
        """Cria chave única para evento."""
        from liu import fingerprint
        
        if event.kind is NodeKind.REL and event.label:
            args_str = "_".join(
                arg.label if arg.kind is NodeKind.ENTITY else "?"
                for arg in event.args[:2]
            )
            return f"{event.label}:{args_str}"
        
        return fingerprint(event)
    
    def _key_to_node(self, key: str) -> Node:
        """Reconstrói nó a partir de chave (simplificado)."""
        from liu import entity, relation
        
        # Simplificação: assume formato "LABEL:arg1_arg2"
        if ":" in key:
            label, args_str = key.split(":", 1)
            args = args_str.split("_")
            if len(args) >= 2:
                return relation(label, entity(args[0]), entity(args[1]))
        
        # Fallback: cria nó genérico
        return entity(key)


__all__ = ["CausalRelation", "CausalGraph", "CausalLearner"]
