from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Dict, Optional, TYPE_CHECKING

from .types import EvolutionPatch
if TYPE_CHECKING:
    from metanucleus.kernel.meta_kernel import AutoEvolutionFilters


def _serialize_patch(patch: EvolutionPatch, applied: bool) -> Dict[str, object]:
    return {
        "domain": patch.domain,
        "title": patch.title,
        "description": patch.description,
        "diff": patch.diff,
        "meta": patch.meta,
        "applied": applied,
    }


def write_auto_evolve_report(
    path: Path,
    *,
    domains: Iterable[str],
    patches: Iterable[EvolutionPatch],
    domain_stats: Iterable[Dict[str, object]],
    filters: Optional["AutoEvolutionFilters"],
    applied: bool,
    source: str,
    max_patches: Optional[int],
    extra: Optional[Dict[str, object]] = None,
) -> None:
    domain_list = list(domains)
    patch_list = list(patches)
    stats_list = list(domain_stats)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "applied_changes": applied,
        "max_patches": max_patches,
        "domains": domain_list,
        "filters": (filters.to_dict() if filters else {}),
        "domain_stats": stats_list,
        "patch_count": len(patch_list),
        "patches": [_serialize_patch(patch, applied) for patch in patch_list],
    }

    if extra:
        payload.update(extra)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


__all__ = ["write_auto_evolve_report"]
