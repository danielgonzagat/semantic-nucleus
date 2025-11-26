"""Orquestrador de autoevolução supervisionada de alto nível."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional

from metanucleus.runtime.meta_runtime import MetaRuntime
from metanucleus.test.testcore import TestCase, TestResult, PatchSuggestion, run_test_suite


# ---------------------------------------------------------------------------
# Modelos centrais
# ---------------------------------------------------------------------------


@dataclass()
class EvolutionConfig:
    """Configuração de uma sessão de evolução."""

    max_rounds: int = 5
    stop_on_all_green: bool = True
    focus_on_first_failure: bool = True


@dataclass()
class PatchPlan:
    """
    Descreve um patch sugerido em termos humanos/estruturados.

    Essa estrutura é enviada para uma IA programadora ou humano responsável
    por aplicar a modificação no código-fonte.
    """

    module: str
    reason: str
    hints: Dict[str, object]
    related_test: str
    input_example: str
    expected_behavior: Dict[str, object]
    detected_behavior: Dict[str, object]
    raw_patch_suggestion: Dict[str, object]


@dataclass()
class EvolutionStep:
    """Um round da evolução supervisionada."""

    round_idx: int
    results: List[TestResult]
    patch_plans: List[PatchPlan]


@dataclass()
class EvolutionRun:
    """Relatório completo da sessão."""

    steps: List[EvolutionStep]
    finished: bool
    reason: str


# ---------------------------------------------------------------------------
# Helpers para transformar TestResult -> PatchPlan
# ---------------------------------------------------------------------------


def _extract_expected_dict(testcase: TestCase) -> Dict[str, object]:
    exp = testcase.expected
    return {
        "intent": exp.intent,
        "lang": exp.lang,
        "answer_prefix": exp.answer_prefix,
        "answer_contains": exp.answer_contains,
    }


def _extract_detected_dict(result: TestResult) -> Dict[str, object]:
    return {
        "detected_intent": result.detected_intent,
        "detected_lang": result.detected_lang,
        "raw_answer": result.raw_answer,
    }


def _make_patch_plan(result: TestResult) -> Optional[PatchPlan]:
    """Traduz a PatchSuggestion do TESTCORE em um PatchPlan detalhado."""

    patch: Optional[PatchSuggestion] = result.patch
    if patch is None:
        return None

    return PatchPlan(
        module=patch.module,
        reason=patch.reason,
        hints=patch.hints or {},
        related_test=result.case.name,
        input_example=result.case.input_text,
        expected_behavior=_extract_expected_dict(result.case),
        detected_behavior=_extract_detected_dict(result),
        raw_patch_suggestion={
            "module": patch.module,
            "reason": patch.reason,
            "hints": patch.hints or {},
        },
    )


def build_patch_plans(results: List[TestResult], focus_on_first_failure: bool = True) -> List[PatchPlan]:
    """
    Gera planos de patch a partir dos testes que falharam.

    Se focus_on_first_failure=True, produz apenas o primeiro plano (útil para loops curtos).
    """

    plans: List[PatchPlan] = []
    for result in results:
        if result.passed:
            continue
        plan = _make_patch_plan(result)
        if plan is not None:
            plans.append(plan)
            if focus_on_first_failure:
                break
    return plans


def build_patch_prompt(project_name: str, plan: PatchPlan) -> str:
    """Prompt estruturado para uma IA programadora aplicar o patch."""

    lines: List[str] = [
        f"Você é uma IA programadora especializada no projeto: {project_name}.",
        "",
        "Objetivo: aplicar um patch no Metanúcleo para corrigir o comportamento abaixo.",
        "",
        "=== CASO DE TESTE RELACIONADO ===",
        f"- Nome: {plan.related_test}",
        f"- Input: {plan.input_example!r}",
        "",
        "=== COMPORTAMENTO ESPERADO ===",
    ]
    for key, value in plan.expected_behavior.items():
        lines.append(f"- {key}: {value!r}")
    lines.extend(
        [
            "",
            "=== COMPORTAMENTO DETECTADO ===",
        ]
    )
    for key, value in plan.detected_behavior.items():
        lines.append(f"- {key}: {value!r}")
    lines.extend(
        [
            "",
            "=== MÓDULO ALVO ===",
            f"- módulo sugerido: {plan.module}",
            f"- motivo: {plan.reason}",
            "",
            "=== HINTS ===",
        ]
    )
    if plan.hints:
        for key, value in plan.hints.items():
            lines.append(f"- {key}: {value!r}")
    else:
        lines.append("- (sem hints adicionais)")
    lines.extend(
        [
            "",
            "=== INSTRUÇÕES ===",
            "1) Localize o módulo/arquivo indicado e revise a lógica atual.",
            "2) Faça uma alteração mínima e determinística que faça o teste passar.",
            "3) Retorne o patch (diff) e um resumo do que mudou.",
            "4) Não introduza dependências externas nem heurísticas não determinísticas.",
        ]
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Execução principal
# ---------------------------------------------------------------------------

ApplyPatchCallback = Callable[[PatchPlan, str], bool]
RuntimeFactory = Callable[[], MetaRuntime]


def run_evolution_session(
    runtime_factory: RuntimeFactory,
    tests: List[TestCase],
    project_name: str,
    cfg: Optional[EvolutionConfig] = None,
    apply_patch_callback: Optional[ApplyPatchCallback] = None,
) -> EvolutionRun:
    """
    Executa vários rounds:

    1. Cria um runtime fresco via runtime_factory.
    2. Roda TESTCORE.
    3. Se todos os testes passam → encerra com sucesso.
    4. Caso contrário, gera PatchPlan(s) e, se houver callback, pede aplicação de patch.
    5. Se nenhum patch for aplicado, encerra informando o motivo.
    """

    if cfg is None:
        cfg = EvolutionConfig()

    steps: List[EvolutionStep] = []

    for round_idx in range(1, cfg.max_rounds + 1):
        runtime = runtime_factory()
        results = run_test_suite(runtime, tests)
        plans = build_patch_plans(results, focus_on_first_failure=cfg.focus_on_first_failure)

        steps.append(EvolutionStep(round_idx=round_idx, results=results, patch_plans=plans))

        all_passed = all(r.passed for r in results)
        if all_passed:
            return EvolutionRun(
                steps=steps,
                finished=True,
                reason=f"Todos os testes passaram no round {round_idx}.",
            )

        if not plans:
            return EvolutionRun(
                steps=steps,
                finished=False,
                reason=f"Sem planos de patch gerados no round {round_idx}.",
            )

        if apply_patch_callback is None:
            return EvolutionRun(
                steps=steps,
                finished=False,
                reason=(
                    "PatchPlan gerado, mas nenhum apply_patch_callback foi fornecido "
                    "para aplicar as sugestões."
                ),
            )

        any_applied = False
        for plan in plans:
            prompt = build_patch_prompt(project_name, plan)
            try:
                applied = apply_patch_callback(plan, prompt)
            except Exception as exc:  # pragma: no cover
                applied = False
                plan.hints.setdefault("callback_error", str(exc))
            if applied:
                any_applied = True

        if not any_applied:
            return EvolutionRun(
                steps=steps,
                finished=False,
                reason=f"Nenhum patch foi aprovado/aplicado no round {round_idx}.",
            )

    return EvolutionRun(
        steps=steps,
        finished=False,
        reason=f"Número máximo de rounds ({cfg.max_rounds}) atingido.",
    )


__all__ = [
    "EvolutionConfig",
    "PatchPlan",
    "EvolutionStep",
    "EvolutionRun",
    "run_evolution_session",
    "build_patch_plans",
    "build_patch_prompt",
]
