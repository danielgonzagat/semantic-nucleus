"""
MetaKernel central do Metanúcleo — orquestra runtime e autoevolução.
"""

from __future__ import annotations

import json

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, TYPE_CHECKING

from liu import to_json
from nsr import SessionCtx, run_text_full, meta_summary_to_dict

from metanucleus.core.sandbox import MetaSandbox
from metanucleus.core.state import MetaState
from metanucleus.evolution.intent_auto_patch import suggest_intent_patches
from metanucleus.evolution.meta_calculus_auto_patch import suggest_meta_calculus_patches
from metanucleus.evolution.rule_patch_generator import RulePatchGenerator
from metanucleus.evolution.semantic_frames_auto_patch import suggest_frame_patches
from metanucleus.evolution.semantic_patch_generator import SemanticPatchGenerator
from metanucleus.evolution.types import EvolutionPatch

if TYPE_CHECKING:
    from metanucleus.runtime.meta_runtime import MetaRuntime
    from nsr.meta_calculator import MetaCalculationResult


# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class AutoEvolutionConfig:
    enable_intent: bool = True
    enable_calculus: bool = True
    max_new_intent_rules: int = 10
    max_new_calculus_rules: int = 10


@dataclass(slots=True)
class MetaKernelConfig:
    auto_evolution: AutoEvolutionConfig = field(default_factory=AutoEvolutionConfig)


@dataclass(slots=True)
class MetaKernelTurnResult:
    answer_text: str
    answer_struct: Any | None = None
    suggested_patches: List[EvolutionPatch] = field(default_factory=list)
    debug_info: Dict[str, Any] = field(default_factory=dict)
    meta_summary: Dict[str, Any] | None = None
    calc_exec: Dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# MetaKernel
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class MetaKernel:
    state: MetaState = field(default_factory=MetaState)
    config: MetaKernelConfig = field(default_factory=MetaKernelConfig)
    nsr_session: SessionCtx = field(default_factory=SessionCtx)

    @classmethod
    def bootstrap(cls) -> MetaKernel:
        return cls(state=MetaState())

    # ---------------- Runtime helpers ---------------- #

    def spawn_runtime(self) -> "MetaRuntime":
        sandbox = MetaSandbox.from_state(self.state)
        return sandbox.spawn_runtime()

    def handle_turn(
        self,
        user_text: str,
        *,
        session_id: Optional[str] = None,
        enable_auto_evolution: bool = False,
        evolution_domains: Optional[List[str]] = None,
    ) -> MetaKernelTurnResult:
        if evolution_domains is None:
            evolution_domains = ["intent", "calculus"]

        answer_text, answer_struct, debug, meta_summary, calc_exec = self._run_symbolic_pipeline(
            user_text=user_text
        )
        if session_id:
            debug["session_id"] = session_id

        patches: List[EvolutionPatch] = []
        if enable_auto_evolution:
            patches = self.run_auto_evolution_cycle(domains=evolution_domains)

        return MetaKernelTurnResult(
            answer_text=answer_text,
            answer_struct=answer_struct,
            suggested_patches=patches,
            debug_info=debug,
            meta_summary=meta_summary,
            calc_exec=calc_exec,
        )

    def _run_symbolic_pipeline(
        self, user_text: str
    ) -> tuple[str, Any | None, Dict[str, Any], Dict[str, Any] | None, Dict[str, Any] | None]:
        """
        Conecta diretamente ao NSR e devolve resposta, STRUCT e pacote meta.
        """

        outcome = run_text_full(user_text, session=self.nsr_session)
        answer_struct = outcome.isr.answer if outcome.isr else None
        answer_text = outcome.answer
        meta_dict: Dict[str, Any] | None = None
        if outcome.meta_summary is not None:
            meta_dict = meta_summary_to_dict(outcome.meta_summary)
            self._record_meta_history(meta_dict)
        calc_exec: Dict[str, Any] | None = None
        debug_info: Dict[str, Any] = {
            "trace_digest": outcome.trace.digest,
            "trace_steps": len(outcome.trace.steps),
            "halt_reason": outcome.halt_reason.value,
            "quality": outcome.quality,
            "finalized": outcome.finalized,
            "route": meta_dict.get("route") if meta_dict else None,
            "language": meta_dict.get("language") if meta_dict else None,
        }
        if meta_dict:
            debug_info["meta_summary"] = meta_dict
            debug_info["meta_digest"] = meta_dict.get("meta_digest")
            debug_info["phi_plan_chain"] = meta_dict.get("phi_plan_chain")
            debug_info["phi_plan_digest"] = meta_dict.get("phi_plan_digest")
            debug_info["calc_exec_snapshot_digest"] = meta_dict.get("calc_exec_snapshot_digest")
            debug_info["calc_exec_consistent"] = meta_dict.get("calc_exec_consistent")
            debug_info["calc_exec_error"] = meta_dict.get("calc_exec_error")
        if outcome.lc_meta is not None:
            debug_info["lc_meta"] = to_json(outcome.lc_meta)
        if outcome.language_profile is not None:
            debug_info["language_profile"] = to_json(outcome.language_profile)
        if outcome.code_summary is not None and meta_dict:
            debug_info["code_summary"] = meta_dict.get("code_summary_function_details")
            debug_info["code_summary_digest"] = meta_dict.get("code_summary_digest")
        if outcome.calc_plan is not None:
            debug_info["calc_plan_route"] = outcome.calc_plan.route.value
            debug_info["calc_plan_description"] = outcome.calc_plan.description
        if outcome.calc_result is not None:
            debug_info.setdefault("calc_exec_consistent", outcome.calc_result.consistent)
            debug_info.setdefault("calc_exec_error", outcome.calc_result.error)
            calc_exec = _calc_result_to_dict(outcome.calc_result)
        return answer_text, answer_struct, debug_info, meta_dict, calc_exec

    def _record_meta_history(self, entry: Dict[str, Any]) -> None:
        record = dict(entry)
        self.state.meta_history.append(record)
        limit = getattr(self.nsr_session.config, "meta_history_limit", 64) or 64
        if len(self.state.meta_history) > limit:
            del self.state.meta_history[:-limit]

    # ---------------- Autoevolução ---------------- #

    def run_auto_evolution_cycle(
        self,
        domains: Optional[Iterable[str]] = None,
        *,
        max_patches: Optional[int] = None,
        apply_changes: bool = False,
        source: str = "cli",
    ) -> List[EvolutionPatch]:
        """
        Executa uma rodada de autoevolução agregando patches por domínio.
        """
        normalized = _normalize_domains(domains)
        patches: List[EvolutionPatch] = []

        if "intent" in normalized and self.config.auto_evolution.enable_intent:
            patches.extend(self._suggest_intent_patches())
        if "rules" in normalized:
            patches.extend(self._suggest_rule_patches())
        if "semantics" in normalized or "language" in normalized:
            patches.extend(self._suggest_semantic_patches())
        if "semantic_frames" in normalized:
            patches.extend(self._suggest_semantic_frame_patches())
        if "meta_calculus" in normalized:
            patches.extend(self._suggest_meta_calculus_patches())

        if max_patches is not None and len(patches) > max_patches:
            patches = patches[:max_patches]

        for patch in patches:
            patch.meta.setdefault("source", source)

        if apply_changes:
            for patch in patches:
                patch.apply()

        return patches

    def _suggest_intent_patches(self) -> List[EvolutionPatch]:
        limit = self.config.auto_evolution.max_new_intent_rules
        return suggest_intent_patches(max_candidates=limit)

    def _suggest_meta_calculus_patches(self) -> List[EvolutionPatch]:
        return suggest_meta_calculus_patches(
            max_mismatches=self.config.auto_evolution.max_new_calculus_rules
        )

    def _suggest_rule_patches(self, max_rules: Optional[int] = None) -> List[EvolutionPatch]:
        generator = RulePatchGenerator()
        candidates = generator.generate_patches(max_rules=max_rules or 20)
        patches: List[EvolutionPatch] = []
        for cand in candidates:
            patches.append(
                EvolutionPatch(
                    domain="rules",
                    title=cand.title,
                    description=cand.description,
                    diff=cand.diff,
                    meta={"source": "MetaKernel._suggest_rule_patches"},
                )
            )
        return patches

    def _suggest_semantic_patches(self, max_groups: Optional[int] = None) -> List[EvolutionPatch]:
        generator = SemanticPatchGenerator()
        candidates = generator.generate_patches(max_groups=max_groups or 20)
        patches: List[EvolutionPatch] = []
        for cand in candidates:
            patches.append(
                EvolutionPatch(
                    domain="semantics",
                    title=cand.title,
                    description=cand.description,
                    diff=cand.diff,
                    meta={"source": "MetaKernel._suggest_semantic_patches"},
                )
            )
        return patches

    def _suggest_semantic_frame_patches(self) -> List[EvolutionPatch]:
        return suggest_frame_patches()


