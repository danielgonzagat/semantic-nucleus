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
            if _pattern_matches(str(pattern).lower(), text_lower):
                frame_type = "event"
                if label and "definition" in label:
                    frame_type = "definition_request"
                elif label and "communication" in label:
                    frame_type = "communication"
                roles: Dict[str, str] = {}
                if frame_type == "definition_request":
                    topic = _extract_topic_from_definition(text_lower)
                    if topic:
                        roles["TOPIC"] = topic
                        signals.append(f"TOPIC={topic}")
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


def _pattern_matches(pattern: str, text: str) -> bool:
    words = [word for word in pattern.split() if word]
    return all(word in text for word in words)


def _extract_topic_from_definition(text: str) -> Optional[str]:
    for trigger in ["o que é", "o que e", "me explique", "me explica"]:
        if trigger in text:
            return text.split(trigger, 1)[-1].strip(" ?!.")
    return None
