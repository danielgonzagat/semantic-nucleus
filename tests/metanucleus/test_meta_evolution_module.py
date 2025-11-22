from __future__ import annotations

from metanucleus.core.state import MetaState
from metanucleus.runtime.meta_runtime import MetaRuntime
from metanucleus.test.testcore import Expected, TestCase
from metanucleus.evolution.meta_evolution import (
    EvolutionConfig,
    run_evolution_session,
)


def _runtime_factory() -> MetaRuntime:
    return MetaRuntime(state=MetaState())


def test_evolution_session_finishes_when_all_tests_pass():
    tests = [
        TestCase(
            name="greeting",
            input_text="oi, tudo bem?",
            expected=Expected(intent="greeting", lang="pt", answer_prefix="Olá!"),
        )
    ]

    run = run_evolution_session(
        runtime_factory=_runtime_factory,
        tests=tests,
        project_name="Metanucleus",
        cfg=EvolutionConfig(max_rounds=2),
        apply_patch_callback=None,
    )

    assert run.finished is True
    assert "Todos os testes passaram" in run.reason
    assert run.steps[-1].patch_plans == []


def test_evolution_session_requires_callback_for_patch_plans():
    tests = [
        TestCase(
            name="force_patch",
            input_text="oi, tudo bem?",
            expected=Expected(intent="command"),  # intenção impossível para gerar patch
        )
    ]

    run = run_evolution_session(
        runtime_factory=_runtime_factory,
        tests=tests,
        project_name="Metanucleus",
        cfg=EvolutionConfig(max_rounds=1),
        apply_patch_callback=None,
    )

    assert run.finished is False
    assert "PatchPlan gerado" in run.reason
    assert run.steps[-1].patch_plans  # houve plano


def test_evolution_session_calls_patch_callback():
    tests = [
        TestCase(
            name="needs_fix",
            input_text="oi, tudo bem?",
            expected=Expected(intent="command"),
        )
    ]

    captured = {}

    def fake_apply(plan, prompt):
        captured["plan"] = plan
        captured["prompt"] = prompt
        return False

    run = run_evolution_session(
        runtime_factory=_runtime_factory,
        tests=tests,
        project_name="Metanucleus",
        cfg=EvolutionConfig(max_rounds=1),
        apply_patch_callback=fake_apply,
    )

    assert run.finished is False
    assert "Nenhum patch foi aprovado" in run.reason
    assert "plan" in captured and "prompt" in captured
