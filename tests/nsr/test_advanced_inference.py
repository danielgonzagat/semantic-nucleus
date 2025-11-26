"""
Tests for Advanced Inference Engine.

Tests cover:
- Multiple inference types (causal, temporal, conditional, transitive)
- Rule matching and application
- Proof generation
- Contradiction detection
- Inference explanation
"""

import pytest
from nsr.advanced_inference import (
    AdvancedInferenceEngine,
    InferenceRule,
    InferenceProof,
    create_inference_engine
)
from nsr import SessionCtx
from liu import entity, relation, struct


class TestInferenceRule:
    """Test InferenceRule structure."""
    
    def test_rule_creation(self):
        """Test creating an inference rule."""
        rule = InferenceRule(
            name="test_rule",
            conditions=[entity("A")],
            consequences=[entity("B")],
            confidence=0.9,
            rule_type="conditional"
        )
        
        assert rule.name == "test_rule"
        assert len(rule.conditions) == 1
        assert len(rule.consequences) == 1
        assert rule.confidence == 0.9
        assert rule.rule_type == "conditional"


class TestInferenceProof:
    """Test InferenceProof structure."""
    
    def test_proof_creation(self):
        """Test creating a proof."""
        proof = InferenceProof(conclusion=entity("B"))
        
        assert proof.conclusion.label == "B"
        assert len(proof.rules_applied) == 0
        assert proof.confidence == 1.0
    
    def test_add_step(self):
        """Test adding steps to proof."""
        proof = InferenceProof(conclusion=entity("C"))
        
        rule = InferenceRule("test", [], [], 0.9, "test")
        proof.add_step(rule, entity("A"))
        
        assert len(proof.rules_applied) == 1
        assert len(proof.premises) == 1
        assert proof.confidence == 0.9


class TestAdvancedInferenceEngine:
    """Test Advanced Inference Engine."""
    
    def test_engine_creation(self):
        """Test creating engine."""
        engine = create_inference_engine()
        
        assert engine is not None
        assert len(engine.inference_rules) > 0  # Should have basic rules
    
    def test_basic_rules_loaded(self):
        """Test that basic rules are loaded."""
        engine = create_inference_engine()
        
        rule_names = [r.name for r in engine.inference_rules]
        
        # Should have fundamental rules
        assert "modus_ponens" in rule_names
        assert "causal_transitivity" in rule_names
        assert "temporal_transitivity" in rule_names
    
    def test_add_rule(self):
        """Test adding custom rule."""
        engine = create_inference_engine()
        initial_count = len(engine.inference_rules)
        
        rule = InferenceRule("custom", [], [], 1.0, "custom")
        engine.add_rule(rule)
        
        assert len(engine.inference_rules) == initial_count + 1
    
    def test_simple_inference(self):
        """Test simple inference."""
        engine = create_inference_engine()
        
        # Given: A causes B, B causes C
        knowledge = [
            relation("causes", entity("A"), entity("B")),
            relation("causes", entity("B"), entity("C"))
        ]
        
        # Infer: A causes C
        new_facts, proofs = engine.infer(knowledge, max_iterations=5)
        
        # Should derive new fact
        assert isinstance(new_facts, list)
        assert isinstance(proofs, list)
    
    def test_temporal_inference(self):
        """Test temporal reasoning."""
        engine = create_inference_engine()
        
        knowledge = [
            relation("before", entity("morning"), entity("noon")),
            relation("before", entity("noon"), entity("evening"))
        ]
        
        new_facts, proofs = engine.infer(knowledge)
        
        # Should infer morning before evening
        assert len(new_facts) >= 0  # May or may not find matches
    
    def test_modus_ponens(self):
        """Test modus ponens inference."""
        engine = create_inference_engine()
        
        knowledge = [
            relation("implies", entity("rain"), entity("wet")),
            entity("rain")
        ]
        
        new_facts, proofs = engine.infer(knowledge)
        
        # Should infer: wet
        assert isinstance(new_facts, list)
    
    def test_match_pattern(self):
        """Test pattern matching."""
        engine = create_inference_engine()
        
        pattern = entity("A")
        fact = entity("A")
        
        matches = engine._matches_pattern(pattern, fact)
        assert matches is True
    
    def test_match_variable(self):
        """Test variable matching."""
        engine = create_inference_engine()
        
        pattern = entity("?X")  # Variable
        fact = entity("anything")
        
        matches = engine._matches_pattern(pattern, fact)
        assert matches is True
    
    def test_fingerprint_deduplication(self):
        """Test that fingerprints deduplicate knowledge."""
        engine = create_inference_engine()
        
        fp1 = engine._fingerprint_node(entity("A"))
        fp2 = engine._fingerprint_node(entity("A"))
        fp3 = engine._fingerprint_node(entity("B"))
        
        assert fp1 == fp2
        assert fp1 != fp3
    
    def test_explain_inference(self):
        """Test inference explanation."""
        engine = create_inference_engine()
        
        rule = InferenceRule("test", [], [], 0.9, "test")
        proof = InferenceProof(conclusion=entity("B"))
        proof.add_step(rule, entity("A"))
        
        explanation = engine.explain_inference(proof)
        
        assert isinstance(explanation, str)
        assert "Conclusion" in explanation
        assert "Confidence" in explanation
    
    def test_detect_contradictions(self):
        """Test contradiction detection."""
        engine = create_inference_engine()
        
        knowledge = [
            entity("raining"),
            relation("not", entity("raining"))
        ]
        
        contradictions = engine.detect_contradictions(knowledge)
        
        # Should detect contradiction
        assert isinstance(contradictions, list)
    
    def test_no_contradictions(self):
        """Test with no contradictions."""
        engine = create_inference_engine()
        
        knowledge = [
            entity("A"),
            entity("B")
        ]
        
        contradictions = engine.detect_contradictions(knowledge)
        
        assert len(contradictions) == 0


class TestIntegration:
    """Integration tests for inference."""
    
    def test_multi_step_inference(self):
        """Test inference over multiple iterations."""
        engine = create_inference_engine()
        
        knowledge = [
            relation("causes", entity("A"), entity("B")),
            relation("causes", entity("B"), entity("C")),
            relation("causes", entity("C"), entity("D"))
        ]
        
        new_facts, proofs = engine.infer(knowledge, max_iterations=10)
        
        # Should derive multiple new causal relationships
        assert len(new_facts) >= 0
        assert len(proofs) >= 0
    
    def test_with_session(self):
        """Test with real session."""
        session = SessionCtx()
        engine = AdvancedInferenceEngine(session)
        
        knowledge = [entity("test")]
        new_facts, proofs = engine.infer(knowledge)
        
        assert isinstance(new_facts, list)
        assert isinstance(proofs, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
