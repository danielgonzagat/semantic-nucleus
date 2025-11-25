"""
Testes para Meta-Reflexão e Árvore de Justificativa.
"""

from typing import cast
from liu import Node, NodeKind, entity, relation, struct, operation, list_node, text, number
from nsr.state import ISR, SessionCtx, initial_isr
from nsr.operators import apply_operator
from nsr.meta_reflection import MetaReflectionEngine, JustificationNode

def test_justification_tree_building() -> None:
    # Simula um contexto com uma prova lógica
    proof_node = struct(
        tag=entity("logic_proof"),
        query=text("chuva"),
        truth=entity("true"),
        facts=list_node([
            struct(statement=text("nuvens"), truth=entity("true")),
            struct(statement=text("se nuvens entao chuva"), truth=entity("true"))
        ])
    )
    
    context = (proof_node,)
    answer_node = text("chuva") # A resposta que queremos justificar
    
    # A engine deve ligar a resposta 'chuva' à prova 'logic_proof'
    # Nota: No código atual, _is_proof_for é simplificado, vamos assumir que ele aceita
    
    engine = MetaReflectionEngine([])
    tree = engine.build_justification_tree(answer_node, context)
    
    assert tree is not None
    assert tree.type == "LOGIC_PROOF"
    assert "chuva" in tree.description
    assert len(tree.dependencies) == 2 # 2 fatos
    assert tree.dependencies[0].type == "FACT"

def test_operator_reflect() -> None:
    session = SessionCtx()
    start_struct = struct(relations=list_node([]))
    isr = initial_isr(start_struct, session)
    
    # Prepara um ISR com uma resposta e um contexto justificável
    proof_node = struct(
        tag=entity("logic_proof"),
        query=text("socrates mortal"),
        truth=entity("true"),
        facts=list_node([])
    )
    
    # Atualiza ISR manualmente
    from nsr.operators import _update
    new_context = isr.context + (proof_node,)
    new_answer = struct(answer=text("socrates mortal"))
    isr = _update(isr, context=new_context, answer=new_answer)
    
    # Aplica REFLECT
    op = operation("REFLECT")
    isr_new = apply_operator(isr, op, session)
    
    # A resposta nova deve conter o campo 'justification_tree'
    fields = dict(isr_new.answer.fields)
    assert "justification_tree" in fields
    
    tree_node = fields["justification_tree"]
    assert tree_node.kind == NodeKind.STRUCT
    tree_fields = dict(tree_node.fields)
    assert tree_fields["tag"] == entity("justification_node")
    assert tree_fields["type"] == entity("LOGIC_PROOF")
