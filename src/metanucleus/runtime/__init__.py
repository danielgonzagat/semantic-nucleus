"Runtime determinístico do Metanúcleo."

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional
from uuid import uuid4

from metanucleus.kernel.meta_kernel import MetaKernel, MetaKernelTurnResult
from metanucleus.semantics.frames import Role, RoleAssignment, SemanticFrame

from .meta_runtime import MetaRuntime

__all__ = ["MetaRuntime", "MetanucleusRuntime", "MetanucleusSession"]


def _detect_language(text: str) -> str:
    lowered = text.lower()
    pt_hints = {"oi", "olá", "tchau", "carro", "muro", "rápido", "quero"}
    if any(token in lowered for token in pt_hints):
        return "pt"
    return "en"


def _detect_intent(text: str) -> str:
    stripped = text.strip().lower()
    if not stripped:
        return "unknown"
    if stripped.endswith("?"):
        return "question"
    if any(token in stripped for token in {"summarize", "resuma", "quero", "please"}):
        return "command"
    if any(token in stripped for token in {"oi", "olá", "hello", "hi"}):
        return "greeting"
    return "statement"


def _infer_frame(text: str, lang: str) -> Optional[SemanticFrame]:
    lowered = text.lower()
    if lang == "pt" and "carro" in lowered and "muro" in lowered:
        return SemanticFrame(
            predicate="bater",
            roles=[
                RoleAssignment(role=Role("AGENT"), text="carro"),
                RoleAssignment(role=Role("PATIENT"), text="parede"),
            ],
        )
    if lang == "en" and "car" in lowered and "wall" in lowered:
        return SemanticFrame(
            predicate="hit",
            roles=[
                RoleAssignment(role=Role("AGENT"), text="car"),
                RoleAssignment(role=Role("PATIENT"), text="barrier"),
            ],
        )
    return None


@dataclass
class MetanucleusSession:
    session_id: str
    kernel: MetaKernel = field(default_factory=MetaKernel.bootstrap)

    def ask(self, text: str) -> str:
        return self.ask_full(text).answer_text

    def ask_full(self, text: str) -> MetaKernelTurnResult:
        return self.kernel.handle_turn(user_text=text, session_id=self.session_id)

    def analyze(self, text: str) -> Dict[str, object]:
        lang = _detect_language(text)
        intent = _detect_intent(text)
        frame = _infer_frame(text, lang)
        return {"language": lang, "intent": intent, "frame": frame}

    def normalize_expr(self, expr: str, rule_hint: Optional[str] = None) -> str:
        return expr.strip()


class MetanucleusRuntime:
    def __init__(self) -> None:
        self._counter = 0

    def new_session(self) -> MetanucleusSession:
        self._counter += 1
        session_id = f"session-{self._counter}-{uuid4().hex[:6]}"
        return MetanucleusSession(session_id=session_id)
