"""
MetaKernel central do Metanúcleo — orquestra runtime e autoevolução.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from metanucleus.core.sandbox import MetaSandbox
from metanucleus.core.state import MetaState
from metanucleus.evolution.intent_patch_generator import IntentLexiconPatchGenerator
from metanucleus.evolution.meta_calculus_patch_generator import MetaCalculusPatchGenerator

if TYPE_CHECKING:
    from metanucleus.runtime.meta_runtime import MetaRuntime


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
class EvolutionPatch:
    type: str
    diff: str
    title: str
    description: str
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MetaKernelTurnResult:
    answer_text: str
    answer_struct: Any | None = None
    suggested_patches: List[EvolutionPatch] = field(default_factory=list)
    debug_info: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# MetaKernel
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class MetaKernel:
    state: MetaState = field(default_factory=MetaState)
    config: MetaKernelConfig = field(default_factory=MetaKernelConfig)

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

        answer_text, answer_struct, debug = self._run_symbolic_pipeline(user_text=user_text)
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
        )

    def _run_symbolic_pipeline(self, user_text: str) -> tuple[str, Any | None, Dict[str, Any]]:
        answer = f"[ECO] {user_text}"
        debug_info: Dict[str, Any] = {
            "note": "MetaKernel._run_symbolic_pipeline ainda é um placeholder determinístico."
        }
        return answer, None, debug_info

    # ---------------- Autoevolução ---------------- #

    def run_auto_evolution_cycle(self, domains: Optional[List[str]] = None) -> List[EvolutionPatch]:
        if domains is None:
            domains = ["intent", "calculus"]

        patches: List[EvolutionPatch] = []
        if "intent" in domains and self.config.auto_evolution.enable_intent:
            patches.extend(self._suggest_intent_patches())
        if "calculus" in domains and self.config.auto_evolution.enable_calculus:
            patches.extend(self._suggest_calculus_patches())
        return patches

    def _suggest_intent_patches(self) -> List[EvolutionPatch]:
        generator = IntentLexiconPatchGenerator()
        candidates = generator.generate_patches(
            max_candidates=self.config.auto_evolution.max_new_intent_rules
        )
        patches: List[EvolutionPatch] = []
        for cand in candidates:
            patches.append(
                EvolutionPatch(
                    type="intent",
                    diff=cand.diff,
                    title=cand.title,
                    description=cand.description,
                    meta={"source": "MetaKernel._suggest_intent_patches"},
                )
            )
        return patches

    def _suggest_calculus_patches(self) -> List[EvolutionPatch]:
        generator = MetaCalculusPatchGenerator()
        candidates = generator.generate_patches(
            max_new_rules=self.config.auto_evolution.max_new_calculus_rules
        )
        patches: List[EvolutionPatch] = []
        for cand in candidates:
            patches.append(
                EvolutionPatch(
                    type="calculus",
                    diff=cand.diff,
                    title=cand.title,
                    description=cand.description,
                    meta={"source": "MetaKernel._suggest_calculus_patches"},
                )
            )
        return patches


__all__ = ["MetaKernel", "MetaKernelConfig", "AutoEvolutionConfig", "EvolutionPatch", "MetaKernelTurnResult"]
