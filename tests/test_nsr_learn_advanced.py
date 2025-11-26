"""
Testes para os módulos avançados do NSR-Learn.

Testa:
- Analogia estrutural
- Cadeia de raciocínio
- Abstração hierárquica
- Atenção simbólica
- Geração de texto
- Motor integrado
"""

import pytest
from typing import Set


# ==================== TESTES DE ANALOGIA ====================

class TestAnalogy:
    """Testes para o módulo de analogia."""
    
    def test_structure_creation(self):
        """Testa criação de estruturas relacionais."""
        from nsr_learn.analogy import Structure, Relation
        
        facts = [
            ("atrai", "sol", "planetas"),
            ("orbita", "planetas", "sol"),
        ]
        
        struct = Structure.from_facts("solar", facts)
        
        assert struct.name == "solar"
        assert len(struct.relations) == 2
        assert "sol" in struct.entities
        assert "planetas" in struct.entities
    
    def test_analogy_finding(self):
        """Testa descoberta de analogias."""
        from nsr_learn.analogy import AnalogyEngine, SOLAR_SYSTEM, ATOM
        
        engine = AnalogyEngine()
        engine.register_structure(SOLAR_SYSTEM)
        engine.register_structure(ATOM)
        
        analogy = engine.find_analogy(SOLAR_SYSTEM, ATOM, min_score=0.1)
        
        assert analogy is not None
        assert analogy.confidence > 0
        assert analogy.source_domain == "sistema_solar"
        assert analogy.target_domain == "atomo"
    
    def test_structural_mapping(self):
        """Testa mapeamento estrutural."""
        from nsr_learn.analogy import AnalogyEngine, Structure
        
        engine = AnalogyEngine()
        
        # Estruturas simples para testar
        source = Structure.from_facts("A", [("rel", "x", "y")])
        target = Structure.from_facts("B", [("rel", "a", "b")])
        
        engine.register_structure(source)
        engine.register_structure(target)
        
        analogy = engine.find_analogy(source, target)
        
        assert analogy is not None
        assert "x" in analogy.mapping.entity_map
        assert "rel" in analogy.mapping.relation_map


# ==================== TESTES DE RACIOCÍNIO ====================

class TestReasoning:
    """Testes para o módulo de raciocínio."""
    
    def test_knowledge_base(self):
        """Testa base de conhecimento."""
        from nsr_learn.reasoning import KnowledgeBase
        
        kb = KnowledgeBase()
        kb.add_fact("math", "2+2=4")
        kb.add_rule("número par", "divisível por 2", "paridade")
        kb.add_definition("algoritmo", "sequência de passos")
        
        facts = kb.query_facts("math")
        assert "2+2=4" in facts
        
        rules = kb.find_applicable_rules("número par")
        assert len(rules) == 1
        assert rules[0][2] == "paridade"
    
    def test_chain_of_thought(self):
        """Testa cadeia de raciocínio."""
        from nsr_learn.reasoning import ChainOfThoughtEngine, KnowledgeBase
        
        kb = KnowledgeBase()
        kb.add_fact("biologia", "mamíferos têm sangue quente")
        kb.add_rule("mamífero", "sangue quente", "termo")
        
        engine = ChainOfThoughtEngine(kb)
        chain = engine.reason("O que sabemos sobre mamíferos?")
        
        assert chain.query == "O que sabemos sobre mamíferos?"
        assert len(chain.steps) > 0
        assert chain.conclusion != ""
        assert chain.total_confidence > 0
    
    def test_reasoning_step_types(self):
        """Testa tipos de passos de raciocínio."""
        from nsr_learn.reasoning import ChainOfThoughtEngine, KnowledgeBase, StepType
        
        engine = ChainOfThoughtEngine(KnowledgeBase())
        chain = engine.reason("teste")
        
        step_types = {s.step_type for s in chain.steps}
        
        assert StepType.OBSERVATION in step_types
        assert StepType.CONCLUSION in step_types
    
    def test_chain_validation(self):
        """Testa validação da cadeia."""
        from nsr_learn.reasoning import ChainOfThoughtEngine, KnowledgeBase
        
        engine = ChainOfThoughtEngine(KnowledgeBase())
        chain = engine.reason("validar cadeia")
        
        valid, errors = chain.validate()
        
        assert valid is True
        assert len(errors) == 0


# ==================== TESTES DE ABSTRAÇÃO ====================

