"""
MetaKernel central do Metanúcleo — orquestra runtime e autoevolução.
"""

from __future__ import annotations

import json

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, TYPE_CHECKING
from time import perf_counter
from datetime import datetime, timezone

from liu import to_json
from nsr import SessionCtx, run_text_full, meta_summary_to_dict

from metanucleus.core.sandbox import MetaSandbox
from metanucleus.core.state import MetaState
from metanucleus.evolution.intent_auto_patch import suggest_intent_patches
from metanucleus.evolution.meta_calculus_auto_patch import suggest_meta_calculus_patches
from metanucleus.evolution.meta_calculus_mismatch_log import configure_meta_calculus_log_limit
from metanucleus.evolution.rule_patch_generator import RulePatchGenerator
from metanucleus.evolution.semantic_frames_auto_patch import suggest_frame_patches
from metanucleus.evolution.semantic_patch_generator import SemanticPatchGenerator
from metanucleus.evolution.types import EvolutionPatch
from metanucleus.evolution.intent_mismatch_log import (
    INTENT_MISMATCH_LOG_PATH,
    configure_intent_log_limit,
)
from metanucleus.evolution.rule_mismatch_log import (
    RULE_MISMATCH_LOG_PATH,
    configure_rule_log_limit,
)
from metanucleus.evolution.semantic_mismatch_log import (
    SEMANTIC_MISMATCH_LOG_PATH,
    configure_semantic_log_limit,
)
from metanucleus.utils.project import get_project_root

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
    log_limit: int | None = 500
    log_rotation_limit: int | None = 5000


@dataclass(slots=True)
class MetaKernelConfig:
    auto_evolution: AutoEvolutionConfig = field(default_factory=AutoEvolutionConfig)


