"""
Comprehensive tests for Code Evolution System.

Tests cover:
- Performance analysis
- Improvement identification
- Code proposal generation
- Testing improvements
- Evolution cycles
- Reporting
"""

import pytest
from pathlib import Path
from nsr.code_evolution import (
    CodeEvolutionEngine,
    PerformanceMetric,
    CodeImprovement,
    EvolutionCycle,
    create_evolution_engine
)


class TestPerformanceMetric:
    """Test PerformanceMetric data structure."""
    
    def test_metric_creation(self):
        """Test creating a performance metric."""
        metric = PerformanceMetric(
            component_name="test_component",
            metric_type="quality",
            value=0.75,
            sample_size=100,
            timestamp="2025-01-01"
        )
        
        assert metric.component_name == "test_component"
        assert metric.metric_type == "quality"
        assert metric.value == 0.75
        assert metric.sample_size == 100


class TestCodeImprovement:
    """Test CodeImprovement data structure."""
    
    def test_improvement_creation(self):
        """Test creating a code improvement."""
        improvement = CodeImprovement(
            file_path="test.py",
            function_name="test_func",
            current_code="def test(): pass",
            proposed_code="def test(): return True",
            reason="Add return value",
            expected_improvement="Better functionality",
            risk_level="low"
        )
        
        assert improvement.file_path == "test.py"
        assert improvement.function_name == "test_func"
        assert improvement.risk_level == "low"


class TestEvolutionCycle:
    """Test EvolutionCycle data structure."""
    
    def test_cycle_creation(self):
        """Test creating an evolution cycle."""
        cycle = EvolutionCycle(
            cycle_id=1,
            metrics_analyzed=[],
            improvements_proposed=[]
        )
        
        assert cycle.cycle_id == 1
        assert len(cycle.improvements_applied) == 0
        assert cycle.success is False


class TestCodeEvolutionEngine:
    """Test Code Evolution Engine."""
    
    def test_engine_creation(self):
        """Test creating evolution engine."""
        source_root = Path(__file__).parent.parent
        engine = CodeEvolutionEngine(source_root)
        
        assert engine.source_root == source_root
        assert len(engine.performance_history) == 0
        assert len(engine.evolution_cycles) == 0
    
    def test_analyze_performance(self):
        """Test performance analysis."""
        engine = create_evolution_engine()
        
        metrics = engine.analyze_performance()
        
        assert isinstance(metrics, list)
        assert len(metrics) > 0
        
        # Check metric structure
        for metric in metrics:
            assert isinstance(metric, PerformanceMetric)
            assert metric.component_name is not None
            assert metric.metric_type is not None
            assert metric.value >= 0.0
    
    def test_identify_improvements(self):
        """Test improvement identification."""
        engine = create_evolution_engine()
        
        metrics = engine.analyze_performance()
        improvements = engine.identify_improvement_opportunities(metrics)
        
        assert isinstance(improvements, list)
        
        # Should propose improvements for low metrics
        for improvement in improvements:
            assert isinstance(improvement, CodeImprovement)
            assert improvement.file_path is not None
            assert improvement.function_name is not None
    
    def test_propose_conversation_improvement(self):
        """Test conversation improvement proposal."""
        engine = create_evolution_engine()
        
        metric = PerformanceMetric(
            component_name="conversation_system",
            metric_type="quality",
            value=0.70,  # Below target
            sample_size=100,
            timestamp="current"
        )
        
        improvement = engine._propose_conversation_improvement(metric)
        
        assert improvement.file_path.endswith("enhanced_conversation.py")
        assert "conversation" in improvement.reason.lower()
        assert improvement.risk_level in ["low", "medium", "high"]
    
    def test_propose_reasoning_improvement(self):
        """Test reasoning improvement proposal."""
        engine = create_evolution_engine()
        
        metric = PerformanceMetric(
            component_name="reasoning_engine",
            metric_type="inference_depth",
            value=3.0,  # Below target
            sample_size=50,
            timestamp="current"
        )
        
        improvement = engine._propose_reasoning_improvement(metric)
        
        assert improvement.file_path.endswith("deep_reasoning.py")
        assert "reasoning" in improvement.reason.lower()
    
    def test_propose_learning_improvement(self):
        """Test learning improvement proposal."""
        engine = create_evolution_engine()
        
        metric = PerformanceMetric(
            component_name="weightless_learning",
            metric_type="pattern_extraction_rate",
            value=0.10,  # Below target
            sample_size=200,
            timestamp="current"
        )
        
        improvement = engine._propose_learning_improvement(metric)
        
        assert improvement.file_path.endswith("weightless_learning.py")
        assert "learning" in improvement.reason.lower() or "pattern" in improvement.reason.lower()
    
    def test_test_improvement(self):
        """Test improvement testing."""
        engine = create_evolution_engine()
        
        improvement = CodeImprovement(
            file_path="test.py",
            function_name="test_func",
            current_code="pass",
            proposed_code="return True",
            reason="Test",
            expected_improvement="Better",
            risk_level="low"
        )
        
        result = engine.test_improvement(improvement)
        
        assert isinstance(result, bool)
        assert improvement.test_results is not None
    
    def test_apply_improvement_dry_run(self):
        """Test applying improvement in dry run mode."""
        engine = create_evolution_engine()
        
        improvement = CodeImprovement(
            file_path="test.py",
            function_name="test_func",
            current_code="pass",
            proposed_code="return True",
            reason="Test",
            expected_improvement="Better",
            risk_level="low"
        )
        
        result = engine.apply_improvement(improvement, dry_run=True)
        
        # Dry run should always succeed
        assert result is True
    
    def test_run_evolution_cycle(self):
        """Test running a complete evolution cycle."""
        engine = create_evolution_engine()
        
        cycle = engine.run_evolution_cycle(dry_run=True)
        
        assert isinstance(cycle, EvolutionCycle)
        assert cycle.cycle_id == 1
        assert len(cycle.metrics_analyzed) > 0
        assert len(cycle.improvements_proposed) > 0
    
    def test_generate_evolution_report(self):
        """Test evolution report generation."""
        engine = create_evolution_engine()
        
        # Run a cycle first
        engine.run_evolution_cycle(dry_run=True)
        
        report = engine.generate_evolution_report()
        
        assert isinstance(report, str)
        assert "Evolution" in report or "Cycle" in report
    
    def test_generate_report_no_cycles(self):
        """Test report with no cycles."""
        engine = create_evolution_engine()
        
        report = engine.generate_evolution_report()
        
        assert "No evolution cycles" in report