class TestAbstraction:
    """Testes para o módulo de abstração."""
    
    def test_taxonomy_creation(self):
        """Testa criação de taxonomia."""
        from nsr_learn.abstraction import Taxonomy
        
        tax = Taxonomy()
        tax.add_concept("ANIMAL", 0, {"vivo"})
        tax.add_concept("MAMIFERO", 1, {"quente"})
        tax.add_relation("MAMIFERO", "ANIMAL")
        
        assert "ANIMAL" in tax.concepts
        assert "MAMIFERO" in tax.concepts
        assert "ANIMAL" in tax.nodes["MAMIFERO"].parents
    
    def test_inheritance(self):
        """Testa herança de propriedades."""
        from nsr_learn.abstraction import create_default_taxonomy
        
        tax = create_default_taxonomy()
        
        # Cachorro herda de Mamífero, Animal, Ser Vivo
        props = tax.get_inherited_properties("CACHORRO")
        
        assert "late" in props  # Própria
        assert "amamenta" in props  # De MAMIFERO
        assert "move" in props  # De ANIMAL
        assert "nasce" in props  # De SER_VIVO
    
    def test_is_a_relation(self):
        """Testa relação IS-A."""
        from nsr_learn.abstraction import create_default_taxonomy
        
        tax = create_default_taxonomy()
        
        assert tax.is_a("CACHORRO", "MAMIFERO") is True
        assert tax.is_a("CACHORRO", "ANIMAL") is True
        assert tax.is_a("CACHORRO", "PLANTA") is False
    
    def test_lowest_common_ancestor(self):
        """Testa ancestral comum mais baixo."""
        from nsr_learn.abstraction import create_default_taxonomy
        
        tax = create_default_taxonomy()
        
        lca = tax.lowest_common_ancestor("CACHORRO", "GATO")
        assert lca == "MAMIFERO"
        
        lca = tax.lowest_common_ancestor("CACHORRO", "AVE")
        assert lca == "ANIMAL"
    
    def test_semantic_distance(self):
        """Testa distância semântica."""
        from nsr_learn.abstraction import create_default_taxonomy
        
        tax = create_default_taxonomy()
        
        d1 = tax.semantic_distance("CACHORRO", "GATO")
        d2 = tax.semantic_distance("CACHORRO", "AVE")
        d3 = tax.semantic_distance("CACHORRO", "PLANTA")
        
        assert d1 < d2  # Cachorro-Gato mais próximo que Cachorro-Ave
        assert d2 < d3  # Cachorro-Ave mais próximo que Cachorro-Planta


# ==================== TESTES DE ATENÇÃO ====================

class TestAttention:
    """Testes para o módulo de atenção."""
    
    def test_attention_context(self):
        """Testa contexto de atenção."""
        from nsr_learn.attention import AttentionContext
        
        ctx = AttentionContext(query="teste")
        ctx.add_to_history("item1", 0)
        ctx.add_to_history("item2", 1)
        
        assert len(ctx.history) == 2
        assert ctx.get_recency("item2") > ctx.get_recency("item1")
    
    def test_symbolic_attention(self):
        """Testa atenção simbólica."""
        from nsr_learn.attention import SymbolicAttention, AttentionContext
        
        attention = SymbolicAttention()
        
        items = ["cachorro", "corre", "parque", "rápido"]
        context = AttentionContext(query="cachorro")
        
        scores = attention.attend(items, context)
        
        assert len(scores) == len(items)
        assert all(0 <= s.total_score <= 1 for s in scores)
        # "cachorro" deve ter maior atenção por match direto
        assert scores[0].item == "cachorro" or any(s.item == "cachorro" for s in scores[:2])
    
    def test_attention_factors(self):
        """Testa fatores de atenção."""
        from nsr_learn.attention import SymbolicAttention, AttentionContext, AttentionFactor
        
        attention = SymbolicAttention()
        
        items = ["teste", "exemplo"]
        context = AttentionContext(query="teste")
        
        scores = attention.attend(items, context)
        
        for score in scores:
            assert AttentionFactor.RELEVANCE in score.factors
            assert AttentionFactor.SALIENCE in score.factors
    
    def test_multi_head_attention(self):
        """Testa atenção multi-head."""
        from nsr_learn.attention import MultiHeadSymbolicAttention, AttentionContext
        
        mha = MultiHeadSymbolicAttention()
        
        items = ["a", "b", "c"]
        context = AttentionContext(query="b")
        
        scores = mha.attend(items, context)
        
        assert len(scores) == len(items)


# ==================== TESTES DE GERAÇÃO ====================

class TestGenerator:
    """Testes para o módulo de geração."""
    
    def test_template_creation(self):
        """Testa criação de templates."""
        from nsr_learn.generator import Template
        
        template = Template(
            name="test",
            pattern="{A} is {B}",
            slots=["A", "B"],
        )
        
        result = template.instantiate({"A": "X", "B": "Y"})
        assert result == "X is Y"
    
    def test_text_generator(self):
        """Testa gerador de texto."""
        from nsr_learn.generator import create_default_generator
        
        gen = create_default_generator()
        
        result = gen.generate_from_template(
            "neutral_statement",
            bindings={
                "TOPIC": "Teste",
                "PREDICATE": "funciona",
                "DETAIL": "bem",
            },
            context_tags={"neutral"},
        )
        
        assert "Teste" in result
    
    def test_markov_composer(self):
        """Testa compositor Markov."""
        from nsr_learn.generator import MarkovComposer
        
        composer = MarkovComposer(order=2)
        
        sentences = [
            "o cachorro corre rápido",
            "o gato dorme sempre",
            "o pássaro voa alto",
        ]
        
        composer.learn(sentences)
        
        assert len(composer.transitions) > 0
        
        completion = composer.complete("o cachorro", max_words=3)
        assert len(completion.split()) >= 2


