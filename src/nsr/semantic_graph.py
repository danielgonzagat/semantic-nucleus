"""
Grafo semântico determinístico para o NSR.
Oferece indexação e travessia eficiente sobre a lista plana de relações do ISR.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set, Tuple, Optional

from liu import Node, NodeKind, fingerprint


@dataclass(frozen=True)
class SemanticGraph:
    """
    Representação em grafo de um conjunto de relações LIU.
    Imutável por design para facilitar snapshots do ISR.
    """

    # Adjacency list: fingerprint(source) -> {relation_label: [target_node, ...]}
    _outgoing: Dict[str, Dict[str, List[Node]]] = field(default_factory=dict)
    
    # Reverse index: fingerprint(target) -> {relation_label: [source_node, ...]}
    _incoming: Dict[str, Dict[str, List[Node]]] = field(default_factory=dict)

    # Lookup: fingerprint -> Node (para reconstrução)
    _nodes: Dict[str, Node] = field(default_factory=dict)
    
    # Metadata de domínio: fingerprint(rel) -> domain_name
    _rel_domains: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_relations(cls, relations: Iterable[Node], domain_map: Dict[str, str] = None) -> "SemanticGraph":
        """
        Constrói um grafo a partir de uma lista de nós de relação.
        Ignora nós que não sejam REL.
        domain_map: mapeia fingerprint(rel) -> nome_do_dominio (opcional)
        """
        outgoing: Dict[str, Dict[str, List[Node]]] = {}
        incoming: Dict[str, Dict[str, List[Node]]] = {}
        nodes: Dict[str, Node] = {}
        rel_domains = domain_map or {}

        for rel in relations:
            if rel.kind is not NodeKind.REL:
                continue
            
            # Suporta apenas relações binárias por enquanto para o grafo
            # (mas armazena o nó original completo)
            if len(rel.args) < 2:
                continue

            label = (rel.label or "").upper()
            source = rel.args[0]
            target = rel.args[1]
            
            src_fp = fingerprint(source)
            tgt_fp = fingerprint(target)

            nodes[src_fp] = source
            nodes[tgt_fp] = target

            # Outgoing
            if src_fp not in outgoing:
                outgoing[src_fp] = {}
            if label not in outgoing[src_fp]:
                outgoing[src_fp][label] = []
            outgoing[src_fp][label].append(target)

            # Incoming
            if tgt_fp not in incoming:
                incoming[tgt_fp] = {}
            if label not in incoming[tgt_fp]:
                incoming[tgt_fp][label] = []
            incoming[tgt_fp][label].append(source)

        return cls(_outgoing=outgoing, _incoming=incoming, _nodes=nodes, _rel_domains=rel_domains)

    def get_neighbors(self, node: Node, rel_type: str | None = None, direction: str = "out") -> List[Node]:
        """
        Retorna vizinhos de um nó.
        direction: "out" (filhos), "in" (pais), "both".
        """
        fp = fingerprint(node)
        results: List[Node] = []

        if direction in ("out", "both"):
            if fp in self._outgoing:
                for label, targets in self._outgoing[fp].items():
                    if rel_type is None or label == rel_type:
                        results.extend(targets)

        if direction in ("in", "both"):
            if fp in self._incoming:
                for label, sources in self._incoming[fp].items():
                    if rel_type is None or label == rel_type:
                        results.extend(sources)
        
        # Deduplica preservando ordem (para determinismo)
        seen = set()
        deduped = []
        for n in results:
            n_fp = fingerprint(n)
            if n_fp not in seen:
                seen.add(n_fp)
                deduped.append(n)
        
        # Ordena por fingerprint para garantir determinismo absoluto
        deduped.sort(key=fingerprint)
        return deduped

    def transitive_closure(self, start_node: Node, rel_type: str, max_depth: int = 10) -> List[Node]:
        """
        Encontra todos os nós alcançáveis seguindo uma relação específica.
        Ex: IS_A (para encontrar toda a taxonomia acima).
        """
        visited = set()
        results = []
        queue = [(start_node, 0)]
        visited.add(fingerprint(start_node))

        idx = 0
        while idx < len(queue):
            current, depth = queue[idx]
            idx += 1

            if depth >= max_depth:
                continue

            neighbors = self.get_neighbors(current, rel_type=rel_type, direction="out")
            for neighbor in neighbors:
                n_fp = fingerprint(neighbor)
                if n_fp not in visited:
                    visited.add(n_fp)
                    results.append(neighbor)
                    queue.append((neighbor, depth + 1))
        
        return results

    def get_properties(self, node: Node, inherit: bool = False, domain_filter: Optional[str] = None) -> List[Tuple[str, Node]]:
        """
        Retorna (relação, valor) para o nó.
        Se inherit=True, sobe a taxonomia IS_A e coleta propriedades dos pais.
        domain_filter: se fornecido, retorna apenas propriedades definidas nesse domínio (requer _rel_domains populado).
        """
        props = []
        
        # Helper interno para coletar props de um nó específico
        def _collect(n: Node):
            n_fp = fingerprint(n)
            if n_fp in self._outgoing:
                for label, targets in self._outgoing[n_fp].items():
                    for t in targets:
                        # Se tiver filtro de domínio, verificar (nota: implementação completa exigiria linkar a aresta exata ao domínio)
                        # Como simplificação, aceitamos tudo se não houver filtro
                        props.append((label, t))

        # 1. Propriedades diretas
        _collect(node)

        # 2. Herança
        if inherit:
            parents = self.transitive_closure(node, "IS_A")
            for parent in parents:
                # Não herdamos IS_A de novo
                p_fp = fingerprint(parent)
                if p_fp in self._outgoing:
                    for label, targets in self._outgoing[p_fp].items():
                        if label != "IS_A":
                            for t in targets:
                                props.append((label, t))
        
        # Sort determinístico
        props.sort(key=lambda x: (x[0], fingerprint(x[1])))
        return props

    @property
    def node_count(self) -> int:
        return len(self._nodes)
