"""
Testes para o módulo de Ambiguidade e operador DISAMBIGUATE.
"""

from typing import cast
from liu import Node, NodeKind, entity, relation, struct, operation, list_node, text
from nsr.semantic_graph import SemanticGraph
from nsr.state import ISR, SessionCtx, initial_isr
from nsr.operators import apply_operator
from nsr.ambiguity import detect_ambiguity, AmbiguityResolver


def test_ambiguity_detection() -> None:
    # Cria uma struct que simula uma ambiguidade detectada pelo parser (ex: "manga")
    ambiguous_struct = struct(
        tag=entity("AMBIGUOUS_TERM"),
        term=text("manga"),
        candidates=list_node([
            entity("manga_fruta"),
            entity("manga_roupa")
        ])
    )
    
    session = SessionCtx()
    start_struct = struct(relations=list_node([]))
    isr = initial_isr(start_struct, session)
    
    # Injeta a ambiguidade no contexto
    context_with_ambiguity = isr.context + (ambiguous_struct,)
    isr_amb = isr.snapshot()
    # Como ISR é imutável via snapshot mas context é tuple, precisamos criar um novo ISR 
    # ou usar _update (mas _update é interno). Vamos criar um mock rápido.
    # O jeito certo é usar a estrutura de testes do ISR.
    
    # Vamos usar apply_operator com um operador dummy se precisássemos, mas aqui queremos testar a função direta
    # Então vamos hackear o ISR mockado
    from nsr.operators import _update
    isr_amb = _update(isr, context=context_with_ambiguity)
    
    detected = detect_ambiguity(isr_amb)
    assert len(detected) == 1
    term, cands = detected[0]
    assert term == "manga"
    assert len(cands) == 2
    assert entity("manga_fruta") in cands


def test_ambiguity_resolution_by_graph_density() -> None:
    # Cenário: Contexto fala de "camisa" e "botão". Termo ambíguo: "manga" (roupa vs fruta).
    # Ontologia:
    # manga_roupa PART_OF camisa
    # manga_fruta IS_A fruta
    
    ontology = [
        relation("PART_OF", entity("manga_roupa"), entity("camisa")),
        relation("IS_A", entity("manga_fruta"), entity("fruta")),
        relation("HAS_PART", entity("camisa"), entity("botao")),
    ]
    
    graph = SemanticGraph.from_relations(ontology)
    resolver = AmbiguityResolver(graph)
    
    # Contexto tem "camisa"
    context = (entity("camisa"),)
    
    candidates = [entity("manga_fruta"), entity("manga_roupa")]
    
    interpretations = resolver.resolve("manga", candidates, context)
    
    # Esperamos que manga_roupa vença porque tem conexão direta com 'camisa' no grafo
    best = interpretations[0]
    assert best.meaning_node == entity("manga_roupa")
    assert best.score > 1.0  # Ganhou ponto por conexão


def test_operator_disambiguate() -> None:
    # Setup completo
    ontology = (
        relation("IS_A", entity("banco_assento"), entity("mobilia")),
        relation("IS_A", entity("banco_financeiro"), entity("instituicao")),
        relation("RELATED_TO", entity("dinheiro"), entity("financeiro")),
        relation("RELATED_TO", entity("banco_financeiro"), entity("dinheiro")),
    )
    
    session = SessionCtx()
    session.kb_ontology = ontology
    
    # Contexto inicial tem "dinheiro" e uma ambiguidade "banco"
    ambiguous_struct = struct(
        tag=entity("AMBIGUOUS_TERM"),
        term=text("banco"),
        candidates=list_node([
            entity("banco_assento"),
            entity("banco_financeiro")
        ])
    )
    
    start_struct = struct(relations=list_node([]))
    isr = initial_isr(start_struct, session)
    
    # Injeta contexto manual via hack _update ou recriando ISR, 
    # mas vamos usar o ciclo normal: adicionar ao contexto via struct inicial seria o ideal
    # Mas initial_isr coloca struct_node no contexto.
    # Vamos fazer o hack do _update para teste unitário ser preciso
    from nsr.operators import _update
    
    new_context = isr.context + (entity("dinheiro"), ambiguous_struct)
    isr = _update(isr, context=new_context, relations=ontology) # Carrega ontologia nas relações para o grafo ver
    
    # Estado antes: incerteza alta (padrão 1.0)
    assert isr.uncertainty_level == 1.0
    
    # Aplica DISAMBIGUATE
    op = operation("DISAMBIGUATE")
    isr_new = apply_operator(isr, op, session)
    
    # Verifica se resolveu
    # Deve ter escolhido banco_financeiro (conectado a dinheiro)
    
    resolutions = [n for n in isr_new.context 
                   if n.kind == NodeKind.STRUCT and 
                   dict(n.fields).get("tag") == entity("RESOLUTION")]
    
    assert len(resolutions) == 1
    res = resolutions[0]
    fields = dict(res.fields)
    assert fields["selected"] == entity("banco_financeiro")
    
    # Incerteza deve ter baixado
    assert isr_new.uncertainty_level < 1.0
