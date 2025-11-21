"""
Renderizadores determinísticos usados para explicar o estado do NSR.
"""

from __future__ import annotations

from typing import Iterable, Tuple

from liu import Node, NodeKind, struct, text

from .state import ISR


def render_explanation(
    isr: ISR,
    focus: Node | None = None,
    *,
    relation_limit: int = 4,
    context_limit: int = 3,
    ops_limit: int = 4,
) -> str:
    """
    Constrói um relatório determinístico cobrindo foco, relações, contexto e fila Φ.
    """

    focus_node = focus if focus is not None else struct()
    relations_preview = _relations_summary(isr.relations, relation_limit)
    context_preview = _context_summary(isr.context, context_limit)
    ops_preview = _ops_summary(isr.ops_queue, ops_limit)
    focus_desc = _focus_description(focus_node)
    parts = [
        "Explicação determinística:",
        f"- Foco: {focus_desc}",
        f"- Qualidade: {isr.quality:.2f}",
        f"- Relações ({len(isr.relations)}): {relations_preview}",
        f"- Contexto ({len(isr.context)}): {context_preview}",
        f"- Próximos Φ: {ops_preview}",
    ]
    return "\n".join(parts)


def render_struct_sentence(node: Node) -> str:
    """
    Converte um STRUCT LIU em sentença legível, preservando relações derivadas.
    """

    subject = _field_label(node, "subject")
    action = _field_label(node, "action")
    obj = _field_label(node, "object")
    modifier = _field_label(node, "modifier")
    relations_summary = _format_relations(_field_node(node, "relations"))
    pieces = [subject, action]
    if obj:
        pieces.append(obj)
    if modifier:
        pieces.append(modifier)
    sent = " ".join(filter(None, pieces)).strip()
    clauses: list[str] = []
    if not sent:
        clauses.append("Resposta não determinada")
    else:
        clauses.append(sent[0].upper() + sent[1:])
    if relations_summary:
        clauses.append(f"Relações: {relations_summary}")
    final = ". ".join(clauses) + "."
    return final


def render_struct_node(node: Node) -> Node:
    """
    Retorna um nó TEXT contendo a frase determinística do STRUCT informado.
    """

    return text(render_struct_sentence(node))


def _focus_description(node: Node) -> str:
    if not node.fields and not node.args and not node.label:
        return "estrutura vazia"
    return _describe_node(node)


def _relations_summary(relations: Tuple[Node, ...], limit: int) -> str:
    if not relations:
        return "sem relações"
    phrases = [_render_relation(rel) or rel.label or "REL" for rel in relations[: max(1, limit)]]
    summary = "; ".join(phrases)
    if len(relations) > limit:
        summary += f"; ...(+{len(relations) - limit})"
    return summary


def _context_summary(context: Tuple[Node, ...], limit: int) -> str:
    if not context:
        return "contexto vazio"
    limit = max(1, limit)
    if len(context) <= limit:
        items = context
        prefix = ""
    else:
        items = context[-limit:]
        prefix = f"...(+{len(context) - limit}) "
    descriptions = [_describe_node(node) for node in items]
    return prefix + "; ".join(descriptions)


def _ops_summary(ops_queue: Iterable[Node], limit: int) -> str:
    limit = max(1, limit)
    items = list(ops_queue)
    if not items:
        return "fila vazia"
    preview = [(node.label or "NOOP") for node in items[:limit]]
    summary = ", ".join(preview)
    if len(items) > limit:
        summary += f", ...(+{len(items) - limit})"
    return summary


def _describe_node(node: Node) -> str:
    if node.kind is NodeKind.REL:
        relation_text = _render_relation(node)
        return relation_text or f"REL:{node.label or '?'}"
    if node.kind is NodeKind.STRUCT:
        return render_struct_sentence(node)
    if node.kind is NodeKind.TEXT:
        return node.label or "texto vazio"
    if node.kind is NodeKind.ENTITY:
        return node.label or "entidade"
    if node.kind is NodeKind.NUMBER:
        return f"número {node.value:.3f}" if node.value is not None else "número indefinido"
    if node.kind is NodeKind.BOOL:
        return "verdadeiro" if node.value else "falso"
    if node.kind is NodeKind.LIST:
        return f"lista({len(node.args)})"
    if node.kind is NodeKind.OP:
        return f"Φ:{node.label or 'NOOP'}"
    return node.kind.value


def _field_label(node: Node, field: str) -> str:
    target = _field_node(node, field)
    if target is None:
        return ""
    if target.kind is NodeKind.ENTITY:
        return target.label or ""
    if target.kind is NodeKind.LIST:
        return " ".join(item.label or "" for item in target.args if item.label)
    if target.kind is NodeKind.TEXT:
        return target.label or ""
    return ""


def _field_node(node: Node, field: str) -> Node | None:
    for key, value in node.fields:
        if key == field:
            return value
    return None


def _format_relations(relations_node: Node | None) -> str | None:
    if relations_node is None or relations_node.kind is not NodeKind.LIST:
        return None
    phrases = []
    for candidate in relations_node.args:
        phrase = _render_relation(candidate)
        if phrase:
            phrases.append(phrase)
    if not phrases:
        return None
    return "; ".join(phrases)


def _render_relation(node: Node) -> str | None:
    if node.kind is not NodeKind.REL or not node.label:
        return None
    if len(node.args) < 2:
        return None
    source = _node_token(node.args[0])
    target = _node_token(node.args[1])
    if not source or not target:
        return None
    rel_label = node.label.replace("_", " ").lower()
    return f"{source} {rel_label} {target}"


def _node_token(node: Node) -> str:
    if node.kind in (NodeKind.ENTITY, NodeKind.TEXT):
        return (node.label or "").strip()
    return ""


__all__ = ["render_explanation", "render_struct_sentence", "render_struct_node"]
