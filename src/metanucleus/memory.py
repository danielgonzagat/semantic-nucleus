"""Symbolic session memory utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from .phi_intent import IntentFrame
from .phi_semantics import SemanticFrame
from .phi_structure import LIUStructure


@dataclass
class MemoryEntry:
    timestamp: str
    role: str
    text: str
    intent: str
    semantics: str
    liu: Dict[str, Any]


@dataclass
class SymbolicMemory:
    entries: List[MemoryEntry] = field(default_factory=list)
    max_entries: int = 50

    def add(
        self,
        role: str,
        text: str,
        intent: IntentFrame,
        semantics: SemanticFrame,
        liu: LIUStructure,
    ) -> None:
        ts = datetime.utcnow().isoformat() + "Z"
        entry = MemoryEntry(
            timestamp=ts,
            role=role,
            text=text,
            intent=intent.label,
            semantics=semantics.label,
            liu=dict(liu.fields),
        )
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries :]

    def last_intents(self, n: int = 5) -> List[str]:
        return [entry.intent for entry in self.entries if entry.role == "user"][-n:]

    def last_texts(self, n: int = 5) -> List[str]:
        return [entry.text for entry in self.entries][-n:]

    def as_debug_dict(self) -> Dict[str, Any]:
        return {
            "size": len(self.entries),
            "last_entries": [
                {
                    "ts": entry.timestamp,
                    "role": entry.role,
                    "intent": entry.intent,
                    "semantics": entry.semantics,
                    "liu": entry.liu,
                    "text": entry.text,
                }
                for entry in self.entries[-5:]
            ],
        }
