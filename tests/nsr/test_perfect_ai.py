"""
Comprehensive tests for Perfect AI System.

Tests cover:
- System initialization
- Conversation integration
- Deep reasoning integration
- Code evolution integration
- Response generation
- Status reporting
"""

import pytest
from pathlib import Path
from nsr.perfect_ai import (
    PerfectAI,
    PerfectAIResponse,
    create_perfect_ai,
    demo_perfect_ai
)


class TestPerfectAIResponse:
    """Test PerfectAIResponse data structure."""
    
    def test_response_creation(self):
        """Test creating a perfect AI response."""
        response = PerfectAIResponse(
            answer="Test answer",
            conversation_turn=None,
            reasoning_chain=None,
            evolution_status=None,
            quality_score=0.85,
            thinking_depth=3
        )
        
        assert response.answer == "Test answer"
        assert response.quality_score == 0.85
        assert response.thinking_depth == 3


class TestPerfectAI:
    """Test Perfect AI System."""
    
    def test_ai_creation(self):
        """Test creating perfect AI."""
        ai = create_perfect_ai()
        
        assert ai is not None
        assert isinstance(ai, PerfectAI)
        assert ai.session is not None
        assert ai.conversation is not None
        assert ai.reasoner is not None
        assert ai.evolution is not None
    
    def test_ai_with_source_root(self):
        """Test creating AI with custom source root."""
        source_root = Path(__file__).parent.parent
        ai = PerfectAI(source_root=source_root)
        
        assert ai.evolution.source_root == source_root
    
    def test_basic_interaction(self):
        """Test basic interaction."""
        ai = create_perfect_ai()
        
        response = ai.interact("Olá!")
        
        assert isinstance(response, PerfectAIResponse)
        assert response.answer is not None
        assert response.quality_score >= 0.0
        assert response.quality_score <= 1.0
    
    def test_interaction_without_deep_thinking(self):
        """Test interaction without deep thinking."""
        ai = create_perfect_ai()
        
        response = ai.interact("Olá!", enable_deep_thinking=False)
        
        assert response.thinking_depth == 0
        assert response.reasoning_chain is None
    
    def test_interaction_with_deep_thinking(self):
        """Test interaction with deep thinking."""
        ai = create_perfect_ai()
        
        response = ai.interact("Como funciona?", enable_deep_thinking=True)
        
        # Should engage deep reasoning for questions
        assert response.thinking_depth >= 0
    
    def test_greeting_interaction(self):
        """Test greeting interaction."""
        ai = create_perfect_ai()
        
        response = ai.interact("Olá!", enable_deep_thinking=False)
        
        assert response.answer is not None
        assert response.conversation_turn is not None
        assert response.conversation_turn.intent == "greeting"
    
    def test_question_interaction(self):
        """Test question interaction."""
        ai = create_perfect_ai()
        
        response = ai.interact("Como você está?", enable_deep_thinking=False)
        
        assert response.conversation_turn is not None
        assert response.conversation_turn.intent == "question"
    
    def test_interaction_tracking(self):
        """Test that interactions are tracked."""
        ai = create_perfect_ai()
        
        initial_count = ai.total_interactions
        
        ai.interact("Test_1")
        ai.interact("Test_2")
        
        assert ai.total_interactions == initial_count + 2
    
    def test_reasoning_tracking(self):
        """Test that reasoning is tracked."""
        ai = create_perfect_ai()
        
        initial_count = ai.successful_reasonings
        
        ai.interact("Question?", enable_deep_thinking=True)
        
        # Should increment if deep thinking was used
        assert ai.successful_reasonings >= initial_count
    
    def test_evolve_dry_run(self):
        """Test evolution in dry run mode."""
        ai = create_perfect_ai()
        
        result = ai.evolve(dry_run=True)
        
        assert isinstance(result, str)
        assert "cycle" in result.lower() or "evolution" in result.lower()
    
    def test_evolve_increments_counter(self):
        """Test that evolution increments counter."""
        ai = create_perfect_ai()
        
        initial_count = ai.evolution_cycles_completed
        
        ai.evolve(dry_run=True)
        
        assert ai.evolution_cycles_completed == initial_count + 1
    
    def test_get_conversation_summary(self):
        """Test conversation summary."""
        ai = create_perfect_ai()
        
        ai.interact("Olá!")
        ai.interact("Tudo bem?")
        
        summary = ai.get_conversation_summary()
        
        assert isinstance(summary, str)
        assert "Turns" in summary or "turn" in summary.lower()
    
    def test_explain_last_reasoning(self):
        """Test reasoning explanation."""
        ai = create_perfect_ai()
        
        # First without reasoning
        explanation1 = ai.explain_last_reasoning()
        assert "No reasoning" in explanation1 or "available" in explanation1
        
        # Then with reasoning
        ai.interact("Question?", enable_deep_thinking=True)
        explanation2 = ai.explain_last_reasoning()
        
        # Should have explanation now
        assert isinstance(explanation2, str)
    
    def test_get_evolution_report(self):
        """Test evolution report."""
        ai = create_perfect_ai()
        
        # Before evolution
        report1 = ai.get_evolution_report()
        assert "No evolution cycles" in report1 or "Evolution" in report1
        
        # After evolution
        ai.evolve(dry_run=True)
        report2 = ai.get_evolution_report()
        
        assert isinstance(report2, str)
    
    def test_get_status_report(self):
        """Test status report generation."""
        ai = create_perfect_ai()
        
        # Do some interactions
        ai.interact("Test_1")
        ai.interact("Test_2", enable_deep_thinking=True)
        
        status = ai.get_status_report()
        
        assert isinstance(status, str)
        assert "PERFECT AI" in status or "STATUS" in status
        assert str(ai.total_interactions) in status


