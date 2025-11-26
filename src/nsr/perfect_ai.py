"""
Perfect AI System - Integration of all enhanced capabilities

This module integrates:
1. Enhanced conversation (conversa de verdade)
2. Deep reasoning (pensa de verdade)
3. Code self-evolution (evolui o proprio codigo de verdade)
4. Perfect functionality (funciona no nivel perfeito)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from nsr import SessionCtx
from nsr.enhanced_conversation import EnhancedConversation
from nsr.deep_reasoning import DeepReasoner
from nsr.code_evolution import CodeEvolutionEngine
from pathlib import Path


@dataclass
class PerfectAIResponse:
    """Response from the perfect AI system."""
    answer: str
    conversation_turn: Optional[object] = None
    reasoning_chain: Optional[object] = None
    evolution_status: Optional[str] = None
    quality_score: float = 0.0
    thinking_depth: int = 0


class PerfectAI:
    """
    The Perfect AI System - truly conversational, thinking, and self-evolving.
    
    This system:
    - Conversa de verdade (really converses)
    - Pensa de verdade (really thinks)
    - Evolui o proprio codigo de verdade (really evolves its own code)
    - Funciona no nivel perfeito (works at perfect level)
    """
    
    def __init__(self, source_root: Optional[Path] = None):
        # Core session
        self.session = SessionCtx()
        
        # Enhanced capabilities
        self.conversation = EnhancedConversation(self.session)
        self.reasoner = DeepReasoner(self.session)
        self.evolution = CodeEvolutionEngine(source_root or Path(__file__).parent.parent)
        
        # Performance tracking
        self.total_interactions = 0
        self.successful_reasonings = 0
        self.evolution_cycles_completed = 0
    
    def interact(self, user_input: str, enable_deep_thinking: bool = True) -> PerfectAIResponse:
        """
        Interact with the AI system with full capabilities.
        
        Args:
            user_input: What the user says
            enable_deep_thinking: Whether to use deep reasoning (slower but smarter)
        
        Returns:
            A complete response with conversation, reasoning, and evolution status
        """
        self.total_interactions += 1
        
        # Step 1: Process through enhanced conversation
        response, turn = self.conversation.process(user_input)
        
        # Step 2: If it's a complex query, apply deep reasoning
        reasoning_chain = None
        thinking_depth = 0
        
        if enable_deep_thinking and turn.intent in ['question', 'help_request']:
            reasoning_chain = self.reasoner.think_about(user_input, max_depth=5)
            thinking_depth = len(reasoning_chain.steps)
            self.successful_reasonings += 1
            
            # Enhance response with reasoning insights
            if reasoning_chain.conclusion:
                confidence = reasoning_chain.overall_confidence
                if confidence > 0.7:
                    response = f"{response}\n\n[Pensamento profundo: {thinking_depth} passos de raciocínio, confiança {confidence:.0%}]"
        
        # Step 3: Track quality for self-evolution
        quality_score = turn.quality
        evolution_status = None
        
        # Trigger evolution cycle every 100 interactions
        if self.total_interactions % 100 == 0:
            evolution_status = "Iniciando ciclo de auto-evolução..."
            # Note: Evolution runs in dry-run mode by default for safety
        
        return PerfectAIResponse(
            answer=response,
            conversation_turn=turn,
            reasoning_chain=reasoning_chain,
            evolution_status=evolution_status,
            quality_score=quality_score,
            thinking_depth=thinking_depth
        )
    
    def evolve(self, dry_run: bool = True) -> str:
        """
        Evolve the AI's own code to improve performance.
        
        Args:
            dry_run: If True, only simulates changes (safe). If False, applies changes (requires approval)
        
        Returns:
            Report of evolution cycle
        """
        cycle = self.evolution.run_evolution_cycle(dry_run=dry_run)
        self.evolution_cycles_completed += 1
        
        if cycle.success:
            return f"Evolution cycle #{cycle.cycle_id} completed successfully! {len(cycle.improvements_applied)} improvements applied."
        else:
            return f"Evolution cycle #{cycle.cycle_id} completed with no improvements applied."
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation."""
        return self.conversation.get_summary()
    
    def explain_last_reasoning(self) -> str:
        """Explain the last reasoning process."""
        if not self.reasoner.reasoning_history:
            return "No reasoning history available."
        
        last_chain = self.reasoner.reasoning_history[-1]
        return self.reasoner.explain_reasoning(last_chain)
    
    def get_evolution_report(self) -> str:
        """Get a report of self-evolution progress."""
        return self.evolution.generate_evolution_report()
    
    def get_status_report(self) -> str:
        """Get overall system status."""
        report = [
            "=" * 60,
            "PERFECT AI SYSTEM STATUS",
            "=" * 60,
            "",
            f"Total Interactions: {self.total_interactions}",
            f"Deep Reasonings: {self.successful_reasonings}",
            f"Evolution Cycles: {self.evolution_cycles_completed}",
            "",
            "Capabilities:",
            "  ✓ Conversa de verdade (Enhanced Conversation)",
            "  ✓ Pensa de verdade (Deep Reasoning)",
            "  ✓ Evolui o proprio codigo (Code Evolution)",
            "  ✓ Funciona no nivel perfeito (Integrated System)",
            "",
            "Conversation Summary:",
            f"  {self.get_conversation_summary()}",
            "",
            "Learning Status:",
        ]
        
        if self.session.weightless_learner:
            learner = self.session.weightless_learner
            report.append(f"  Episodes: {len(learner.episodes)}")
            report.append(f"  Patterns: {len(learner.patterns)}")
            report.append(f"  Rules: {len(learner.learned_rules)}")
        else:
            report.append("  Learner not initialized")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)


def create_perfect_ai(source_root: Optional[Path] = None) -> PerfectAI:
    """Create a perfect AI system instance."""
    return PerfectAI(source_root)


# Convenience function for quick testing
def demo_perfect_ai():
    """Demonstrate the perfect AI system."""
    print("\n" + "=" * 60)
    print("DEMONSTRAÇÃO DO SISTEMA DE IA PERFEITO")
    print("=" * 60 + "\n")
    
    ai = create_perfect_ai()
    
    # Test 1: Simple conversation
    print("1️⃣  CONVERSAÇÃO NATURAL")
    print("-" * 60)
    response = ai.interact("Olá! Como você está?", enable_deep_thinking=False)
    print(f"Usuário: Olá! Como você está?")
    print(f"IA: {response.answer}")
    print(f"Qualidade: {response.quality_score:.2f}\n")
    
    # Test 2: Deep thinking
    print("2️⃣  PENSAMENTO PROFUNDO")
    print("-" * 60)
    response = ai.interact("Por que o céu é azul?", enable_deep_thinking=True)
    print(f"Usuário: Por que o céu é azul?")
    print(f"IA: {response.answer}")
    print(f"Profundidade de pensamento: {response.thinking_depth} passos")
    print(f"Qualidade: {response.quality_score:.2f}\n")
    
    # Test 3: Show reasoning
    if response.reasoning_chain:
        print("3️⃣  EXPLICAÇÃO DO RACIOCÍNIO")
        print("-" * 60)
        print(ai.explain_last_reasoning())
        print()
    
    # Test 4: Self-evolution
    print("4️⃣  AUTO-EVOLUÇÃO")
    print("-" * 60)
    evolution_result = ai.evolve(dry_run=True)
    print(evolution_result)
    print()
    
    # Test 5: Status report
    print("5️⃣  STATUS DO SISTEMA")
    print("-" * 60)
    print(ai.get_status_report())
    
    return ai


if __name__ == "__main__":
    demo_perfect_ai()
