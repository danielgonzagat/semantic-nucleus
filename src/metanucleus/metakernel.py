"""MetaKernel: orchestrates semantic pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from .ontology_index import get_global_index
from .semantic_mapper import analyze_text, SemanticParse
from .phi_intent import phi_intent, IntentFrame
from .phi_semantics import phi_semantics, SemanticFrame
from .phi_structure import phi_structure, LIUStructure
from .phi_frames import phi_frames, FrameResult
from .phi_calculus import phi_calculus, CalculusResult


@dataclass
class MetaKernelResult:
    text: str
    intent: IntentFrame
    semantics: SemanticFrame
    liu: LIUStructure
    frames: FrameResult
    calculus: CalculusResult
    confidence: float
    debug: Dict[str, Any] = field(default_factory=dict)


def metakernel_process(text: str) -> MetaKernelResult:
    idx = get_global_index()

    parse: SemanticParse = analyze_text(text, idx)
    intent_frame = phi_intent(parse, idx)
    semantic_frame = phi_semantics(parse, idx)
    liu_struct = phi_structure(parse, idx)
    frame_result = phi_frames(parse, idx)
    calc_result = phi_calculus(parse)

    confidences = [intent_frame.confidence, semantic_frame.confidence, liu_struct.confidence, frame_result.confidence]
    if calc_result.kind != "none":
        confidences.append(calc_result.confidence)
    overall = sum(confidences) / len(confidences)

    debug = {
        "num_tokens": len(parse.tokens),
        "num_hits": len(parse.hits),
        "frame_type": frame_result.frame_type,
        "calculus_kind": calc_result.kind,
    }

    return MetaKernelResult(
        text=text,
        intent=intent_frame,
        semantics=semantic_frame,
        liu=liu_struct,
        frames=frame_result,
        calculus=calc_result,
        confidence=overall,
        debug=debug,
    )
