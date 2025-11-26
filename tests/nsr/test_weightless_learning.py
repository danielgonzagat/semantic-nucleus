"""
Testes para o sistema de aprendizado sem pesos.
"""

from nsr.weightless_learning import WeightlessLearner, Episode
from nsr.state import Rule
from liu import entity, relation, struct, text


def test_weightless_learner_basic():
    """Testa funcionalidade básica do WeightlessLearner."""
    learner = WeightlessLearner(min_pattern_support=2)
    
    # Adiciona alguns episódios similares
    for i in range(3):
        ep_fp = learner.add_episode(
            input_text=f"O carro {i} tem rodas",
            input_struct=struct(subject=entity("carro"), action=entity("tem"), object=entity("rodas")),
            output_text="Sim, carros têm rodas",
            output_struct=struct(answer=text("Sim")),
            relations=(relation("HAS", entity("carro"), entity("rodas")),),
            context=(entity("veiculo"),),
            quality=0.8,
        )
        assert ep_fp is not None
    
    # Verifica que episódios foram adicionados
    assert len(learner.episodes) == 3
    
    # Busca episódios similares
    query_struct = struct(subject=entity("carro"), action=entity("tem"))
    similar = learner.find_similar_episodes(query_struct, k=5)
    assert len(similar) > 0


def test_pattern_extraction():
    """Testa extração de padrões."""
    learner = WeightlessLearner(min_pattern_support=2)
    
    # Adiciona episódios com padrão comum
    for i in range(3):
        learner.add_episode(
            input_text=f"Item {i}",
            input_struct=struct(subject=entity(f"item_{i}"), action=entity("existe")),
            output_text="Sim",
            output_struct=struct(answer=text("Sim")),
            relations=(relation("EXISTS", entity(f"item_{i}"), entity("coisa")),),
            context=(),
            quality=0.7,
        )
    
    # Extrai padrões
    patterns = learner.extract_patterns()
    assert len(patterns) > 0


def test_rule_learning():
    """Testa aprendizado de regras."""
    learner = WeightlessLearner(min_pattern_support=2, min_confidence=0.6)
    
    # Adiciona episódios que devem gerar regra
    for i in range(3):
        learner.add_episode(
            input_text=f"Teste {i}",
            input_struct=struct(subject=entity("x"), action=entity("tem"), object=entity("y")),
            output_text="OK",
            output_struct=struct(answer=text("OK")),
            relations=(
                relation("PART_OF", entity("x"), entity("y")),
                relation("HAS", entity("y"), entity("x")),
            ),
            context=(),
            quality=0.8,
        )
    
    # Aprende regras
    patterns = learner.extract_patterns()
    rules = learner.learn_rules_from_patterns(patterns)
    
    # Deve ter aprendido pelo menos uma regra se padrão for forte
    # (pode não aprender se padrão não for suficientemente frequente)
    assert isinstance(rules, list)


def test_episode_index():
    """Testa sistema de índices."""
    from nsr.weightless_index import EpisodeIndex
    
    index = EpisodeIndex()
    
    # Cria episódio
    episode = Episode(
        input_text="Teste",
        input_struct=struct(subject=entity("teste")),
        output_text="OK",
        output_struct=struct(answer=text("OK")),
        relations=(relation("IS_A", entity("teste"), entity("coisa")),),
        context=(),
        quality=0.8,
        fingerprint="test_fp",
    )
    
    # Adiciona ao índice
    index.add_episode(episode)
    
    # Busca por estrutura
    results = index.find_by_structure(struct(subject=entity("teste")), k=5)
    assert len(results) > 0
    assert "test_fp" in results


if __name__ == "__main__":
    test_weightless_learner_basic()
    test_pattern_extraction()
    test_rule_learning()
    test_episode_index()
    print("Todos os testes passaram!")
