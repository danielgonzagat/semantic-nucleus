#!/usr/bin/env python3
"""
Demonstração Avançada do NSR-Learn.

Este script demonstra todas as capacidades do sistema de
aprendizado simbólico sem pesos neurais.

Execute com: python -m nsr_learn.advanced_demo
"""

from __future__ import annotations

import sys
import time

# Imports dos módulos
from .advanced_engine import AdvancedLearningEngine, AdvancedConfig, ProcessingMode
from .analogy import AnalogyEngine, Structure, SOLAR_SYSTEM, ATOM
from .reasoning import ChainOfThoughtEngine, KnowledgeBase, create_example_kb
from .abstraction import Taxonomy, create_default_taxonomy
from .attention import SymbolicAttention, AttentionContext
from .generator import TextGenerator, create_default_generator


def print_section(title: str) -> None:
    """Imprime cabeçalho de seção."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def demo_analogy():
    """Demonstra raciocínio por analogia."""
    print_section("1. RACIOCÍNIO POR ANALOGIA")
    
    print("A analogia permite transferir conhecimento entre domínios diferentes.")
    print("Exemplo clássico: Átomo ≈ Sistema Solar\n")
    
    engine = AnalogyEngine()
    
    # Registra estruturas
    engine.register_structure(SOLAR_SYSTEM)
    engine.register_structure(ATOM)
    
    print(f"Estrutura FONTE: {SOLAR_SYSTEM}")
    print(f"Estrutura ALVO:  {ATOM}")
    print()
    
    # Encontra analogia
    analogy = engine.find_analogy(SOLAR_SYSTEM, ATOM)
    
    if analogy:
        print("Analogia encontrada!")
        print(analogy.explain())
    else:
        print("Nenhuma analogia encontrada.")
    
    # Demonstra similaridade estrutural
    print("\n--- Similaridade Estrutural ---")
    
    # Cria novas estruturas para comparar
    professor = Structure.from_facts("escola", [
        ("ensina", "professor", "aluno"),
        ("avalia", "professor", "aluno"),
        ("superior", "professor", "aluno"),
    ])
    
    medico = Structure.from_facts("hospital", [
        ("trata", "medico", "paciente"),
        ("diagnostica", "medico", "paciente"),
        ("superior", "medico", "paciente"),
    ])
    
    engine.register_structure(professor)
    engine.register_structure(medico)
    
    analogy2 = engine.find_analogy(professor, medico)
    if analogy2:
        print(f"\nAnalogia entre escola e hospital:")
        print(f"  Professor → Médico")
        print(f"  Aluno → Paciente")
        print(f"  Confiança: {analogy2.confidence:.2%}")


def demo_reasoning():
    """Demonstra cadeia de raciocínio."""
    print_section("2. CADEIA DE RACIOCÍNIO (Chain of Thought)")
    
    print("Cada passo de raciocínio é explícito e auditável.")
    print("Diferente de LLMs onde o raciocínio está implícito nos pesos.\n")
    
    kb = create_example_kb()
    
    # Adiciona mais conhecimento
    kb.add_fact("biologia", "mamíferos são animais de sangue quente")
    kb.add_fact("biologia", "cachorros são mamíferos")
    kb.add_fact("biologia", "animais de sangue quente regulam temperatura")
    kb.add_rule("mamífero", "sangue quente", "herança_mamífero")
    kb.add_rule("cachorro", "mamífero", "classificação")
    
    engine = ChainOfThoughtEngine(kb)
    
    queries = [
        "Por que cachorros regulam temperatura corporal?",
        "Como funciona a soma de números pares?",
    ]
    
    for query in queries:
        print(f"Query: '{query}'")
        print("-" * 40)
        
        chain = engine.reason(query)
        
        for i, step in enumerate(chain.steps, 1):
            print(f"  {i}. [{step.step_type.name}] {step.content[:60]}...")
        
        print(f"\n  Conclusão: {chain.conclusion}")
        print(f"  Confiança: {chain.total_confidence:.2%}")
        print()


def demo_abstraction():
    """Demonstra abstração hierárquica."""
    print_section("3. ABSTRAÇÃO HIERÁRQUICA")
    
    print("Organização de conceitos em níveis de abstração.")
    print("Herança de propriedades via hierarquia.\n")
    
    taxonomy = create_default_taxonomy()
    
    # Mostra hierarquia
    print("Hierarquia de conceitos:")
    print("  ENTIDADE")
    print("    └── SER_VIVO")
    print("        ├── ANIMAL")
    print("        │   ├── MAMIFERO")
    print("        │   │   ├── CACHORRO")
    print("        │   │   └── GATO")
    print("        │   └── AVE")
    print("        └── PLANTA")
    print()
    
    # Demonstra herança
    print("Propriedades herdadas por CACHORRO:")
    props = taxonomy.get_inherited_properties("CACHORRO")
    for prop in sorted(props):
        print(f"  - {prop}")
    print()
    
    # Demonstra IS-A
    tests = [
        ("CACHORRO", "MAMIFERO"),
        ("CACHORRO", "ANIMAL"),
        ("CACHORRO", "SER_VIVO"),
        ("CACHORRO", "PLANTA"),
    ]
    
    print("Testes de IS-A:")
    for specific, general in tests:
        result = taxonomy.is_a(specific, general)
        symbol = "✓" if result else "✗"
        print(f"  {specific} IS-A {general}? {symbol}")
    print()
    
    # Demonstra LCA
    print("Ancestral Comum Mais Baixo (LCA):")
    pairs = [
        ("CACHORRO", "GATO"),
        ("CACHORRO", "AVE"),
        ("CACHORRO", "PLANTA"),
    ]
    
    for c1, c2 in pairs:
        lca = taxonomy.lowest_common_ancestor(c1, c2)
        dist = taxonomy.semantic_distance(c1, c2)
        print(f"  LCA({c1}, {c2}) = {lca} (distância: {dist})")


def demo_attention():
    """Demonstra atenção simbólica."""
    print_section("4. ATENÇÃO SIMBÓLICA")
    
    print("Foco dinâmico baseado em relevância explícita.")
    print("Sem pesos - usa saliência, relevância, surpresa, etc.\n")
    
    attention = SymbolicAttention()
    
    # Treina com corpus
    corpus = [
        "O cachorro corre no parque".split(),
        "O gato dorme no sofá".split(),
        "Inteligência artificial aprende padrões".split(),
        "Redes neurais usam pesos".split(),
        "Sistemas simbólicos usam regras".split(),
    ]
    attention.salience.learn_corpus(corpus)
    attention.relevance.learn_cooccurrence(corpus)
    attention.surprise.learn_distribution(corpus)
    
    # Demonstra atenção
    text = "O sistema simbólico aprende regras sem usar pesos neurais"
    tokens = text.split()
    
    context = AttentionContext(query="como aprender sem pesos?")
    
    print(f"Texto: '{text}'")
    print(f"Query: '{context.query}'")
    print()
    
    scores = attention.attend(tokens, context, top_k=5)
    
    print("Top 5 tokens por atenção:")
    for i, score in enumerate(scores, 1):
        top_factors = score.top_factors(2)
        factors_str = ", ".join(f"{f.name}:{v:.2f}" for f, v in top_factors)
        print(f"  {i}. '{score.item}' (score: {score.total_score:.3f}) - {factors_str}")


def demo_generator():
    """Demonstra geração de texto."""
    print_section("5. GERAÇÃO DE TEXTO")
    
    print("Geração via templates, fragmentos e composição Markov.")
    print("Determinístico e auditável.\n")
    
    generator = create_default_generator()
    
    # Adiciona mais templates
    from .generator import Template, TextFragment, FragmentType
    
    generator.add_template(Template(
        name="definicao",
        pattern="{TERMO} é definido como {DEFINICAO}. {EXEMPLO}",
        slots=["TERMO", "DEFINICAO", "EXEMPLO"],
        required_tags={"definir"},
    ))
    
    # Gera textos
    print("Gerando texto via template 'explanation':")
    result = generator.generate_from_template(
        "explanation",
        bindings={
            "TOPIC": "Inteligência Artificial Simbólica",
            "DEFINITION": "uma abordagem de IA baseada em regras explícitas",
            "ELABORATION": "Diferente de redes neurais, usa representações simbólicas.",
        },
        context_tags={"explain"},
    )
    print(f"  {result}")
    print()
    
    # Demonstra Markov completion
    print("Geração Markov (completando prefixo):")
    prefix = "O sistema gera"
    completion = generator.composer.complete(prefix, max_words=8)
    print(f"  Prefixo: '{prefix}'")
    print(f"  Completo: '{completion}'")


def demo_integrated():
    """Demonstra motor integrado."""
    print_section("6. MOTOR INTEGRADO AVANÇADO")
    
    print("Integração de todos os componentes em um sistema coeso.\n")
    
    # Cria motor
    config = AdvancedConfig(
        min_pattern_length=2,
        min_rule_support=1,
        min_rule_confidence=0.3,
    )
    engine = AdvancedLearningEngine(config)
    
    # Corpus expandido
    corpus = [
        "O cachorro é um mamífero que late e corre no parque.",
        "O gato é um mamífero que mia e dorme no sofá.",
        "Pássaros são aves que voam pelo céu.",
        "Mamíferos são animais de sangue quente.",
        "Animais de sangue quente regulam a temperatura corporal.",
        "Inteligência artificial pode ser simbólica ou neural.",
        "Sistemas simbólicos usam regras explícitas e são interpretáveis.",
        "Redes neurais usam pesos e aprendem por backpropagation.",
        "Compressão de dados revela padrões escondidos.",
        "Analogias transferem conhecimento entre domínios diferentes.",
        "Raciocínio lógico deriva conclusões de premissas.",
        "Memória associativa recupera informações por similaridade.",
    ]
    
    print("Treinando o motor...")
    stats = engine.train(corpus, verbose=True)
    print()
    
    # Demonstra query
    print("--- Consulta ---")
    queries = [
        "O que é um cachorro?",
        "Como funcionam sistemas simbólicos?",
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        answer, confidence, explanation = engine.query(query)
        print(f"Resposta: {answer}")
        print(f"Confiança: {confidence:.2%}")
    
    # Demonstra análise
    print("\n--- Análise ---")
    text = "Redes neurais aprendem padrões usando gradientes."
    analysis = engine.analyze(text)
    print(f"Texto: '{text}'")
    print(f"Análise:\n{analysis}")
    
    # Status final
    print("\n--- Status do Motor ---")
    status = engine.status()
    for key, value in status.items():
        print(f"  {key}: {value}")


def demo_comparison():
    """Compara abordagem simbólica vs neural."""
    print_section("7. COMPARAÇÃO: SIMBÓLICO vs NEURAL")
    
    print("""
