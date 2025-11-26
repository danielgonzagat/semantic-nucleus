"""Φ-FRAMES v2 using configuration + ontological fallback."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import json

from .semantic_mapper import SemanticParse
from .ontology_index import OntologyIndex, get_global_index

FRAMES_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "frames_config.json"


@dataclass
class FrameResult:
    frame_id: Optional[str]
    frame_type: str
    roles: Dict[str, str]
    confidence: float
    signals: List[str] = field(default_factory=list)


def _load_frames_config(path: Path = FRAMES_CONFIG_PATH) -> Dict[str, List[Dict[str, object]]]:
    if not path.exists():
        return {"frames": []}
    return json.loads(path.read_text(encoding="utf-8"))


def phi_frames(parse: SemanticParse, idx: Optional[OntologyIndex] = None) -> FrameResult:
    if idx is None:
        idx = get_global_index()

    cfg = _load_frames_config()
    text_lower = parse.text.lower()
    signals: List[str] = []

    for frame in cfg.get("frames", []):
        fid = frame.get("id")
        label = frame.get("label", fid)
        for pattern in frame.get("patterns", []):
            normalized_pattern = str(pattern).lower()
            span = _locate_span(parse.tokens, normalized_pattern)
            if span or _pattern_matches(normalized_pattern, text_lower):
                frame_type = _infer_frame_type(label)
                roles = _prefill_roles(frame_type, text_lower)
                if span:
                    _populate_roles_from_span(roles, span, parse)
                signals.append(f"match_frame:{fid}:{pattern}")
                return FrameResult(frame_id=fid, frame_type=frame_type, roles=roles, confidence=0.85, signals=signals)

    # fallback heuristics
    roles: Dict[str, str] = {}
    entity_hits = [hit for hit in parse.hits if hit.category_id.startswith("A000")]
    op_hits = [hit for hit in parse.hits if hit.category_id.startswith("A003")]

    if entity_hits:
        roles["AGENT"] = entity_hits[0].token.text
        signals.append(f"AGENT={entity_hits[0].token.text}")
    if len(entity_hits) >= 2:
        patient = entity_hits[-1].token.text
        if roles.get("AGENT") != patient:
            roles["PATIENT"] = patient
            signals.append(f"PATIENT={patient}")
    if op_hits:
        roles["ACTION"] = op_hits[0].token.text
        signals.append(f"ACTION={op_hits[0].token.text}")

    if roles.get("ACTION") and (roles.get("AGENT") or roles.get("PATIENT")):
        frame_type = "event"
        confidence = 0.7 if "AGENT" in roles and "PATIENT" in roles else 0.5
    elif roles.get("AGENT") or roles.get("PATIENT"):
        frame_type = "relation"
        confidence = 0.4
    else:
        frame_type = "unknown"
        confidence = 0.2

    return FrameResult(frame_id=None, frame_type=frame_type, roles=roles, confidence=confidence, signals=signals)


def _prefill_roles(frame_type: str, text_lower: str) -> Dict[str, str]:
    roles: Dict[str, str] = {}
    if frame_type == "definition_request":
        topic = _extract_topic_from_definition(text_lower)
        if topic:
            roles["TOPIC"] = topic
    return roles


def _populate_roles_from_span(roles: Dict[str, str], span: List[int], parse: SemanticParse) -> None:
    tokens = parse.tokens
    surface = " ".join(tokens[i].text for i in span)
    roles.setdefault("ACTION", surface)

    before = _nearest_entity_hit(parse.hits, span[0], direction=-1)
    after = _nearest_entity_hit(parse.hits, span[-1], direction=1)
    if before and "AGENT" not in roles:
        roles["AGENT"] = before.token.text
    if after and "PATIENT" not in roles and (not before or after.token_index != before.token_index):
        roles["PATIENT"] = after.token.text


def _nearest_entity_hit(hits, pivot: int, direction: int):
    ordered = sorted(hits, key=lambda h: h.token_index, reverse=(direction < 0))
    for hit in ordered:
        if not hit.category_id.startswith("A000"):
            continue
        if direction < 0 and hit.token_index < pivot:
            return hit
        if direction > 0 and hit.token_index > pivot:
            return hit
    return None


def _locate_span(tokens, pattern: str) -> Optional[List[int]]:
    pattern_parts = [p for p in pattern.split() if p]
    if not pattern_parts:
        return None
    norms = [t.norm for t in tokens]
    n = len(pattern_parts)
    for i in range(len(tokens) - n + 1):
        if all(norms[i + j] == pattern_parts[j] for j in range(n)):
            return list(range(i, i + n))
    return None


def _infer_frame_type(label: Optional[str]) -> str:
    if not label:
        return "event"
    label_lower = label.lower()
    if "definition" in label_lower:
        return "definition_request"
    if "communication" in label_lower:
        return "communication"
    return "event"


def _pattern_matches(pattern: str, text: str) -> bool:
    words = [word for word in pattern.split() if word]
    return all(word in text for word in words)


def _extract_topic_from_definition(text: str) -> Optional[str]:
    for trigger in ["o que é", "o que e", "me explique", "me explica"]:
        if trigger in text:
            return text.split(trigger, 1)[-1].strip(" ?!.")
    return None