def _normalize_domains(domains: Optional[Iterable[str]]) -> List[str]:
    allowed = [
        "intent",
        "rules",
        "semantics",
        "language",
        "semantic_frames",
        "meta_calculus",
        "calculus",
        "all",
    ]
    if domains is None:
        return ["intent", "meta_calculus"]
    normalized: List[str] = []
    for domain in domains:
        if domain is None:
            continue
        clean = domain.strip().lower()
        if clean not in allowed:
            raise ValueError(f"Domínio desconhecido: {domain}")
        if clean == "all":
            return ["intent", "rules", "semantics", "semantic_frames", "meta_calculus"]
        if clean == "language":
            clean = "semantics"
        normalized.append("meta_calculus" if clean == "calculus" else clean)
    return normalized or ["intent", "meta_calculus"]


__all__ = ["MetaKernel", "MetaKernelConfig", "AutoEvolutionConfig", "MetaKernelTurnResult"]


def _calc_result_to_dict(calc_result: "MetaCalculationResult") -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "plan_route": calc_result.plan.route.value,
        "plan_description": calc_result.plan.description,
        "consistent": calc_result.consistent,
        "error": calc_result.error or "",
    }
    if calc_result.answer is not None:
        payload["answer"] = to_json(calc_result.answer)
    if calc_result.snapshot is not None:
        payload["snapshot"] = calc_result.snapshot
    if calc_result.code_summary is not None:
        payload["code_summary"] = json.loads(to_json(calc_result.code_summary))
    return payload
