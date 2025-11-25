"""
Gerenciador de Múltiplas Ontologias (Domínios de Conhecimento).
Permite segmentar o Grafo Semântico em namespaces (ex: 'core', 'medical', 'legal').
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Set

from liu import Node, NodeKind, entity, relation, struct, text

@dataclass(frozen=True)
class OntologyDomain:
    name: str
    relations: Tuple[Node, ...]
    version: str = "1.0"
    dependencies: Tuple[str, ...] = tuple()

class MultiOntologyManager:
    """
    Gerencia o carregamento e acesso a múltiplos domínios ontológicos.
    """
    
    def __init__(self):
        self.domains: Dict[str, OntologyDomain] = {}
        self.active_domains: Set[str] = {"core"}

    def register_domain(self, domain: OntologyDomain) -> None:
        self.domains[domain.name] = domain

    def activate_domain(self, name: str) -> None:
        if name in self.domains:
            self.active_domains.add(name)
            # Ativa dependências recursivamente
            for dep in self.domains[name].dependencies:
                self.activate_domain(dep)
    
    def deactivate_domain(self, name: str) -> None:
        if name in self.active_domains:
            self.active_domains.remove(name)

    def get_active_relations(self) -> Tuple[Node, ...]:
        """
        Retorna a união de todas as relações dos domínios ativos.
        """
        all_rels = []
        # Garante ordem determinística por nome do domínio
        for name in sorted(self.active_domains):
            if name in self.domains:
                all_rels.extend(self.domains[name].relations)
        return tuple(all_rels)

    def get_domain_for_entity(self, entity_node: Node) -> str | None:
        """
        Tenta identificar a qual domínio uma entidade pertence primariamente.
        (Heurística simples: onde ela aparece primeiro como sujeito)
        """
        label = entity_node.label
        for name in sorted(self.domains.keys()):
            domain = self.domains[name]
            for rel in domain.relations:
                if rel.kind == NodeKind.REL and len(rel.args) > 0:
                    if rel.args[0].label == label:
                        return name
        return None

# Instância global ou por sessão? Por sessão é melhor, mas vamos criar helpers aqui.
def create_domain_node(name: str, relations: List[Node]) -> Node:
    return struct(
        tag=entity("ontology_domain"),
        name=text(name),
        relation_count=text(str(len(relations)))
        # Relações não são serializadas dentro do nó para economizar, ficam no registro
    )
