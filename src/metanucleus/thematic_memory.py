"""Conversation memory focused on semantic topics."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set


Speaker = str  # "user" | "system"


@dataclass()
class MemoryItem:
    speaker: Speaker
    text: str
    lang: str
    intent: Optional[str]
    frame_id: Optional[str]
    concepts: Set[str]
    meta: Dict[str, float]


@dataclass
class ThematicMemory:
    """Stores the symbolic conversation history."""

    entries: List[MemoryItem] = field(default_factory=list)
    max_entries: int = 200

    def add_turn(
        self,
        *,
        speaker: Speaker,
        text: str,
        lang: str,
        intent: Optional[str],
        frame_id: Optional[str],
        concepts: Sequence[str],
        metrics: Dict[str, float],
    ) -> None:
        entry = MemoryItem(
            speaker=speaker,
            text=text,
            lang=lang,
            intent=intent,
            frame_id=frame_id,
            concepts=set(concepts),
            meta=dict(metrics),
        )
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            overflow = len(self.entries) - self.max_entries
            del self.entries[:overflow]

    def recent(self, limit: int = 5) -> List[MemoryItem]:
        if limit <= 0:
            return list(self.entries)
        return self.entries[-limit:]

    def dominant_concepts(self, min_freq: int = 2) -> Set[str]:
        if not self.entries:
            return set()
        freq: Dict[str, int] = {}
        for entry in self.entries:
            for concept in entry.concepts:
                freq[concept] = freq.get(concept, 0) + 1
        return {concept for concept, count in freq.items() if count >= min_freq}

    def recent_concepts(self, limit: int = 5) -> Set[str]:
        collected: Set[str] = set()
        for entry in self.recent(limit):
            collected.update(entry.concepts)
        return collected

    def short_summary(self, limit: int = 3) -> str:
        if not self.entries:
            return "Memória vazia."
        snippets = []
        for entry in self.recent(limit):
            prefix = "Usuário" if entry.speaker == "user" else "Núcleo"
            snippets.append(f"{prefix}: {entry.text}")
        return "\n".join(snippets)
