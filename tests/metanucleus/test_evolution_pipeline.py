import random
import textwrap

from metanucleus.core.evolution import EvolutionRequest, MetaEvolution


def test_meta_evolution_simplifies_redundant_terms():
    source = textwrap.dedent(
        """
        def calcular(x):
            return (x * 2) + (x * 2)
        """
    )
    request = EvolutionRequest(source=source, function_name="calcular")
    result = MetaEvolution().evolve(request)

    assert result.success, f"esperado sucesso, motivo: {result.reason}"
    assert result.optimized_source is not None
    normalized = result.optimized_source.replace(" ", "")
    assert "return4*x" in normalized
    assert result.analysis is not None
    assert result.analysis.cost_after < result.analysis.cost_before
    assert "py_function" in result.analysis.liu_repr
    assert result.diff
    diff_normalized = result.diff.replace(" ", "")
    assert "-return(x*2)+(x*2)" in diff_normalized
    assert "+return4*x" in diff_normalized


def test_meta_evolution_reports_no_change_when_not_optimizible():
    source = textwrap.dedent(
        """
        def soma(a, b):
            return a + b
        """
    )
    request = EvolutionRequest(source=source, function_name="soma")
    result = MetaEvolution().evolve(request)

    assert not result.success
    assert result.reason == "no_optimization_found"


def test_meta_evolution_regression_guard():
    # otimização quebra comportamento por colapsar duas chamadas randômicas em uma só
    source = textwrap.dedent(
        """
        import random

        def noisy():
            return random.random() + random.random()
        """
    )
    random.seed(123)
    request = EvolutionRequest(source=source, function_name="noisy", samples=[()])
    result = MetaEvolution().evolve(request)

    assert not result.success
    assert result.reason == "regression_failed"