@dataclass(slots=True)
class AutoEvolutionFilters:
    log_since: Optional[datetime] = None
    frame_languages: Optional[Set[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_since": self.log_since.isoformat() if self.log_since else None,
            "frame_languages": sorted(self.frame_languages) if self.frame_languages else [],
        }


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
    last_evolution_stats: List[Dict[str, str]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        rotation_limit = self.config.auto_evolution.log_rotation_limit
        configure_intent_log_limit(rotation_limit)
        configure_rule_log_limit(rotation_limit)
        configure_semantic_log_limit(rotation_limit)
        configure_meta_calculus_log_limit(rotation_limit)

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
        filters: Optional[AutoEvolutionFilters] = None,
    ) -> List[EvolutionPatch]:
        """
        Executa uma rodada de autoevolução agregando patches por domínio.
        """
        normalized = _normalize_domains(domains)
        patches: List[EvolutionPatch] = []
        self.last_evolution_stats = []
        filters = filters or AutoEvolutionFilters()

        def record(
            domain: str,
            status: str,
            reason: str = "",
            start_time: float | None = None,
            entries_scanned: Optional[int] = None,
        ) -> None:
            duration_ms = None
            if start_time is not None:
                duration_ms = round((perf_counter() - start_time) * 1000, 2)
            self.last_evolution_stats.append(
                {k: v for k, v in {
                    "domain": domain,
                    "status": status,
                    "reason": reason,
                    "duration_ms": duration_ms,
                    "entries_scanned": entries_scanned,
                }.items() if v not in (None, "")}
            )

        def remaining_capacity() -> Optional[int]:
            if max_patches is None:
                return None
            return max(0, max_patches - len(patches))

        log_limit = self.config.auto_evolution.log_limit
        log_since = filters.log_since
        meta_types: List[str] = []
        if "semantic_frames" in normalized:
            meta_types.append("frame_mismatch")
        if "meta_calculus" in normalized and self.config.auto_evolution.enable_calculus:
            meta_types.append("calc_rule_mismatch")
        meta_records: Dict[str, List[Dict[str, Any]]] = {}
        meta_counts: Dict[str, int] = {}
        if meta_types:
            meta_records, meta_counts = _load_meta_mismatch_records(
                meta_types,
                log_limit,
                since=log_since,
                frame_languages=filters.frame_languages,
            )

        if "intent" in normalized:
            start = perf_counter()
            if not self.config.auto_evolution.enable_intent:
                record("intent", "disabled", "config flag disabled", start)
            else:
                available = remaining_capacity()
                if available is not None and available <= 0:
                    record("intent", "skipped", "max patches reached", start)
                elif not _log_has_entries(INTENT_MISMATCH_LOG_PATH):
                    record("intent", "skipped", "no intent mismatches", start, entries_scanned=0)
                else:
                    intent_entries = _count_log_entries(INTENT_MISMATCH_LOG_PATH, log_limit, log_since)
                    limit = self.config.auto_evolution.max_new_intent_rules
                    if available is not None:
                        limit = min(limit, available)
                    if limit <= 0:
                        record("intent", "skipped", "max patches reached", start, entries_scanned=intent_entries)
                    else:
                        new_patches, processed_count = self._suggest_intent_patches(
                            max_candidates=limit,
                            log_limit=log_limit,
                            log_since=log_since,
                        )
                        patches.extend(new_patches)
                        record(
                            "intent",
                            "executed",
                            f"{len(new_patches)} patch(es)",
                            start,
                            entries_scanned=processed_count or intent_entries,
                        )

        if "rules" in normalized:
            start = perf_counter()
            available = remaining_capacity()
            if available is not None and available <= 0:
                record("rules", "skipped", "max patches reached", start)
            elif not _log_has_entries(RULE_MISMATCH_LOG_PATH):
                record("rules", "skipped", "no rule mismatches", start, entries_scanned=0)
            else:
                rule_entries = _count_log_entries(RULE_MISMATCH_LOG_PATH, log_limit, log_since)
                new_patches, processed_rules = self._suggest_rule_patches(
                    max_rules=available,
                    log_since=log_since,
                )
                patches.extend(new_patches)
                record(
                    "rules",
                    "executed",
                    f"{len(new_patches)} patch(es)",
                    start,
                    entries_scanned=processed_rules or rule_entries,
                )

        if "semantics" in normalized or "language" in normalized:
            start = perf_counter()
            available = remaining_capacity()
            if available is not None and available <= 0:
                record("semantics", "skipped", "max patches reached", start)
            elif not _log_has_entries(SEMANTIC_MISMATCH_LOG_PATH):
                record("semantics", "skipped", "no semantic mismatches", start, entries_scanned=0)
            else:
                semantic_entries = _count_log_entries(SEMANTIC_MISMATCH_LOG_PATH, log_limit, log_since)
                new_patches, processed_semantics = self._suggest_semantic_patches(
                    max_groups=available,
                    log_since=log_since,
                )
                patches.extend(new_patches)
                record(
                    "semantics",
                    "executed",
                    f"{len(new_patches)} patch(es)",
                    start,
                    entries_scanned=processed_semantics or semantic_entries,
                )

        if "semantic_frames" in normalized:
            start = perf_counter()
            available = remaining_capacity()
            if available is not None and available <= 0:
                record("semantic_frames", "skipped", "max patches reached", start)
            else:
                frame_records = meta_records.get("frame_mismatch", [])
                if not frame_records:
                    record("semantic_frames", "skipped", "no frame mismatches", start, entries_scanned=meta_counts.get("frame_mismatch"))
                else:
                    new_patches = self._suggest_semantic_frame_patches(records=frame_records)
                    patches.extend(new_patches)
                    record(
                        "semantic_frames",
                        "executed",
                        f"{len(new_patches)} patch(es)",
                        start,
                        entries_scanned=meta_counts.get("frame_mismatch"),
                    )

        if "meta_calculus" in normalized:
            start = perf_counter()
            if not self.config.auto_evolution.enable_calculus:
                record("meta_calculus", "disabled", "config flag disabled", start)
            else:
                available = remaining_capacity()
                if available is not None and available <= 0:
                    record("meta_calculus", "skipped", "max patches reached", start)
                else:
                    calc_records = meta_records.get("calc_rule_mismatch", [])
                    if not calc_records:
                        record(
                            "meta_calculus",
                            "skipped",
                            "no calc_rule mismatches",
                            start,
                            entries_scanned=meta_counts.get("calc_rule_mismatch"),
                        )
                    else:
                        new_patches = self._suggest_meta_calculus_patches(records=calc_records)
                        patches.extend(new_patches)
                        record(
                            "meta_calculus",
                            "executed",
                            f"{len(new_patches)} patch(es)",
                            start,
                            entries_scanned=meta_counts.get("calc_rule_mismatch"),
                        )

        if max_patches is not None and len(patches) > max_patches:
            patches = patches[:max_patches]

        for patch in patches:
            patch.meta.setdefault("source", source)

        if apply_changes:
            for patch in patches:
                patch.apply()

        return patches

    def _suggest_intent_patches(
        self,
        max_candidates: Optional[int] = None,
        log_limit: Optional[int] = None,
        log_since: Optional[datetime] = None,
    ) -> Tuple[List[EvolutionPatch], int]:
        limit = max_candidates or self.config.auto_evolution.max_new_intent_rules
        effective_log_limit = log_limit if log_limit is not None else self.config.auto_evolution.log_limit
        return suggest_intent_patches(
            max_candidates=limit,
            log_limit=effective_log_limit,
            log_since=log_since,
        )

    def _suggest_meta_calculus_patches(
        self,
        records: Optional[List[Dict[str, Any]]] = None,
    ) -> List[EvolutionPatch]:
        return suggest_meta_calculus_patches(
            max_mismatches=self.config.auto_evolution.max_new_calculus_rules,
            records=records,
        )

    def _suggest_rule_patches(
        self,
        max_rules: Optional[int] = None,
        log_since: Optional[datetime] = None,
    ) -> Tuple[List[EvolutionPatch], int]:
        generator = RulePatchGenerator(
            log_limit=self.config.auto_evolution.log_limit,
            log_since=log_since,
        )
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
        return patches, generator.processed_entries

    def _suggest_semantic_patches(
        self,
        max_groups: Optional[int] = None,
        log_since: Optional[datetime] = None,
    ) -> Tuple[List[EvolutionPatch], int]:
        generator = SemanticPatchGenerator(
            log_limit=self.config.auto_evolution.log_limit,
            log_since=log_since,
        )
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
        return patches, generator.processed_entries

    def _suggest_semantic_frame_patches(
        self,
        records: Optional[List[Dict[str, Any]]] = None,
    ) -> List[EvolutionPatch]:
        return suggest_frame_patches(records=records)


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


__all__ = ["MetaKernel", "MetaKernelConfig", "AutoEvolutionConfig", "MetaKernelTurnResult", "AutoEvolutionFilters"]


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


_PROJECT_ROOT = get_project_root(Path(__file__))
_META_MISMATCH_LOG_PATH = _PROJECT_ROOT / ".metanucleus" / "mismatch_log.jsonl"


def _log_has_entries(path: Path) -> bool:
    try:
        return path.exists() and path.stat().st_size > 0
    except OSError:
        return False


def _count_log_entries(path: Path, limit: Optional[int], since: Optional[datetime] = None) -> int:
    if not path.exists():
        return 0
    count = 0
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                if since is not None:
                    try:
                        data = json.loads(line)
                        ts = _parse_timestamp(data.get("timestamp"))
                        if ts is not None and ts < since:
                            continue
                    except json.JSONDecodeError:
                        pass
                count += 1
                if limit is not None and count >= limit:
                    break
    except OSError:
        return 0
    return count


def _parse_timestamp(value: object) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def _load_meta_mismatch_records(
    types: Iterable[str],
    limit: Optional[int],
    since: Optional[datetime] = None,
    frame_languages: Optional[Set[str]] = None,
) -> tuple[Dict[str, List[Dict[str, Any]]], Dict[str, int]]:
    unique_types = list(dict.fromkeys(types))
    records: Dict[str, List[Dict[str, Any]]] = {kind: [] for kind in unique_types}
    counts: Dict[str, int] = {kind: 0 for kind in unique_types}
    if not unique_types or not _META_MISMATCH_LOG_PATH.exists():
        return records, counts
    normalized_frame_langs = {code.lower() for code in frame_languages} if frame_languages else None

    remaining: Dict[str, Optional[int]] = {
        kind: (limit if limit is not None else None) for kind in unique_types
    }
    fulfilled = set()

    with _META_MISMATCH_LOG_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = record.get("type")
            if kind not in records:
                continue
            if since is not None:
                ts = _parse_timestamp(record.get("timestamp"))
                if ts is not None and ts < since:
                    continue
            if kind == "frame_mismatch" and normalized_frame_langs:
                lang = str(record.get("language") or "").lower()
                if lang not in normalized_frame_langs:
                    continue
            bucket = records[kind]
            bucket.append(record)
            counts[kind] += 1
            cap = remaining[kind]
            if cap is not None:
                cap -= 1
                remaining[kind] = cap
                if cap <= 0:
                    fulfilled.add(kind)
                    if len(fulfilled) == len(unique_types):
                        break
    return records, counts
