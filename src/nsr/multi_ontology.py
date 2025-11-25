"""
Gerenciador de ontologias múltiplas e detector de escopos semânticos.

Permite segmentar o grafo em namespaces (core, code, medical, legal, etc),
inferir quais domínios são relevantes para uma entrada e produzir nós LIU
auditáveis (`ontology_scope`) que descrevem exatamente quais bases de conhecimento
estão ativas e quantas relações sustentam cada uma.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import blake2b
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from liu import (
    Node,
    NodeKind,
    entity,
    list_node,
    number,
    relation,
    struct,
    text,
)


@dataclass(frozen=True, slots=True)
class OntologyDomain:
    name: str
    relations: Tuple[Node, ...]
    version: str = "1.0"
    dependencies: Tuple[str, ...] = tuple()
    keywords: Tuple[str, ...] = tuple()


class MultiOntologyManager:
    """
    Gerencia o carregamento, ativação e auditoria de múltiplos domínios.
    """

    def __init__(self):
        self.domains: Dict[str, OntologyDomain] = {}
        self.domain_keywords: Dict[str, Set[str]] = {}
        self.active_domains: Set[str] = set()

    def register_domain(self, domain: OntologyDomain) -> None:
        self.domains[domain.name] = domain
        self.domain_keywords[domain.name] = _normalize_keywords(domain.keywords, domain.relations)

    def activate_domain(self, name: str) -> None:
        if name not in self.domains:
            return
        if name in self.active_domains:
            return
        self.active_domains.add(name)
        for dep in self.domains[name].dependencies:
            self.activate_domain(dep)

    def deactivate_domain(self, name: str) -> None:
        if name in self.active_domains:
            self.active_domains.remove(name)

    def get_active_relations(self) -> Tuple[Node, ...]:
        relations: List[Node] = []
        for name in sorted(self.active_domains):
            domain = self.domains.get(name)
            if domain is None:
                continue
            relations.extend(domain.relations)
        return tuple(relations)

    def get_domain_for_entity(self, entity_node: Node) -> str | None:
        label = entity_node.label
        for name in sorted(self.domains):
            domain = self.domains[name]
            for rel in domain.relations:
                if rel.kind is NodeKind.REL and rel.args and rel.args[0].label == label:
                    return name
        return None

    def infer_domains(
        self,
        *,
        text_value: str | None = None,
        struct_node: Node | None = None,
    ) -> Tuple[str, ...]:
        """
        Retorna uma tupla determinística com os domínios cujo vocabulário
        aparece na entrada atual.
        """

        tokens: Set[str] = set()
        if text_value:
            tokens.update(_tokenize_text(text_value))
        if struct_node is not None:
            tokens.update(_collect_entity_labels(struct_node))
        inferred: List[str] = []
        for name in sorted(self.domains):
            keywords = self.domain_keywords.get(name, set())
            if not keywords:
                continue
            if tokens & keywords:
                inferred.append(name)
        return tuple(inferred)

    def build_scope_node(
        self,
        *,
        inferred_domains: Sequence[str],
        active_domains: Sequence[str] | None = None,
    ) -> Node:
        """
        Constrói um nó LIU `ontology_scope` listando domínios ativos/inferidos.
        """

        active = tuple(sorted(active_domains or self.active_domains))
        inferred = tuple(sorted(dict.fromkeys(inferred_domains)))
        relation_total = 0
        inferred_set = set(inferred)
        detail_nodes: List[Node] = []
        for name in active:
            domain = self.domains.get(name)
            if domain is None:
                continue
            relation_count = len(domain.relations)
            relation_total += relation_count
            status = "inferred" if name in inferred_set else "active"
            detail_nodes.append(
                struct(
                    tag=entity("ontology_scope_domain"),
                    name=entity(name),
                    version=text(domain.version),
                    relation_count=number(relation_count),
                    status=entity(status),
                )
            )
        digest = _scope_digest(active, inferred, relation_total)
        fields: Dict[str, Node] = {
            "tag": entity("ontology_scope"),
            "domain_count": number(len(active)),
            "relation_total": number(relation_total),
            "digest": text(digest),
            "active": list_node(entity(name) for name in active),
            "details": list_node(detail_nodes),
        }
        if inferred:
            fields["inferred"] = list_node(entity(name) for name in inferred)
        return struct(**fields)


def build_default_multi_ontology_manager(
    extra_domains: Sequence[OntologyDomain] | None = None,
) -> MultiOntologyManager:
    """
    Cria um gerenciador com os domínios normativos (core/code) e
    domínios estendidos (medical, legal, finance).
    """

    from ontology import core as core_ontology
    from ontology import code as code_ontology

    manager = MultiOntologyManager()
    manager.register_domain(
        OntologyDomain(
            name="core",
            version="core.v1",
            relations=tuple(core_ontology.CORE_V1),
            keywords=tuple(),
        )
    )
    manager.register_domain(
        OntologyDomain(
            name="code",
            version="code.v1",
            relations=tuple(code_ontology.CODE_V1),
            keywords=tuple(),
        )
    )
    for domain in DEFAULT_EXTRA_DOMAINS:
        manager.register_domain(domain)
    if extra_domains:
        for domain in extra_domains:
            manager.register_domain(domain)
    manager.activate_domain("core")
    manager.activate_domain("code")
    return manager


DEFAULT_EXTRA_DOMAINS: Tuple[OntologyDomain, ...] = (
    OntologyDomain(
        name="medical",
        version="medical.v1",
        relations=(
            relation("IS_A", entity("aspirina"), entity("medicamento")),
            relation("TREATS", entity("aspirina"), entity("dor_cabeca")),
            relation("ASSIGNED_TO", entity("medico"), entity("paciente")),
            relation("LOCATED_IN", entity("paciente"), entity("hospital")),
        ),
        keywords=(
            "aspirina",
            "paciente",
            "medico",
            "saude",
            "hospital",
            "tratamento",
            "diagnostico",
            "dor",
        ),
    ),
    OntologyDomain(
        name="legal",
        version="legal.v1",
        relations=(
            relation("IS_A", entity("contrato"), entity("documento_legal")),
            relation("REQUIRES", entity("contrato"), entity("assinatura")),
            relation("FILED_IN", entity("processo_judicial"), entity("tribunal")),
        ),
        keywords=(
            "contrato",
            "assinatura",
            "legal",
            "juridico",
            "tribunal",
            "processo",
            "advogado",
        ),
    ),
    OntologyDomain(
        name="finance",
        version="finance.v1",
        relations=(
            relation("IS_A", entity("acao"), entity("ativo_financeiro")),
            relation("MEASURED_BY", entity("acao"), entity("preco_mercado")),
            relation("OWNS", entity("investidor"), entity("acao")),
        ),
        keywords=(
            "acao",
            "bolsa",
            "investidor",
            "mercado",
            "financeiro",
            "ativo",
            "preco",
        ),
    ),
)


def _normalize_keywords(keywords: Iterable[str], relations: Tuple[Node, ...]) -> Set[str]:
    normalized = {kw.strip().lower() for kw in keywords if kw and kw.strip()}
    if normalized:
        return normalized
    return _derive_keywords(relations)


def _derive_keywords(relations: Tuple[Node, ...]) -> Set[str]:
    tokens: Set[str] = set()
    for rel in relations:
        if rel.kind is NodeKind.REL:
            for arg in rel.args:
                if arg.kind is NodeKind.ENTITY:
                    label = (arg.label or "").strip().lower()
                    if label:
                        tokens.add(label)
                elif arg.kind is NodeKind.TEXT and arg.label:
                    tokens.update(_tokenize_text(arg.label))
    return tokens


_TOKEN_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ_]+")


def _tokenize_text(value: str) -> Set[str]:
    return {match.group(0).lower() for match in _TOKEN_PATTERN.finditer(value)}


def _collect_entity_labels(node: Node) -> Set[str]:
    labels: Set[str] = set()
    stack = [node]
    seen: Set[int] = set()
    while stack:
        current = stack.pop()
        pointer = id(current)
        if pointer in seen:
            continue
        seen.add(pointer)
        if current.kind is NodeKind.ENTITY:
            label = (current.label or "").strip().lower()
            if label:
                labels.add(label)
        elif current.kind is NodeKind.TEXT and current.label:
            labels.update(_tokenize_text(current.label))
        if current.kind is NodeKind.STRUCT:
            stack.extend(value for _, value in current.fields)
        elif current.kind in {NodeKind.REL, NodeKind.LIST, NodeKind.OP}:
            stack.extend(current.args)
    return labels


def _scope_digest(active: Sequence[str], inferred: Sequence[str], total_relations: int) -> str:
    hasher = blake2b(digest_size=16)
    for name in active:
        hasher.update(f"A:{name}".encode("utf-8"))
    for name in inferred:
        hasher.update(f"I:{name}".encode("utf-8"))
    hasher.update(f"T:{total_relations}".encode("utf-8"))
    return hasher.hexdigest()


__all__ = [
    "OntologyDomain",
    "MultiOntologyManager",
    "build_default_multi_ontology_manager",
    "DEFAULT_EXTRA_DOMAINS",
]
