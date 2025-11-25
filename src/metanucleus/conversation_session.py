"""Conversation session that uses semantic pipeline turn by turn."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .ontology_index import get_global_index
from .semantic_mapper import analyze_text
from .phi_intent import phi_intent, IntentFrame
from .phi_semantics import phi_semantics, SemanticFrame
from .phi_structure import phi_structure, LIUStructure
from .memory import SymbolicMemory


@dataclass
class TurnResult:
    user_text: str
    intent: IntentFrame
    semantics: SemanticFrame
    liu: LIUStructure
    memory_snapshot: Dict[str, Any]


class ConversationSession:
    def __init__(self, memory_size: int = 50) -> None:
        self.idx = get_global_index()
        self.memory = SymbolicMemory(max_entries=memory_size)

    def process_user_message(self, text: str) -> TurnResult:
        parse = analyze_text(text, self.idx)
        intent = phi_intent(parse, self.idx)
        semantics = phi_semantics(parse, self.idx)
        liu = phi_structure(parse, self.idx)

        self.memory.add(
            role="user",
            text=text,
            intent=intent,
            semantics=semantics,
            liu=liu,
        )

        snapshot = self.memory.as_debug_dict()
        return TurnResult(user_text=text, intent=intent, semantics=semantics, liu=liu, memory_snapshot=snapshot)

    def add_core_message(self, text: str) -> None:
        dummy_intent = IntentFrame(label="core_reply", confidence=1.0)
        dummy_semantics = SemanticFrame(label="core_output", confidence=1.0)
        dummy_liu = LIUStructure(fields={"generated": True}, confidence=1.0)
        self.memory.add(role="core", text=text, intent=dummy_intent, semantics=dummy_semantics, liu=dummy_liu)
