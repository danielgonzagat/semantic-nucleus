"""
Enhanced Conversation System for Metanucleus - True Conversational AI

This module enhances the conversation capabilities to:
1. Maintain better context across turns
2. Understand conversation flow and topics
3. Generate more natural responses
4. Track conversation history meaningfully
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from collections import deque

from liu import Node, struct, text, entity, relation
from nsr import SessionCtx, run_text_full, RunOutcome


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    user_input: str
    system_response: str
    topic: Optional[str] = None
    intent: Optional[str] = None
    quality: float = 0.0
    context_nodes: List[Node] = field(default_factory=list)


@dataclass
class ConversationContext:
    """Enhanced conversation context that tracks dialogue flow."""
    session: SessionCtx
    turns: deque = field(default_factory=lambda: deque(maxlen=20))
    current_topic: Optional[str] = None
    active_entities: set = field(default_factory=set)
    conversation_goals: List[str] = field(default_factory=list)
    
    def add_turn(self, user_input: str, outcome: RunOutcome) -> ConversationTurn:
        """Add a turn and extract context."""
        # Extract topic from the conversation
        topic = self._extract_topic(user_input, outcome)
        
        # Extract entities mentioned
        entities = self._extract_entities(outcome)
        self.active_entities.update(entities)
        
        # Create turn
        turn = ConversationTurn(
            user_input=user_input,
            system_response=outcome.answer,
            topic=topic,
            intent=self._extract_intent(user_input),
            quality=outcome.quality,
            context_nodes=list(outcome.isr.context) if outcome.isr else []
        )
        
        self.turns.append(turn)
        
        # Update current topic
        if topic:
            self.current_topic = topic
            
        return turn
    
    def _extract_topic(self, user_input: str, outcome: RunOutcome) -> Optional[str]:
        """Extract the main topic from the conversation."""
        # Simple heuristic: look for nouns in the input
        words = user_input.lower().split()
        
        # Common conversation topics
        topic_keywords = {
            'ajuda': 'assistance',
            'help': 'assistance',
            'conversa': 'conversation',
            'falar': 'conversation',
            'talk': 'conversation',
            'explicar': 'explanation',
            'explain': 'explanation',
            'aprender': 'learning',
            'learn': 'learning',
        }
        
        for word in words:
            if word in topic_keywords:
                return topic_keywords[word]
        
        # Check if continuing previous topic
        if len(self.turns) > 0 and self.current_topic:
            return self.current_topic
            
        return None
    
    def _extract_intent(self, user_input: str) -> Optional[str]:
        """Extract user intent from input."""
        lower_input = user_input.lower()
        
        if any(q in lower_input for q in ['?', 'como', 'o que', 'quando', 'onde', 'por que', 'quem']):
            return 'question'
        elif any(g in lower_input for g in ['olá', 'oi', 'hello', 'hi', 'bom dia']):
            return 'greeting'
        elif any(t in lower_input for t in ['obrigad', 'valeu', 'thanks', 'thank you']):
            return 'gratitude'
        elif any(h in lower_input for h in ['ajuda', 'help', 'socorro']):
            return 'help_request'
        else:
            return 'statement'
    
    def _extract_entities(self, outcome: RunOutcome) -> set:
        """Extract entities mentioned in the outcome."""
        entities = set()
        
        if not outcome.isr:
            return entities
        
        # Extract from relations
        for rel in outcome.isr.relations:
            if rel.kind.name == 'REL' and len(rel.args) >= 2:
                for arg in rel.args:
                    if arg.kind.name == 'ENTITY' and arg.label:
                        entities.add(arg.label)
        
        return entities
    
    def get_conversation_summary(self) -> str:
        """Generate a summary of the conversation so far."""
        if not self.turns:
            return "No conversation yet."
        
        recent_topics = []
        for turn in list(self.turns)[-5:]:
            if turn.topic:
                recent_topics.append(turn.topic)
        
        topic_str = f"Topics: {', '.join(set(recent_topics))}" if recent_topics else "No clear topics yet"
        entity_str = f"Entities: {', '.join(list(self.active_entities)[:10])}" if self.active_entities else "No entities tracked"
        
        return f"{topic_str}. {entity_str}. Turns: {len(self.turns)}"
    
    def get_context_prompt(self) -> str:
        """Generate a context prompt for better responses."""
        if not self.turns:
            return ""
        
        # Get last few turns for context
        recent = list(self.turns)[-3:]
        context_parts = []
        
        for turn in recent:
            context_parts.append(f"User: {turn.user_input[:50]}")
            context_parts.append(f"System: {turn.system_response[:50]}")
        
        return " | ".join(context_parts)


class EnhancedConversation:
    """Enhanced conversation engine with better dialogue management."""
    
    def __init__(self, session: Optional[SessionCtx] = None):
        self.session = session or SessionCtx()
        self.context = ConversationContext(session=self.session)
    
    def process(self, user_input: str) -> Tuple[str, ConversationTurn]:
        """Process user input with enhanced context awareness."""
        
        # Add conversation context to the input
        if len(self.context.turns) > 0:
            # Inject context information for better responses
            context_hint = self.context.get_context_prompt()
            if context_hint:
                # The context is tracked but we let the system process naturally
                pass
        
        # Run through NSR pipeline
        outcome = run_text_full(user_input, self.session)
        
        # Record the turn
        turn = self.context.add_turn(user_input, outcome)
        
        # Enhance the response based on conversation flow
        enhanced_response = self._enhance_response(outcome.answer, turn)
        
        return enhanced_response, turn
    
    def _enhance_response(self, base_response: str, turn: ConversationTurn) -> str:
        """Enhance the response based on conversation context."""
        
        # For greetings, add context
        if turn.intent == 'greeting' and len(self.context.turns) == 1:
            return f"{base_response}. Como posso ajudar?"
        
        # For help requests, be more specific
        if turn.intent == 'help_request':
            if base_response == "vou consultar o NSR.":
                return "Claro, posso ajudar! O que você gostaria de saber?"
        
        # For questions, add confidence
        if turn.intent == 'question' and turn.quality > 0.8:
            if not any(punct in base_response for punct in ['.', '!', '?']):
                return f"{base_response}."
        
        return base_response
    
    def get_summary(self) -> str:
        """Get conversation summary."""
        return self.context.get_conversation_summary()


# Convenience function for easy use
def create_conversation(session: Optional[SessionCtx] = None) -> EnhancedConversation:
    """Create an enhanced conversation instance."""
    return EnhancedConversation(session)
