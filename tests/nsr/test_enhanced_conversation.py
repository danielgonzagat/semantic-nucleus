"""
Comprehensive tests for Enhanced Conversation System.

Tests cover:
- Context tracking across turns
- Topic identification
- Intent detection
- Entity extraction
- Response enhancement
- Conversation summaries
"""

import pytest
from nsr.enhanced_conversation import (
    EnhancedConversation,
    ConversationTurn,
    ConversationContext,
    create_conversation
)
from nsr import SessionCtx
from liu import struct, entity, text


class TestConversationTurn:
    """Test ConversationTurn data structure."""
    
    def test_turn_creation(self):
        """Test creating a conversation turn."""
        turn = ConversationTurn(
            user_input="Olá!",
            system_response="oi",
            topic="greeting",
            intent="greeting",
            quality=0.85,
            context_nodes=[]
        )
        
        assert turn.user_input == "Olá!"
        assert turn.system_response == "oi"
        assert turn.topic == "greeting"
        assert turn.intent == "greeting"
        assert turn.quality == 0.85


class TestConversationContext:
    """Test ConversationContext management."""
    
    def test_context_creation(self):
        """Test creating conversation context."""
        session = SessionCtx()
        context = ConversationContext(session=session)
        
        assert len(context.turns) == 0
        assert context.current_topic is None
        assert len(context.active_entities) == 0
    
    def test_intent_extraction_question(self):
        """Test extracting question intent."""
        session = SessionCtx()
        context = ConversationContext(session=session)
        
        intent = context._extract_intent("Como funciona?")
        assert intent == "question"
    
    def test_intent_extraction_greeting(self):
        """Test extracting greeting intent."""
        session = SessionCtx()
        context = ConversationContext(session=session)
        
        intent = context._extract_intent("Olá!")
        assert intent == "greeting"
    
    def test_intent_extraction_help(self):
        """Test extracting help request intent."""
        session = SessionCtx()
        context = ConversationContext(session=session)
        
        intent = context._extract_intent("Preciso de ajuda")
        assert intent == "help_request"
    
    def test_intent_extraction_statement(self):
        """Test extracting statement intent."""
        session = SessionCtx()
        context = ConversationContext(session=session)
        
        intent = context._extract_intent("O carro é azul")
        assert intent == "statement"
    
    def test_topic_extraction(self):
        """Test topic extraction from conversation."""
        session = SessionCtx()
        context = ConversationContext(session=session)
        
        from nsr import run_text_full
        outcome = run_text_full("Preciso de ajuda", session)
        
        topic = context._extract_topic("Preciso de ajuda", outcome)
        assert topic == "assistance"
    
    def test_conversation_summary_empty(self):
        """Test summary with no conversation."""
        session = SessionCtx()
        context = ConversationContext(session=session)
        
        summary = context.get_conversation_summary()
        assert "No conversation yet" in summary
    
    def test_turn_tracking(self):
        """Test that turns are tracked correctly."""
        session = SessionCtx()
        context = ConversationContext(session=session)
        
        from nsr import run_text_full
        outcome = run_text_full("Olá", session)
        
        turn = context.add_turn("Olá", outcome)
        
        assert len(context.turns) == 1
        assert turn.user_input == "Olá"
        assert turn.intent == "greeting"


class TestEnhancedConversation:
    """Test Enhanced Conversation system."""
    
    def test_conversation_creation(self):
        """Test creating an enhanced conversation."""
        conv = create_conversation()
        
        assert conv is not None
        assert isinstance(conv, EnhancedConversation)
        assert len(conv.context.turns) == 0
    
    def test_basic_interaction(self):
        """Test basic conversation interaction."""
        conv = create_conversation()
        
        response, turn = conv.process("Olá!")
        
        assert response is not None
        assert turn.user_input == "Olá!"
        assert turn.intent == "greeting"
        assert turn.quality > 0.0
    
    def test_context_preservation(self):
        """Test that context is preserved across turns."""
        conv = create_conversation()
        
        response1, turn1 = conv.process("Olá!")
        response2, turn2 = conv.process("Como vai?")
        
        assert len(conv.context.turns) == 2
        assert turn1.user_input == "Olá!"
        assert turn2.user_input == "Como vai?"
    
    def test_greeting_enhancement(self):
        """Test that greetings are enhanced."""
        conv = create_conversation()
        
        response, turn = conv.process("Olá!")
        
        # First greeting should be enhanced with offer to help
        assert "ajudar" in response.lower() or "help" in response.lower()
    
    def test_help_request_enhancement(self):
        """Test that help requests are enhanced."""
        conv = create_conversation()
        
        response, turn = conv.process("Preciso de ajuda")
        
        # Help request should get clarifying response
        assert len(response) > 0
    
    def test_summary_generation(self):
        """Test conversation summary generation."""
        conv = create_conversation()
        
        conv.process("Olá!")
        conv.process("Como vai?")
        conv.process("Tudo bem?")
        
        summary = conv.get_summary()
        
        assert "Turns: 3" in summary or "No clear topics" in summary
    
    def test_multi_turn_conversation(self):
        """Test multiple conversation turns."""
        conv = create_conversation()
        
        # Simulate a conversation
        inputs = [
            "Olá!",
            "Tudo bem?",
            "Você pode ajudar?",
            "Obrigado!"
        ]
        
        for user_input in inputs:
            response, turn = conv.process(user_input)
            assert response is not None
            assert turn is not None
        
        assert len(conv.context.turns) == 4
    
    def test_quality_tracking(self):
        """Test that quality is tracked."""
        conv = create_conversation()
        
        response, turn = conv.process("Olá!")
        
        assert turn.quality >= 0.0
        assert turn.quality <= 1.0


class TestIntegration:
    """Integration tests for enhanced conversation."""
    
    def test_full_conversation_flow(self):
        """Test a full conversation flow."""
        conv = create_conversation()
        
        # Greeting
        r1, t1 = conv.process("Olá!")
        assert t1.intent == "greeting"
        
        # Question
        r2, t2 = conv.process("Como você está?")
        assert t2.intent == "question"
        
        # Statement
        r3, t3 = conv.process("Estou bem")
        assert t3.intent == "statement"
        
        # Verify all turns recorded
        assert len(conv.context.turns) == 3
    
    def test_deterministic_behavior(self):
        """Test that conversation is deterministic."""
        conv1 = create_conversation()
        conv2 = create_conversation()
        
        # Same input should give same intent
        r1, t1 = conv1.process("Olá!")
        r2, t2 = conv2.process("Olá!")
        
        assert t1.intent == t2.intent
        assert t1.quality == t2.quality


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
