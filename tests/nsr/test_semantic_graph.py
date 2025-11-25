"""
Testes para o Grafo Semântico e operador CONCEPTUALIZE.
"""

from typing import cast
from liu import Node, NodeKind, entity, relation, struct, operation, list_node
from nsr.semantic_graph import SemanticGraph
from nsr.state import ISR, SessionCtx, initial_isr
from nsr.operators import apply_operator

def test_semantic_graph_construction() -> None:
    rels = [
        relation("IS_A", entity("carro"), entity("veiculo")),
        relation("IS_A", entity("veiculo"), entity("objeto")),
        relation("PART_OF", entity("roda"), entity("carro")),
    ]
    graph = SemanticGraph.from_relations(rels)
    
    assert graph.node_count == 4  # carro, veiculo, objeto, roda
    
    # Test neighbor out
    neighbors = graph.get_neighbors(entity("carro"), rel_type="IS_A", direction="out")
    assert len(neighbors) == 1
    assert neighbors[0] == entity("veiculo")
    
    # Test neighbor in (PART_OF -> quem tem roda?)
    # "roda PART_OF carro" -> incoming de carro tem "PART_OF": [roda]
    parts = graph.get_neighbors(entity("carro"), rel_type="PART_OF", direction="in")
    assert len(parts) == 1
    assert parts[0] == entity("roda")

def test_transitive_closure() -> None:
    rels = [
        relation("IS_A", entity("dog"), entity("mammal")),
        relation("IS_A", entity("mammal"), entity("animal")),
        relation("IS_A", entity("animal"), entity("living_thing")),
    ]
    graph = SemanticGraph.from_relations(rels)
    
    parents = graph.transitive_closure(entity("dog"), "IS_A")
    assert len(parents) == 3
    # A ordem pode variar na travessia se fosse BFS/DFS sem critério, mas transitive_closure deve ser estável
    expected = {entity("mammal"), entity("animal"), entity("living_thing")}
    assert set(parents) == expected

def test_property_inheritance() -> None:
    # Hierarquia: Fusca -> Carro -> Veículo
    # Veículo tem "motor"
    # Carro tem "rodas"
    # Fusca tem "personalidade"
    rels = [
        relation("IS_A", entity("fusca"), entity("carro")),
        relation("IS_A", entity("carro"), entity("veiculo")),
        
        relation("HAS_PART", entity("veiculo"), entity("motor")),
        relation("HAS_PART", entity("carro"), entity("rodas")),
        relation("HAS_TRAIT", entity("fusca"), entity("personalidade")),
    ]
    graph = SemanticGraph.from_relations(rels)
    
    # 1. Propriedades diretas do Fusca
    props_direct = graph.get_properties(entity("fusca"), inherit=False)
    # Deve ter IS_A:carro e HAS_TRAIT:personalidade
    assert len(props_direct) == 2 
    
    # 2. Propriedades herdadas
    props_inherited = graph.get_properties(entity("fusca"), inherit=True)
    # IS_A:carro, HAS_TRAIT:personalidade
    # + (from carro) IS_A:veiculo, HAS_PART:rodas
    # + (from veiculo) HAS_PART:motor
    
    labels = [p[0] for p in props_inherited]
    targets = [p[1] for p in props_inherited]
    
    assert "HAS_PART" in labels
    assert entity("motor") in targets
    assert entity("rodas") in targets
    assert entity("personalidade") in targets

def test_operator_conceptualize() -> None:
    # Setup ISR
    session = SessionCtx()
    # Mock ontology in session
    ontology = (
        relation("IS_A", entity("pato"), entity("ave")),
        relation("CAN_DO", entity("ave"), entity("voar")),
    )
    session.kb_ontology = ontology
    
    # Init ISR com um "pato" na mão
    start_struct = struct(relations=list_node([])) # empty relations initially
    isr = initial_isr(start_struct, session)
    
    # O pato não está nas relações explícitas do ISR, mas a ontologia conhece pato->ave->voar.
    # Vamos pedir para "CONCEPTUALIZE(pato)"
    
    op = operation("CONCEPTUALIZE", entity("pato"))
    isr_new = apply_operator(isr, op, session)
    
    # O operador deve ter adicionado "CAN_DO(pato, voar)" e "IS_A(pato, ave)" ao CONTEXTO (não necessariamente relations)
    # Porque get_properties retorna (CAN_DO, voar) para pato (via herança de ave)
    
    context_labels = []
    for node in isr_new.context:
        if node.kind == NodeKind.REL:
            # relation(label, source, target)
            # A gente reconstruiu como relation(LABEL, focus, target)
            context_labels.append((node.label, node.args[0], node.args[1]))
            
    # Verifica se CAN_DO(pato, voar) apareceu
    assert ("CAN_DO", entity("pato"), entity("voar")) in context_labels
    assert ("IS_A", entity("pato"), entity("ave")) in context_labels

def test_semantic_graph_determinism() -> None:
    rels = [
        relation("A", entity("1"), entity("2")),
        relation("B", entity("1"), entity("3")),
        relation("C", entity("2"), entity("4")),
    ]
    import random
    
    # Tenta 10 ordens diferentes
    fingerprints = set()
    for _ in range(10):
        shuffled = list(rels)
        random.shuffle(shuffled)
        graph = SemanticGraph.from_relations(shuffled)
        
        # O estado interno do dict python 3.7+ preserva inserção, mas SemanticGraph deve ordenar ao sair
        # Vamos testar a saída de get_properties
        props = graph.get_properties(entity("1"))
        # Serializa para string para verificar determinismo
        fp = str([(p[0], str(p[1])) for p in props])
        fingerprints.add(fp)
        
    assert len(fingerprints) == 1, "SemanticGraph output must be deterministic regardless of input order"
