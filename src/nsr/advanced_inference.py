"""
Advanced Inference Engine - Making the AI More Intelligent

This module implements advanced inference capabilities from the roadmap:
- Φ_INFER advanced with multiple inference types
- Causal reasoning (A causes B)
- Temporal reasoning (A before B)
- Conditional reasoning (if-then-else)
- Contradiction detection
- Inference explanation with proofs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple
from collections import defaultdict

from liu import Node, NodeKind, entity, relation, struct, text, operation
from nsr.state import SessionCtx, Rule, ISR


@dataclass
class InferenceRule:
    """A single inference rule with conditions and consequences."""
    name: str
    conditions: List[Node]
    consequences: List[Node]
    confidence: float
    rule_type: str  # 'causal', 'temporal', 'conditional', 'transitive'
    
    def __repr__(self):
        return f"InferenceRule({self.name}, type={self.rule_type}, confidence={self.confidence:.2f})"


@dataclass
class InferenceProof:
    """Proof of an inference with all steps traced."""
    conclusion: Node
    rules_applied: List[InferenceRule] = field(default_factory=list)
    premises: List[Node] = field(default_factory=list)
    confidence: float = 1.0
    
    def add_step(self, rule: InferenceRule, premise: Node):
        """Add a step to the proof."""
        self.rules_applied.append(rule)
        self.premises.append(premise)
        self.confidence *= rule.confidence


class AdvancedInferenceEngine:
    """
    Advanced inference engine that makes the AI truly intelligent.
    
    Implements multiple types of inference:
    - Transitive: A→B, B→C ⟹ A→C
    - Causal: A causes B, B causes C ⟹ A causes C
    - Temporal: A before B, B before C ⟹ A before C
    - Conditional: if A then B, A ⟹ B
    - Contrapositive: if A then B ⟹ if not B then not A
    """
    
    def __init__(self, session: SessionCtx):
        self.session = session
        self.inference_rules: List[InferenceRule] = []
        self.proofs: List[InferenceProof] = []
        self._init_basic_rules()
    
    def _init_basic_rules(self):
        """Initialize basic inference rules."""
        
        # Causal rules
        self.add_rule(InferenceRule(
            name="causal_transitivity",
            conditions=[
                relation("causes", entity("A"), entity("B")),
                relation("causes", entity("B"), entity("C"))
            ],
            consequences=[
                relation("causes", entity("A"), entity("C"))
            ],
            confidence=0.9,
            rule_type="causal"
        ))
        
        # Temporal rules
        self.add_rule(InferenceRule(
            name="temporal_transitivity",
            conditions=[
                relation("before", entity("A"), entity("B")),
                relation("before", entity("B"), entity("C"))
            ],
            consequences=[
                relation("before", entity("A"), entity("C"))
            ],
            confidence=1.0,
            rule_type="temporal"
        ))
        
        # Conditional rules
        self.add_rule(InferenceRule(
            name="modus_ponens",
            conditions=[
                relation("implies", entity("A"), entity("B")),
                entity("A")
            ],
            consequences=[entity("B")],
            confidence=1.0,
            rule_type="conditional"
        ))
        
        # Contrapositive
        self.add_rule(InferenceRule(
            name="contrapositive",
            conditions=[
                relation("implies", entity("A"), entity("B"))
            ],
            consequences=[
                relation("implies", relation("not", entity("B")), relation("not", entity("A")))
            ],
            confidence=1.0,
            rule_type="conditional"
        ))
        
        # Symmetry rules
        self.add_rule(InferenceRule(
            name="symmetric_relation",
            conditions=[
                relation("similar_to", entity("A"), entity("B"))
            ],
            consequences=[
                relation("similar_to", entity("B"), entity("A"))
            ],
            confidence=1.0,
            rule_type="transitive"
        ))
    
    def add_rule(self, rule: InferenceRule):
        """Add an inference rule."""
        self.inference_rules.append(rule)
    
    def infer(self, knowledge: List[Node], max_iterations: int = 10) -> Tuple[List[Node], List[InferenceProof]]:
        """
        Apply inference rules to derive new knowledge.
        
        Args:
            knowledge: List of known facts
            max_iterations: Maximum inference iterations
            
        Returns:
            Tuple of (new_knowledge, proofs)
        """
        all_knowledge = set(self._fingerprint_node(n) for n in knowledge)
        new_facts: List[Node] = []
        proofs: List[InferenceProof] = []
        
        for iteration in range(max_iterations):
            iteration_facts = []
            
            for rule in self.inference_rules:
                # Try to match rule conditions against knowledge
                matches = self._match_rule(rule, knowledge)
                
                for match in matches:
                    # Apply rule to get consequences
                    consequences = self._apply_rule(rule, match)
                    
                    # Add new consequences
                    for consequence in consequences:
                        fp = self._fingerprint_node(consequence)
                        if fp not in all_knowledge:
                            iteration_facts.append(consequence)
                            all_knowledge.add(fp)
                            
                            # Create proof
                            proof = InferenceProof(conclusion=consequence)
                            for cond in match:
                                proof.add_step(rule, cond)
                            proofs.append(proof)
            
            if not iteration_facts:
                break  # No new facts derived
            
            new_facts.extend(iteration_facts)
            knowledge = knowledge + iteration_facts
        
        return new_facts, proofs
    
    def _match_rule(self, rule: InferenceRule, knowledge: List[Node]) -> List[List[Node]]:
        """Match rule conditions against knowledge."""
        matches: List[List[Node]] = []
        
        # Simple matching: try to find all conditions in knowledge
        for i, fact in enumerate(knowledge):
            if self._matches_pattern(rule.conditions[0], fact):
                # Found first condition, try to find others
                match = [fact]
                
                if len(rule.conditions) == 1:
                    matches.append(match)
                elif len(rule.conditions) == 2:
                    # Look for second condition
                    for j, fact2 in enumerate(knowledge[i+1:], i+1):
                        if self._matches_pattern(rule.conditions[1], fact2):
                            matches.append([fact, fact2])
        
        return matches
    
    def _matches_pattern(self, pattern: Node, fact: Node) -> bool:
        """Check if a fact matches a pattern."""
        if pattern.kind != fact.kind:
            return False
        
        if pattern.kind == NodeKind.ENTITY:
            # Entity matches if labels are similar or pattern is variable
            if pattern.label and pattern.label.startswith("?"):
                return True  # Variable matches anything
            return pattern.label == fact.label
        
        if pattern.kind == NodeKind.REL:
            # Relation matches if label is same and args match
            if pattern.label != fact.label:
                return False
            
            if len(pattern.args) != len(fact.args):
                return False
            
            # Check if args match (recursively)
            for p_arg, f_arg in zip(pattern.args, fact.args):
                if not self._matches_pattern(p_arg, f_arg):
                    return False
            
            return True
        
        return False
    
    def _apply_rule(self, rule: InferenceRule, match: List[Node]) -> List[Node]:
        """Apply a rule with matched conditions."""
        consequences = []
        
        # Simple substitution: replace variables in consequences
        for consequence in rule.consequences:
            # For now, return consequence as-is
            # In full implementation, would substitute matched variables
            consequences.append(consequence)
        
        return consequences
    
    def _fingerprint_node(self, node: Node) -> str:
        """Create fingerprint for deduplication."""
        from liu import fingerprint
        return fingerprint(node)
    
    def explain_inference(self, proof: InferenceProof) -> str:
        """Explain an inference in natural language."""
        explanation = [f"Conclusion: {self._node_to_text(proof.conclusion)}"]
        explanation.append(f"Confidence: {proof.confidence:.2%}")
        explanation.append("\nProof steps:")
        
        for i, (rule, premise) in enumerate(zip(proof.rules_applied, proof.premises), 1):
            explanation.append(f"  {i}. Applied {rule.name} ({rule.rule_type})")
            explanation.append(f"     Premise: {self._node_to_text(premise)}")
        
        return "\n".join(explanation)
    
    def _node_to_text(self, node: Node) -> str:
        """Convert node to readable text."""
        if node.kind == NodeKind.ENTITY and node.label:
            return node.label
        elif node.kind == NodeKind.REL and node.label:
            args_text = ", ".join(self._node_to_text(arg) for arg in node.args)
            return f"{node.label}({args_text})"
        elif node.kind == NodeKind.TEXT and node.label:
            return node.label
        else:
            from liu import fingerprint
            return fingerprint(node)[:16]
    
    def detect_contradictions(self, knowledge: List[Node]) -> List[Tuple[Node, Node]]:
        """Detect contradictions in knowledge base."""
        contradictions: List[Tuple[Node, Node]] = []
        
        for i, fact1 in enumerate(knowledge):
            for fact2 in knowledge[i+1:]:
                if self._is_contradiction(fact1, fact2):
                    contradictions.append((fact1, fact2))
        
        return contradictions
    
    def _is_contradiction(self, fact1: Node, fact2: Node) -> bool:
        """Check if two facts contradict each other."""
        # Simple contradiction detection
        if fact1.kind == NodeKind.REL and fact2.kind == NodeKind.REL:
            # Check for opposite relations
            if fact1.label == "not" and len(fact1.args) == 1:
                return self._matches_pattern(fact1.args[0], fact2)
            if fact2.label == "not" and len(fact2.args) == 1:
                return self._matches_pattern(fact2.args[0], fact1)
        
        return False


def create_inference_engine(session: Optional[SessionCtx] = None) -> AdvancedInferenceEngine:
    """Create an advanced inference engine."""
    return AdvancedInferenceEngine(session or SessionCtx())


__all__ = [
    "AdvancedInferenceEngine",
    "InferenceRule",
    "InferenceProof",
    "create_inference_engine"
]