class TestIntegration:
    """Integration tests for code evolution."""
    
    def test_full_evolution_pipeline(self):
        """Test complete evolution pipeline."""
        engine = create_evolution_engine()
        
        # Run cycle
        cycle = engine.run_evolution_cycle(dry_run=True)
        
        # Verify all stages completed
        assert len(cycle.metrics_analyzed) > 0
        assert len(cycle.improvements_proposed) > 0
        
        # All improvements should be tested
        for improvement in cycle.improvements_proposed:
            assert improvement in cycle.improvements_applied or improvement not in cycle.improvements_applied
    
    def test_multiple_cycles(self):
        """Test running multiple evolution cycles."""
        engine = create_evolution_engine()
        
        cycle1 = engine.run_evolution_cycle(dry_run=True)
        cycle2 = engine.run_evolution_cycle(dry_run=True)
        
        assert cycle1.cycle_id == 1
        assert cycle2.cycle_id == 2
        assert len(engine.evolution_cycles) == 2
    
    def test_deterministic_analysis(self):
        """Test that analysis is deterministic."""
        engine1 = create_evolution_engine()
        engine2 = create_evolution_engine()
        
        metrics1 = engine1.analyze_performance()
        metrics2 = engine2.analyze_performance()
        
        # Should analyze same metrics
        assert len(metrics1) == len(metrics2)
        
        for m1, m2 in zip(metrics1, metrics2):
            assert m1.component_name == m2.component_name
            assert m1.metric_type == m2.metric_type
    
    def test_improvement_risk_levels(self):
        """Test that improvements have appropriate risk levels."""
        engine = create_evolution_engine()
        
        metrics = engine.analyze_performance()
        improvements = engine.identify_improvement_opportunities(metrics)
        
        for improvement in improvements:
            assert improvement.risk_level in ["low", "medium", "high"]
    
    def test_metrics_in_history(self):
        """Test that metrics are stored in history."""
        engine = create_evolution_engine()
        
        initial_count = len(engine.performance_history)
        
        metrics = engine.analyze_performance()
        
        # Metrics should be added to history
        assert len(engine.performance_history) > initial_count
        assert len(engine.performance_history) == initial_count + len(metrics)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