# ==================== TESTES DO MOTOR INTEGRADO ====================

class TestAdvancedEngine:
    """Testes para o motor integrado."""
    
    def test_engine_creation(self):
        """Testa criação do motor."""
        from nsr_learn.advanced_engine import AdvancedLearningEngine, AdvancedConfig
        
        config = AdvancedConfig(min_pattern_length=3)
        engine = AdvancedLearningEngine(config)
        
        assert engine.config.min_pattern_length == 3
        assert not engine._trained
    
    def test_training(self):
        """Testa treinamento."""
        from nsr_learn.advanced_engine import AdvancedLearningEngine
        
        engine = AdvancedLearningEngine()
        
        corpus = [
            "O cachorro corre no parque.",
            "O gato dorme no sofá.",
            "Pássaros voam no céu.",
        ]
        
        stats = engine.train(corpus)
        
        assert engine._trained
        assert stats["documents"] == 3
    
    def test_query(self):
        """Testa consulta."""
        from nsr_learn.advanced_engine import AdvancedLearningEngine
        
        engine = AdvancedLearningEngine()
        engine.train(["Cachorro é um animal que late."])
        
        answer, confidence, explanation = engine.query("O que é cachorro?")
        
        assert isinstance(answer, str)
        assert 0 <= confidence <= 1
    
    def test_learn_fact(self):
        """Testa aprendizado de fato."""
        from nsr_learn.advanced_engine import AdvancedLearningEngine
        
        engine = AdvancedLearningEngine()
        engine.learn_fact("python", "linguagem de programação")
        
        results = engine.get_similar("python")
        
        assert len(results) > 0
    
    def test_processing_modes(self):
        """Testa modos de processamento."""
        from nsr_learn.advanced_engine import AdvancedLearningEngine, ProcessingMode
        
        engine = AdvancedLearningEngine()
        engine.train(["Teste de processamento."])
        
        modes = [
            ProcessingMode.INFERENCE,
            ProcessingMode.ANALYSIS,
            ProcessingMode.DIALOGUE,
        ]
        
        for mode in modes:
            result = engine.process("teste", mode=mode)
            assert result.mode == mode
            assert result.output_text != ""
    
    def test_demo_engine(self):
        """Testa motor de demonstração."""
        from nsr_learn.advanced_engine import create_demo_engine
        
        engine = create_demo_engine()
        
        assert engine._trained
        status = engine.status()
        assert status["trained"] is True
        assert status["corpus_size"] > 0


# ==================== TESTES DE INTEGRAÇÃO ====================

class TestIntegration:
    """Testes de integração entre módulos."""
    
    def test_full_pipeline(self):
        """Testa pipeline completo."""
        from nsr_learn.advanced_engine import AdvancedLearningEngine
        
        engine = AdvancedLearningEngine()
        
        # Treina
        corpus = [
            "Matemática estuda números e formas.",
            "Física estuda matéria e energia.",
            "Química estuda substâncias e reações.",
        ]
        engine.train(corpus)
        
        # Aprende fatos
        engine.learn_fact("ciência", "conhecimento sistemático")
        
        # Aprende regras
        engine.learn_rule({"matemática"}, "ciência exata")
        
        # Consulta
        answer, conf, _ = engine.query("O que é matemática?")
        
        assert answer != ""
        assert conf > 0
    
    def test_determinism(self):
        """Testa que resultados são determinísticos."""
        from nsr_learn.advanced_engine import AdvancedLearningEngine
        
        corpus = ["Teste de determinismo."]
        
        engine1 = AdvancedLearningEngine()
        engine1.train(corpus)
        result1 = engine1.process("teste")
        
        engine2 = AdvancedLearningEngine()
        engine2.train(corpus)
        result2 = engine2.process("teste")
        
        # Deve produzir mesmos resultados
        assert result1.confidence == result2.confidence
    
    def test_no_neural_weights(self):
        """Verifica que não há pesos neurais."""
        from nsr_learn.advanced_engine import AdvancedLearningEngine
        
        engine = AdvancedLearningEngine()
        
        # Verifica que não tem atributos típicos de redes neurais
        assert not hasattr(engine, "weights")
        assert not hasattr(engine, "gradients")
        assert not hasattr(engine, "optimizer")
        assert not hasattr(engine, "backward")
        
        # Verifica componentes
        assert not hasattr(engine.compressor, "weights")
        assert not hasattr(engine.memory, "embeddings")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
