"""
MetaKernel central do Metanúcleo — orquestra runtime e autoevolução.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, TYPE_CHECKING

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