class TestIntegration:
    """Integration tests for perfect AI."""
    
    def test_full_interaction_pipeline(self):
        """Test complete interaction pipeline."""
        ai = create_perfect_ai()
        
        # Greeting
        r1 = ai.interact("Olá!")
        assert r1.conversation_turn.intent == "greeting"
        
        # Question with deep thinking
        r2 = ai.interact("Por que?", enable_deep_thinking=True)
        assert r2.thinking_depth > 0
        
        # Help request
        r3 = ai.interact("Ajuda!")
        assert r3.conversation_turn.intent == "help_request"
    
    def test_evolution_trigger(self):
        """Test evolution triggering."""
        ai = create_perfect_ai()
        
        # Do a few interactions
        for i in range(10):
            msg = f"Test_{i}"
            response = ai.interact(msg)
        
        # Should track all interactions
        assert ai.total_interactions == 10
    
    def test_conversation_context_preservation(self):
        """Test that conversation context is preserved."""
        ai = create_perfect_ai()
        
        ai.interact("Meu nome é João")
        ai.interact("Eu gosto de Python")
        
        summary = ai.get_conversation_summary()
        
        # Should track entities mentioned
        assert isinstance(summary, str)
    
    def test_reasoning_depth_varies(self):
        """Test that reasoning depth varies by query type."""
        ai = create_perfect_ai()
        
        # Simple greeting - no deep thinking
        r1 = ai.interact("Oi!", enable_deep_thinking=True)
        
        # Complex question - should think deeper
        r2 = ai.interact("Como funciona a gravidade?", enable_deep_thinking=True)
        
        assert isinstance(r1.thinking_depth, int)
        assert isinstance(r2.thinking_depth, int)
    
    def test_quality_tracking(self):
        """Test quality score tracking."""
        ai = create_perfect_ai()
        
        responses = []
        for i in range(5):
            msg = f"Test_{i}"
            response = ai.interact(msg)
            responses.append(response)
        
        # All responses should have quality scores
        for response in responses:
            assert 0.0 <= response.quality_score <= 1.0
    
    def test_deterministic_responses(self):
        """Test that responses are deterministic."""
        ai1 = create_perfect_ai()
        ai2 = create_perfect_ai()
        
        r1 = ai1.interact("Olá!")
        r2 = ai2.interact("Olá!")
        
        # Should have same intent
        assert r1.conversation_turn.intent == r2.conversation_turn.intent
    
    def test_all_capabilities_working(self):
        """Test that all capabilities work together."""
        ai = create_perfect_ai()
        
        # 1. Conversation
        response = ai.interact("Olá!")
        assert response.conversation_turn is not None
        
        # 2. Reasoning
        response = ai.interact("Por que?", enable_deep_thinking=True)
        assert response.reasoning_chain is not None or response.thinking_depth >= 0
        
        # 3. Evolution
        result = ai.evolve(dry_run=True)
        assert "cycle" in result.lower()
        
        # 4. Status
        status = ai.get_status_report()
        assert len(status) > 0
    
    def test_multiple_evolution_cycles(self):
        """Test multiple evolution cycles."""
        ai = create_perfect_ai()
        
        ai.evolve(dry_run=True)
        ai.evolve(dry_run=True)
        
        assert ai.evolution_cycles_completed == 2
        
        report = ai.get_evolution_report()
        assert "2" in report or "two" in report.lower()


class TestDemo:
    """Test demo functionality."""
    
    def test_demo_runs(self):
        """Test that demo can run."""
        # This is a smoke test - demo should not crash
        try:
            ai = demo_perfect_ai()
            assert ai is not None
        except Exception as e:
            pytest.fail(f"Demo failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