┌─────────────────────────────────────────────────────────────────────────┐
│                    COMPARAÇÃO DE ABORDAGENS                              │
├─────────────────────────┬─────────────────────┬─────────────────────────┤
│ Aspecto                 │ Neural (LLMs)       │ Simbólico (NSR-Learn)   │
├─────────────────────────┼─────────────────────┼─────────────────────────┤
│ Representação           │ Embeddings (floats) │ Símbolos discretos      │
│ Aprendizado             │ Backpropagation     │ Compressão MDL          │
│ Memória                 │ Implícita (pesos)   │ Explícita (associativa) │
│ Raciocínio              │ Implícito           │ Chain of Thought expl.  │
│ Atenção                 │ Softmax(QK^T)       │ Relevância simbólica    │
│ Geração                 │ Autoregressive      │ Template + Composição   │
│ Interpretabilidade      │ Baixa               │ Alta                    │
│ Auditabilidade          │ Difícil             │ Total                   │
│ Alucinações             │ Possíveis           │ Impossíveis*            │
│ Treinamento             │ GPU + dados massivos│ CPU + dados modestos    │
└─────────────────────────┴─────────────────────┴─────────────────────────┘

* O sistema só produz o que está explicitamente nas regras/memória.
""")
    
    print("O que NÃO usamos:")
    print("  ✗ Redes neurais")
    print("  ✗ Pesos contínuos")
    print("  ✗ Backpropagation")
    print("  ✗ Gradientes")
    print("  ✗ GPUs")
    print("  ✗ Embeddings densos")
    print()
    
    print("O que USAMOS:")
    print("  ✓ Compressão MDL (Kolmogorov)")
    print("  ✓ Grafos discretos de co-ocorrência")
    print("  ✓ Regras simbólicas explícitas")
    print("  ✓ Memória associativa discreta")
    print("  ✓ Analogia estrutural (Gentner)")
    print("  ✓ Taxonomias hierárquicas")
    print("  ✓ Atenção por relevância explícita")
    print("  ✓ Geração por templates")


def main():
    """Executa todas as demonstrações."""
    print("\n" + "█" * 60)
    print("█" + " " * 58 + "█")
    print("█    NSR-LEARN: IA Simbólica Sem Pesos Neurais    █")
    print("█" + " " * 58 + "█")
    print("█" * 60)
    
    start = time.time()
    
    try:
        demo_analogy()
        demo_reasoning()
        demo_abstraction()
        demo_attention()
        demo_generator()
        demo_integrated()
        demo_comparison()
        
    except Exception as e:
        print(f"\n[ERRO] {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    elapsed = time.time() - start
    
    print_section("DEMONSTRAÇÃO CONCLUÍDA")
    print(f"Tempo total: {elapsed:.2f} segundos")
    print()
    print("O sistema NSR-Learn demonstra que é possível implementar")
    print("capacidades similares a LLMs usando apenas mecanismos simbólicos:")
    print()
    print("  • Aprendizado via compressão (MDL)")
    print("  • Semântica via grafos discretos")
    print("  • Generalização via abstração hierárquica")
    print("  • Transferência via analogia estrutural")
    print("  • Raciocínio via Chain of Thought explícito")
    print("  • Foco via atenção simbólica")
    print("  • Geração via composição de templates")
    print()
    print("Tudo isso é 100% interpretável e auditável.")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
