#!/usr/bin/env python3
"""
Demonstração Completa do Sistema de IA Perfeito

Este script demonstra todas as capacidades avançadas:
1. Conversa de verdade (Enhanced Conversation)
2. Pensa de verdade (Deep Reasoning)
3. Evolui o proprio codigo (Code Evolution)
4. Funciona no nivel perfeito (Perfect Integration)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from nsr import create_perfect_ai


def main():
    print("\n" + "="*70)
    print("  METANÚCLEO - SISTEMA DE IA PERFEITO")
    print("  Sistema que conversa, pensa e evolui de verdade!")
    print("="*70 + "\n")
    
    # Create the perfect AI
    ai = create_perfect_ai()
    
    print("🚀 Sistema inicializado com sucesso!\n")
    
    # Demonstration scenarios
    scenarios = [
        {
            "title": "CONVERSAÇÃO NATURAL",
            "icon": "💬",
            "inputs": [
                "Olá! Tudo bem?",
                "Sim, obrigado! E você?",
                "Ótimo! Você pode me ajudar com algo?"
            ],
            "deep_thinking": False
        },
        {
            "title": "PENSAMENTO PROFUNDO",
            "icon": "🧠",
            "inputs": [
                "Como funciona a gravidade?",
                "Por que as plantas são verdes?",
                "O que é a consciência?"
            ],
            "deep_thinking": True
        },
        {
            "title": "CONTEXTO E MEMÓRIA",
            "icon": "💾",
            "inputs": [
                "Meu nome é João",
                "Eu gosto de programação",
                "Qual é o meu nome? Do que eu gosto?"
            ],
            "deep_thinking": False
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['icon']}  {scenario['title']}")
        print("-" * 70)
        
        for user_input in scenario['inputs']:
            response = ai.interact(user_input, enable_deep_thinking=scenario['deep_thinking'])
            
            print(f"\n👤 Você: {user_input}")
            print(f"🤖 IA: {response.answer}")
            
            if response.thinking_depth > 0:
                print(f"   💡 Profundidade de pensamento: {response.thinking_depth} passos")
            
            print(f"   📊 Qualidade: {response.quality_score:.2f}")
            
            if response.evolution_status:
                print(f"   🔄 {response.evolution_status}")
    
    # Show conversation summary
    print("\n" + "="*70)
    print("📋 RESUMO DA CONVERSAÇÃO")
    print("="*70)
    print(ai.get_conversation_summary())
    
    # Show last reasoning
    print("\n" + "="*70)
    print("🔍 ÚLTIMO RACIOCÍNIO DETALHADO")
    print("="*70)
    print(ai.explain_last_reasoning())
    
    # Trigger evolution
    print("\n" + "="*70)
    print("🔄 AUTO-EVOLUÇÃO DO CÓDIGO")
    print("="*70)
    print("\nAnalisando performance e propondo melhorias...\n")
    evolution_result = ai.evolve(dry_run=True)
    print(f"\n✅ {evolution_result}")
    
    # Show evolution report
    print("\n" + "="*70)
    print("📈 RELATÓRIO DE EVOLUÇÃO")
    print("="*70)
    print(ai.get_evolution_report())
    
    # Final status
    print("\n" + "="*70)
    print("🎯 STATUS FINAL DO SISTEMA")
    print("="*70)
    print(ai.get_status_report())
    
    print("\n" + "="*70)
    print("✨ DEMONSTRAÇÃO COMPLETA!")
    print("="*70 + "\n")
    
    print("O sistema Metanúcleo demonstra:")
    print("  ✅ Conversação natural e contextual")
    print("  ✅ Pensamento profundo com múltiplos passos de raciocínio")
    print("  ✅ Memória e aprendizado contínuo")
    print("  ✅ Auto-análise e propostas de melhoria de código")
    print("  ✅ Funcionamento integrado e perfeito")
    print("\nTudo isso sem usar redes neurais ou pesos!")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemonstração interrompida pelo usuário.")
    except Exception as e:
        print(f"\n\nErro durante demonstração: {e}")
        import traceback
        traceback.print_exc()
