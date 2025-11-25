"""
Testes integrados para Multi-Ontologia e Meta-Learning.
"""

from typing import cast
from liu import Node, NodeKind, entity, relation, struct, operation, list_node, text, number
from nsr.state import ISR, SessionCtx, initial_isr, Rule
from nsr.operators import apply_operator
from nsr.multi_ontology import (
    MultiOntologyManager,
    OntologyDomain,
    build_default_multi_ontology_manager,
)
from nsr.meta_learning import MetaLearningEngine, meta_learn

def test_multi_ontology_manager() -> None:
    manager = MultiOntologyManager()
    
    # Domínio Médico
    med_rels = (
        relation("IS_A", entity("aspirina"), entity("medicamento")),
        relation("TREATS", entity("aspirina"), entity("dor_cabeca")),
    )
    med_domain = OntologyDomain(name="medical", relations=med_rels)
    manager.register_domain(med_domain)
    
    # Domínio Legal
    legal_rels = (
        relation("IS_A", entity("contrato"), entity("documento_legal")),
        relation("REQUIRES", entity("contrato"), entity("assinatura")),
    )
    legal_domain = OntologyDomain(name="legal", relations=legal_rels)
    manager.register_domain(legal_domain)
    
    # Por padrão, só core
    active = manager.get_active_relations()
    assert len(active) == 0 # core está vazio no init padrão do manager (sem carregar o default)
    
    # Ativa médico
    manager.activate_domain("medical")
    active = manager.get_active_relations()
    assert len(active) == 2
    labels = [r.args[0].label for r in active]
    assert "aspirina" in labels
    assert "contrato" not in labels
    
    # Domain detection
    domain = manager.get_domain_for_entity(entity("aspirina"))
    assert domain == "medical"
    
    domain = manager.get_domain_for_entity(entity("contrato"))
    assert domain == "legal" # Mesmo inativo, ele sabe onde está


def test_multi_ontology_infers_domains_from_text() -> None:
    manager = build_default_multi_ontology_manager()
    text_value = "O paciente tomou aspirina no hospital e assinou um contrato legal."
    inferred = manager.infer_domains(text_value=text_value)
    assert "medical" in inferred
    assert "legal" in inferred
    for domain in inferred:
        manager.activate_domain(domain)
    scope_node = manager.build_scope_node(
        inferred_domains=inferred,
        active_domains=tuple(sorted(manager.active_domains)),
    )
    scope_fields = dict(scope_node.fields)
    active_list = scope_fields["active"]
    assert active_list.kind.name == "LIST"
    active_labels = {entry.label for entry in active_list.args}
    assert "medical" in active_labels
    assert "legal" in active_labels
    relation_total = scope_fields["relation_total"]
    assert relation_total.value is not None and relation_total.value > 0

def test_meta_learning_operator() -> None:
    session = SessionCtx()
    start_struct = struct(relations=list_node([]))
    isr = initial_isr(start_struct, session)
    
    # Simula um ISR de alta qualidade (sucesso)
    # Vamos hackear o quality
    # Em um cenário real, o meta_learn precisaria de um trace rico para aprender algo.
    # Nosso mock atual de meta_learn retorna lista vazia por default, 
    # então vamos testar o mecanismo do operador, não a inteligência de indução (que é complexa).
    
    # Mock do meta_learn para retornar uma regra dummy
    import nsr.operators
    # Se o atributo não existe, definimos ele para o patch funcionar e não quebrar o restore
    if not hasattr(nsr.operators, "meta_learn"):
        # Isso é estranho, pois importamos no operators.py
        # Mas se falhar, vamos definir um dummy para o teste prosseguir
        nsr.operators.meta_learn = None 
    
    original_meta_learn = nsr.operators.meta_learn
    
    dummy_rule = Rule(if_all=(entity("A"),), then=entity("B"))
    
    # Monkeypatch
    nsr.operators.meta_learn = lambda ctx: [dummy_rule]
    
    try:
        # Prepara ISR com qualidade alta
        # Hack para acessar _update que é interno
        # from nsr.operators import _update  <-- isso reimporta, não pega a função do módulo que patcheamos?
        # Não, _update está no mesmo módulo. 
        # Mas precisamos chamar apply_operator, que chama _op_learn, que usa meta_learn (que patcheamos).
        
        # Vamos hackear a qualidade do ISR manualmente pois é dataclass frozen? Não, é slots=True, mutável?
        # ISR é frozen por convenção em alguns lugares mas slots=True permite setar se não for frozen=True.
        # Verifiquei: @dataclass(slots=True) sem frozen=True é mutável.
        isr.quality = 0.9
        
        op = operation("LEARN")
        isr_new = apply_operator(isr, op, session)
        
        # Verifica se a regra foi adicionada à sessão
        assert len(session.kb_rules) == 1
        assert session.kb_rules[0] == dummy_rule
        
        # Verifica resumo no contexto
        # O nó de resumo pode estar em qualquer posição no contexto, mas geralmente é o último
        summaries = [n for n in isr_new.context 
                     if n.kind == NodeKind.STRUCT and 
                     _get_struct_tag(n) == "learning_summary"]
        assert len(summaries) >= 1
        
    finally:
        # Restore
        nsr.operators.meta_learn = original_meta_learn

def _get_struct_tag(node: Node) -> str | None:
    fields = dict(node.fields)
    tag = fields.get("tag")
    return tag.label if tag else None

import sys
