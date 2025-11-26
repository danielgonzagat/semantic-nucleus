"""Lightweight semantic frame library for the PhiEngine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence


LanguageCode = str


@dataclass()
class SemanticFrame:
    """Describes a symbolic frame with intent hints and lexical patterns."""

    id: str
    label: str
    description: str
    languages: Sequence[LanguageCode] = field(default_factory=lambda: ("pt",))
    patterns: Sequence[str] = field(default_factory=tuple)
    roles: Dict[str, str] = field(default_factory=dict)
    intent_hint: Optional[str] = None
    tags: Sequence[str] = field(default_factory=tuple)


@dataclass()
class FrameMatch:
    frame: SemanticFrame
    score: int

    @property
    def intent(self) -> Optional[str]:
        return self.frame.intent_hint

    @property
    def id(self) -> str:
        return self.frame.id

    @property
    def tags(self) -> Sequence[str]:
        return self.frame.tags


def _frame(
    *,
    id: str,
    label: str,
    description: str,
    patterns: Sequence[str],
    languages: Sequence[str] = ("pt",),
    roles: Optional[Dict[str, str]] = None,
    intent_hint: Optional[str] = None,
    tags: Optional[Sequence[str]] = None,
) -> SemanticFrame:
    return SemanticFrame(
        id=id,
        label=label,
        description=description,
        languages=languages,
        patterns=patterns,
        roles=roles or {},
        intent_hint=intent_hint,
        tags=tuple(tags or ()),
    )


FRAME_LIBRARY: List[SemanticFrame] = [
    _frame(
        id="greeting.basic",
        label="Saudação",
        description="Frases curtas que indicam abertura de diálogo",
        patterns=("oi", "olá", "hey", "hello", "bom dia", "boa tarde", "boa noite", "hi"),
        intent_hint="social_greeting",
        tags=("social", "opening"),
    ),
    _frame(
        id="goodbye.basic",
        label="Despedida",
        description="Encerramento explícito da conversa",
        patterns=("tchau", "até mais", "até logo", "see you", "bye", "goodbye"),
        intent_hint="social_goodbye",
        tags=("social", "closing"),
    ),
    _frame(
        id="social.thanks",
        label="Agradecimento",
        description="Expressões explícitas de gratidão",
        patterns=("obrigado", "obrigada", "valeu", "thanks", "thank you", "i appreciate"),
        intent_hint="social_thanks",
        tags=("social",),
    ),
    _frame(
        id="social.apology",
        label="Pedido de desculpas",
        description="Frases que pedem perdão",
        patterns=("desculpa", "foi mal", "me perdoa", "sorry", "i apologize"),
        intent_hint="social_apology",
        tags=("social",),
    ),
    _frame(
        id="question.definition",
        label="Pergunta de definição",
        description="Pergunta 'o que é' / 'what is'",
        patterns=("o que é", "o que e", "what is", "what does", "define", "me explica"),
        intent_hint="ask_definition",
        tags=("question", "definition"),
        roles={"TOPIC": "conceito ou entidade a ser explicado"},
    ),
    _frame(
        id="question.identity",
        label="Pergunta de identidade",
        description="Pergunta sobre 'quem é'",
        patterns=("quem é", "who is", "quem foi", "who was"),
        intent_hint="ask_identity",
        tags=("question",),
        roles={"TARGET": "entidade cuja identidade é pedida"},
    ),
    _frame(
        id="question.causal",
        label="Pergunta causal",
        description="Frases que buscam motivo/causa explicitamente",
        patterns=("por que", "porque", "qual o motivo", "why", "what causes"),
        intent_hint="ask_cause",
        tags=("question", "causal"),
        roles={"TOPIC": "evento ou afirmação", "REASON": "motivo buscado"},
    ),
    _frame(
        id="question.how",
        label="Pergunta procedural",
        description="Perguntas 'como fazer' ou 'como funciona'",
        patterns=("como eu", "como faz", "como funciona", "how do i", "how does it work"),
        intent_hint="ask_how",
        tags=("question", "procedural"),
    ),
    _frame(
        id="command.create",
        label="Comando de criação",
        description="Pedidos diretos para criar/gerar algo",
        patterns=("cria", "gera", "implementa", "faça", "create", "generate", "implement"),
        intent_hint="command_create",
        tags=("command",),
        roles={"GOAL": "artefato solicitado"},
    ),
    _frame(
        id="command.explain",
        label="Pedido de explicação",
        description="Solicitação explícita para explicar ou detalhar algo",
        patterns=("me explica", "explica melhor", "explain", "tell me more", "detalha"),
        intent_hint="command_explain",
        tags=("command", "explanation"),
    ),
    _frame(
        id="action.physical",
        label="Ação física",
        description="Relatos de quem fez o quê com quem",
        patterns=("bateu", "empurrou", "quebrou", "hit", "pushed", "broke"),
        roles={"AGENT": "quem executa", "PATIENT": "quem recebe", "ACTION": "verbo principal"},
        tags=("event",),
    ),
    _frame(
        id="meta.reasoning",
        label="Meta-raciocínio",
        description="Pedidos para mostrar raciocínio ou estado interno",
        patterns=(
            "como você chegou",
            "passo a passo",
            "me mostra o raciocínio",
            "explain your reasoning",
            "step by step",
        ),
        intent_hint="meta_reasoning",
        tags=("meta",),
    ),
    _frame(
        id="meta.capabilities",
        label="Meta-capacidades",
        description="Perguntas sobre limites ou habilidades do sistema",
        patterns=("você consegue", "qual o seu limite", "are you able", "can you evolve"),
        intent_hint="meta_capability",
        tags=("meta",),
    ),
]


def iter_frames(language: Optional[LanguageCode] = None) -> Iterable[SemanticFrame]:
    """Returns all frames optionally filtered by language."""
    if language is None:
        return FRAME_LIBRARY
    language = language.lower()
    return [frame for frame in FRAME_LIBRARY if any(lang.lower() == language for lang in frame.languages)]


def match_frames(
    text: str,
    language: Optional[LanguageCode] = None,
    limit: int = 5,
) -> List[FrameMatch]:
    """Returns frames whose lexical patterns appear in text."""
    if not text:
        return []

    lowered = text.lower()
    lang = language.lower() if language else None
    matches: List[FrameMatch] = []
    for frame in FRAME_LIBRARY:
        if lang is not None and lang not in {lng.lower() for lng in frame.languages}:
            continue
        score = sum(1 for pattern in frame.patterns if pattern in lowered)
        if score > 0:
            matches.append(FrameMatch(frame=frame, score=score))
    matches.sort(key=lambda item: item.score, reverse=True)
    if limit > 0:
        return matches[:limit]
    return matches
