"""
Integração do Sistema de Aprendizado Sem Pesos com o Runtime.

Este módulo integra o WeightlessLearner ao pipeline de processamento,
permitindo aprendizado automático e contínuo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from liu import Node

if TYPE_CHECKING:
    from .runtime import RunOutcome
    from .state import SessionCtx
    from .meta_transformer import MetaTransformResult
    from .weightless_learning import WeightlessLearner, Episode


def ensure_weightless_learner(session: "SessionCtx") -> "WeightlessLearner":
    """Garante que o session tem um WeightlessLearner inicializado."""
    from .weightless_learning import WeightlessLearner
    
    if session.weightless_learner is None:
        session.weightless_learner = WeightlessLearner()
    
    return session.weightless_learner


def record_episode_for_learning(
    outcome: "RunOutcome",
    meta_info: "MetaTransformResult",
    session: "SessionCtx",
) -> str | None:
    """
    Registra um episódio para aprendizado.
    
    Retorna o fingerprint do episódio ou None se não foi registrado.
    """
    learner = ensure_weightless_learner(session)
    
    # Só registra se qualidade for suficiente
    if outcome.quality < 0.5:
        return None
    
    # Cria episódio
    episode_fp = learner.add_episode(
        input_text=meta_info.input_text,
        input_struct=meta_info.struct_node,
        output_text=outcome.answer,
        output_struct=outcome.isr.answer,
        relations=outcome.isr.relations,
        context=outcome.isr.context,
        quality=outcome.quality,
    )
    
    return episode_fp


def find_similar_episodes_for_context(
    query_struct: Node,
    session: "SessionCtx",
    k: int = 5,
) -> list["Episode"]:
    """
    Busca episódios similares que podem informar o processamento atual.
    
    Retorna lista vazia se não houver learner ou episódios similares.
    """
    if session.weightless_learner is None:
        return []
    
    learner = session.weightless_learner
    
    # Extrai relações da query
    query_relations = _extract_relations(query_struct)
    
    # Busca episódios similares
    similar = learner.find_similar_episodes(
        query_struct=query_struct,
        query_relations=query_relations,
        k=k,
    )
    
    return similar


def apply_learned_rules_to_session(session: "SessionCtx") -> int:
    """
    Aplica regras aprendidas ao session.
    
    Retorna número de novas regras adicionadas.
    """
    if session.weightless_learner is None:
        return 0
    
    learner = session.weightless_learner
    
    # Pega regras aprendidas que ainda não estão no session
    existing_rule_fps = {_rule_fingerprint(rule) for rule in session.kb_rules}
    
    new_rules = []
    for rule in learner.learned_rules:
        rule_fp = _rule_fingerprint(rule)
        if rule_fp not in existing_rule_fps:
            new_rules.append(rule)
            existing_rule_fps.add(rule_fp)
    
    if new_rules:
        # Adiciona novas regras
        session.kb_rules = tuple(list(session.kb_rules) + new_rules)
    
    return len(new_rules)


def _extract_relations(struct: Node) -> list[Node]:
    """Extrai todas as relações de uma estrutura."""
    from liu import NodeKind
    
    relations = []
    
    if struct.kind is NodeKind.REL:
        relations.append(struct)
    
    for arg in struct.args:
        relations.extend(_extract_relations(arg))
    
    if struct.kind is NodeKind.STRUCT:
        for _, value in struct.fields:
            relations.extend(_extract_relations(value))
    
    return relations


def _rule_fingerprint(rule: "Rule") -> str:
    """Cria fingerprint determinístico de uma regra."""
    from hashlib import blake2b
    from .state import Rule
    
    hasher = blake2b(digest_size=16)
    for antecedent in rule.if_all:
        from liu import fingerprint
        hasher.update(fingerprint(antecedent).encode("utf-8"))
    from liu import fingerprint
    hasher.update(fingerprint(rule.then).encode("utf-8"))
    return hasher.hexdigest()


__all__ = [
    "ensure_weightless_learner",
    "record_episode_for_learning",
    "find_similar_episodes_for_context",
    "apply_learned_rules_to_session",
]
