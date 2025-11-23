"""Sessão de conversa multi-turno para o Metanúcleo."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import itertools
import re
from typing import Dict, List, Optional, Set

from metanucleus.runtime.meta_runtime import MetaRuntime

_WORD_RE = re.compile(r"[a-zA-ZÀ-ÖØ-öø-ÿ0-9_]+", re.UNICODE)
_STOPWORDS = {
    "o",
    "a",
    "os",
    "as",
    "um",
    "uma",
    "de",
    "do",
    "da",
    "e",
    "ou",
    "que",
    "se",
    "the",
    "and",
    "or",
    "is",
    "are",
    "am",
    "to",
    "of",
    "in",
    "on",
    "it",
    "i",
}


def _tokenize(text: str) -> List[str]:
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


def _key_terms(text: str) -> Set[str]:
    return {tok for tok in _tokenize(text) if tok not in _STOPWORDS}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _important(text: str, terms: Set[str], min_tokens: int) -> bool:
    toks = _tokenize(text)
    if len(toks) >= min_tokens:
        return True
    if "?" in text:
        return True
    strong = {"metanúcleo", "meta", "núcleo", "inteligência", "silício"}
    return bool(terms & strong)


@dataclass(slots=True)
class MemoryConfig:
    """Parâmetros de memória/conversação."""

    max_short: int = 8
    max_long: int = 48
    topic_similarity_threshold: float = 0.25
    min_tokens_for_long: int = 10


TurnId = int
TopicId = int


@dataclass(slots=True)
class TurnRecord:
    id: TurnId
    role: str  # "user" / "meta"
    text: str
    created_at: datetime
    topic_id: Optional[TopicId]
    key_terms: Set[str]
    important: bool


@dataclass(slots=True)
class TopicRecord:
    id: TopicId
    title: str
    created_at: datetime
    last_active_at: datetime
    aggregated_terms: Set[str] = field(default_factory=set)


@dataclass(slots=True)
class ConversationState:
    turns: List[TurnRecord] = field(default_factory=list)
    topics: Dict[TopicId, TopicRecord] = field(default_factory=dict)
    active_topic_id: Optional[TopicId] = None
    short_mem: Dict[TopicId, List[TurnId]] = field(default_factory=dict)
    long_mem: List[TurnId] = field(default_factory=list)


class TopicManager:
    def __init__(self, cfg: MemoryConfig):
        self.cfg = cfg
        self._counter = itertools.count(1)

    def assign(self, state: ConversationState, terms: Set[str], hint: str) -> TopicId:
        now = datetime.utcnow()
        if not state.topics:
            tid = next(self._counter)
            state.topics[tid] = TopicRecord(
                id=tid,
                title=hint[:64],
                created_at=now,
                last_active_at=now,
                aggregated_terms=set(terms),
            )
            state.active_topic_id = tid
            return tid

        best_id = None
        best_score = 0.0
        for tid, topic in state.topics.items():
            score = _jaccard(terms, topic.aggregated_terms)
            if score > best_score:
                best_score = score
                best_id = tid

        if best_id is not None and best_score >= self.cfg.topic_similarity_threshold:
            topic = state.topics[best_id]
            topic.aggregated_terms |= terms
            topic.last_active_at = now
            state.active_topic_id = best_id
            return best_id

        tid = next(self._counter)
        state.topics[tid] = TopicRecord(
            id=tid,
            title=hint[:64],
            created_at=now,
            last_active_at=now,
            aggregated_terms=set(terms),
        )
        state.active_topic_id = tid
        return tid


class MemoryManager:
    def __init__(self, cfg: MemoryConfig):
        self.cfg = cfg

    def track(self, state: ConversationState, turn: TurnRecord) -> None:
        if turn.topic_id is not None:
            buf = state.short_mem.setdefault(turn.topic_id, [])
            buf.append(turn.id)
            overflow = len(buf) - self.cfg.max_short
            if overflow > 0:
                del buf[:overflow]

        if turn.important:
            state.long_mem.append(turn.id)
            overflow = len(state.long_mem) - self.cfg.max_long
            if overflow > 0:
                del state.long_mem[:overflow]

    def build_context(self, state: ConversationState) -> str:
        lines: List[str] = []
        if state.long_mem:
            lines.append("# [MEMÓRIA LONGA]")
            for tid in state.long_mem[-self.cfg.max_long :]:
                turn = _find_turn(state, tid)
                if turn:
                    lines.append(f"{turn.role.upper()}: {turn.text}")
            lines.append("")

        active = state.active_topic_id
        if active is not None:
            ids = state.short_mem.get(active, [])
            if ids:
                lines.append("# [MEMÓRIA CURTA]")
                for tid in ids:
                    turn = _find_turn(state, tid)
                    if turn:
                        lines.append(f"{turn.role.upper()}: {turn.text}")
                lines.append("")

        return "\n".join(line for line in lines if line.strip())


def _find_turn(state: ConversationState, turn_id: TurnId) -> Optional[TurnRecord]:
    for turn in state.turns:
        if turn.id == turn_id:
            return turn
    return None


@dataclass
class ConversationSession:
    """Sessão de chat com memória multi-turno."""

    runtime: MetaRuntime
    state: ConversationState = field(default_factory=ConversationState)
    cfg: MemoryConfig = field(default_factory=MemoryConfig)

    def __post_init__(self) -> None:
        self._topics = TopicManager(self.cfg)
        self._memory = MemoryManager(self.cfg)
        self._counter = itertools.count(1)

    def handle_user_message(self, text: str) -> str:
        """Processa mensagem do usuário e retorna a resposta simbólica."""

        turn_user = self._register_turn("user", text)
        context = self._memory.build_context(self.state)
        payload = self._compose_prompt(context, text)
        answer = self.runtime.handle_request(payload)
        self._register_turn("meta", answer, topic_id=turn_user.topic_id)
        return answer

    def _compose_prompt(self, context: str, text: str) -> str:
        if context:
            return f"{context}\n\n# [MENSAGEM ATUAL]\n{text}"
        return text

    def _register_turn(self, role: str, text: str, topic_id: Optional[TopicId] = None) -> TurnRecord:
        terms = _key_terms(text)
        now = datetime.utcnow()
        if role == "user":
            topic_id = self._topics.assign(self.state, terms, text)
        elif topic_id is None:
            topic_id = self.state.active_topic_id

        important = _important(text, terms, self.cfg.min_tokens_for_long)
        turn = TurnRecord(
            id=next(self._counter),
            role=role,
            text=text,
            created_at=now,
            topic_id=topic_id,
            key_terms=terms,
            important=important,
        )
        self.state.turns.append(turn)
        self._memory.track(self.state, turn)
        return turn

    def clear(self) -> None:
        """Reseta o estado da conversa."""

        self.state = ConversationState()
        self._topics = TopicManager(self.cfg)
        self._memory = MemoryManager(self.cfg)
        self._counter = itertools.count(1)


__all__ = [
    "MemoryConfig",
    "ConversationState",
    "ConversationSession",
]
