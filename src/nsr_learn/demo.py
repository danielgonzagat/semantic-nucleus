#!/usr/bin/env python3
"""
Demonstração do NSR-Learn: Aprendizado Simbólico Sem Pesos Neurais.

Este script demonstra como o sistema aprende de dados e responde queries
usando apenas:
- Compressão MDL
- Grafos de co-ocorrência
- Indução de regras
- Memória associativa

ZERO redes neurais. ZERO pesos. ZERO gradientes.
"""

from nsr_learn import LearningEngine, LearningConfig


def main():
    print("=" * 70)
    print("NSR-Learn: Aprendizado de Máquina Sem Pesos Neurais")
    print("=" * 70)
    print()
    
    # Configura o motor
    config = LearningConfig(
        min_pattern_freq=2,
        cooc_window_size=5,
        min_rule_confidence=0.3,
    )
    
    engine = LearningEngine(config)
    
    # ==========================================================================
    # FASE 1: APRENDIZADO (equivalente a "treinamento")
    # ==========================================================================
    print("📚 FASE 1: Aprendizado")
    print("-" * 40)
    
    corpus = [
        "Python é uma linguagem de programação popular.",
        "Python é usado para ciência de dados e machine learning.",
        "JavaScript é usado para desenvolvimento web.",
        "Java é uma linguagem orientada a objetos.",
        "Ciência de dados usa estatística e programação.",
        "Machine learning é um subcampo da inteligência artificial.",
        "Inteligência artificial estuda sistemas inteligentes.",
        "Programação envolve escrever código em linguagens.",
        "Python e JavaScript são linguagens interpretadas.",
        "Dados são processados por algoritmos.",
    ]
    
    result = engine.learn(corpus)
    
    print(f"✓ Documentos processados: {result['documents']}")
    print(f"✓ Tokens vistos: {result['tokens']}")
    print(f"✓ Vocabulário: {result['vocabulary_size']} palavras únicas")
    print(f"✓ Padrões encontrados: {result['patterns_found']}")
    print(f"✓ Taxa de compressão: {result['compression_ratio']:.2%}")
    print(f"✓ Regras induzidas: {result['rules_induced']}")
    print(f"✓ Traços de memória: {result['memory_traces']}")
    print()
    
    # ==========================================================================
    # FASE 2: QUERIES (equivalente a "inferência")
    # ==========================================================================
    print("🔍 FASE 2: Consultas")
    print("-" * 40)
    
    queries = [
        "Python programação",
        "ciência dados",
        "inteligência artificial",
        "JavaScript web",
    ]
    
    for query in queries:
        result = engine.query(query)
        
        print(f"\n📝 Query: '{query}'")
        print(f"   Resposta: {result.response[:100]}...")
        print(f"   Confiança: {result.confidence:.2%}")
        print(f"   Memórias recuperadas: {len(result.retrieved_memories)}")
        print(f"   Regras aplicadas: {len(result.applied_rules)}")
        print(f"   Raciocínio:")
        for step in result.reasoning[:3]:
            print(f"      → {step}")
    
    print()
    
    # ==========================================================================
    # FASE 3: APRENDIZADO DE PARES (equivalente a "fine-tuning")
    # ==========================================================================
    print("🎯 FASE 3: Aprendizado de Pares Pergunta-Resposta")
    print("-" * 40)
    
    pairs = [
        ("Qual a capital do Brasil?", "A capital do Brasil é Brasília."),
        ("Quem inventou Python?", "Python foi criado por Guido van Rossum."),
        ("O que é machine learning?", "Machine learning é aprendizado de máquina."),
    ]
    
    for question, answer in pairs:
        engine.learn_pair(question, answer)
        print(f"✓ Aprendeu: '{question[:30]}...' → '{answer[:30]}...'")
    
    print()
    
    # Testa recuperação
    test_result = engine.query("capital Brasil")
    print(f"📝 Query de teste: 'capital Brasil'")
    print(f"   Resposta: {test_result.response}")
    print(f"   Confiança: {test_result.confidence:.2%}")
    print()
    
    # ==========================================================================
    # FASE 4: SIMILARIDADE
    # ==========================================================================
    print("📊 FASE 4: Cálculo de Similaridade (sem embeddings!)")
    print("-" * 40)
    
    pairs_to_compare = [
        ("Python é bom para dados", "Python é usado em ciência de dados"),
        ("Python é bom para dados", "JavaScript é usado para web"),
        ("gato dorme sofá", "cachorro dorme chão"),
    ]
    
    for text1, text2 in pairs_to_compare:
        sim = engine.similarity(text1, text2)
        print(f"   sim('{text1[:25]}...', '{text2[:25]}...') = {sim:.2%}")
    
    print()
    
    # ==========================================================================
    # ESTATÍSTICAS FINAIS
    # ==========================================================================
    print("📈 Estatísticas do Sistema")
    print("-" * 40)
    
    stats = engine.stats()
    print(f"   Documentos vistos: {stats['documents_seen']}")
    print(f"   Tokens processados: {stats['tokens_seen']}")
    print(f"   Vocabulário: {stats['vocabulary_size']}")
    print(f"   Regras: {stats['rules_count']}")
    print(f"   Memórias: {stats['memory_traces']}")
    print(f"   Digest do estado: {stats['state_digest']}")
    print()
    
    # ==========================================================================
    # O QUE NÃO USAMOS
    # ==========================================================================
    print("🚫 O que este sistema NÃO usa:")
    print("-" * 40)
    print("   ✗ Redes neurais")
    print("   ✗ Matrizes de pesos")
    print("   ✗ Backpropagation")
    print("   ✗ Gradientes")
    print("   ✗ GPUs")
    print("   ✗ Embeddings densos")
    print("   ✗ Attention mechanisms")
    print("   ✗ Transformers")
    print()
    
    print("✅ O que este sistema USA:")
    print("-" * 40)
    print("   ✓ Compressão (MDL)")
    print("   ✓ Contagens discretas")
    print("   ✓ Grafos de co-ocorrência")
    print("   ✓ Regras simbólicas explícitas")
    print("   ✓ Memória associativa indexada")
    print("   ✓ Raciocínio interpretável")
    print()
    
    print("=" * 70)
    print("Demonstração concluída!")
    print("=" * 70)


if __name__ == "__main__":
    main()
