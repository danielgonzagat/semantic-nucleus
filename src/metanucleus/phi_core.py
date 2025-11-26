"""High-level symbolic engine that orchestrates intents, semantics, and memory."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .semantic_mapper import analyze_text, SemanticParse
from .semantic_frames import FrameMatch, match_frames
from .semantic_rules import RuleAnalysis, UtteranceView, apply_semantic_rules, build_view
from .meta_calculus import SemanticMetrics, compute_semantic_metrics
from .thematic_memory import ThematicMemory


@dataclass()
class EngineIntent:
    label: str
    confidence: float
    tags: List[str]
    reasons: List[str]


@dataclass()
class EngineTurn:
    text: str
    language: str
    intent: EngineIntent
    frame: Optional[FrameMatch]
    metrics: SemanticMetrics
    response: str


class PhiEngine:
    """Combines all symbolic layers into a minimal but coherent runtime."""

    def __init__(self, default_language: str = "pt") -> None:
        self.default_language = default_language
        self.memory = ThematicMemory()

    # ------------- public API -------------

    def process(self, text: str, language: Optional[str] = None) -> EngineTurn:
        lang = language or self.detect_language(text)
        parse = analyze_text(text, index=None)
        tokens = [token.lower for token in parse.tokens if not token.is_punctuation]

        frame_match = self._select_frame(text, lang)
        utt_view = build_view(text, lang, tokens=tokens)
        rules = apply_semantic_rules(utt_view, frame_match)

        intent = self._combine_intents(parse, frame_match, rules)
        metrics = compute_semantic_metrics(
            parse=parse,
            best_frame=frame_match,
            rule_analysis=rules,
            recent_concepts=self.memory.recent_concepts(),
            dominant_concepts=self.memory.dominant_concepts(),
        )

        response = self._compose_response(text, lang, intent, frame_match, metrics, rules)

        concepts = [hit.token.lower for hit in parse.hits]
        metrics_dict = {
            "surprise": metrics.surprise,
            "redundancy": metrics.redundancy,
            "coherence": metrics.coherence,
            "conceptual_distance": metrics.conceptual_distance,
            "logical_density": metrics.logical_density,
        }
        self.memory.add_turn(
            speaker="user",
            text=text,
            lang=lang,
            intent=intent.label,
            frame_id=frame_match.id if frame_match else None,
            concepts=concepts,
            metrics=metrics_dict,
        )
        self.memory.add_turn(
            speaker="system",
            text=response,
            lang=lang,
            intent="system_answer",
            frame_id=None,
            concepts=[],
            metrics=metrics_dict,
        )

        return EngineTurn(
            text=text,
            language=lang,
            intent=intent,
            frame=frame_match,
            metrics=metrics,
            response=response,
        )

    # ------------- helpers -------------

    def detect_language(self, text: str) -> str:
        lowered = text.lower()
        if any(token in lowered for token in (" you ", " the ", " what ", " how ", "why")):
            return "en"
        return self.default_language

    def _select_frame(self, text: str, language: str) -> Optional[FrameMatch]:
        matches = match_frames(text, language, limit=3)
        return matches[0] if matches else None

    def _combine_intents(
        self,
        parse: SemanticParse,
        frame: Optional[FrameMatch],
        rules: RuleAnalysis,
    ) -> EngineIntent:
        label = parse.intent.label
        reasons = list(parse.intent.reasons)
        tags = list(rules.tags)
        confidence = parse.intent.confidence

        if rules.intent:
            label = rules.intent
            confidence = max(confidence, rules.confidence)
            reasons.append("regra semântica aplicada")

        if frame and frame.intent and confidence < 0.75:
            label = frame.intent
            confidence = max(confidence, 0.7)
            reasons.append(f"frame {frame.id}")

        label = label or "statement"
        return EngineIntent(label=label, confidence=min(0.99, confidence), tags=tags, reasons=reasons)

    def _compose_response(
        self,
        text: str,
        lang: str,
        intent: EngineIntent,
        frame: Optional[FrameMatch],
        metrics: SemanticMetrics,
        rules: RuleAnalysis,
    ) -> str:
        summary = self.memory.short_summary(limit=3)

        if lang == "en":
            return self._response_en(text, intent, frame, metrics, rules, summary)
        return self._response_pt(text, intent, frame, metrics, rules, summary)

    def _response_pt(
        self,
        text: str,
        intent: EngineIntent,
        frame: Optional[FrameMatch],
        metrics: SemanticMetrics,
        rules: RuleAnalysis,
        summary: str,
    ) -> str:
        if intent.label == "social_greeting":
            return "Olá! Estou em modo simbólico determinístico e pronto para continuar."
        if intent.label == "social_thanks":
            return "Disponha. Continuo acompanhando sua intenção e expandindo o núcleo."
        if intent.label == "ask_definition":
            return (
                "Você pediu uma definição. Posso explicar em termos simbólicos, "
                "mas ainda não estou ligado a todo o conteúdo externo. "
                "Em breve conseguirei citar precisão completa."
            )
        if intent.label == "ask_cause":
            return (
                "Detectei uma pergunta causal. Ainda estou montando meu grafo de razões, "
                "mas já reconheço que você busca relacionamento causa-efeito."
            )
        if intent.label.startswith("command"):
            return (
                "Entendido. Comandos simbólicos recebidos. Continuo evoluindo e registrando passos "
                "para chegar na arquitetura completa."
            )
        if intent.label.startswith("meta"):
            return (
                "Você está em modo meta. Registro cada passo do meu raciocínio determinístico "
                "e uso esses dados para evoluir o Metanúcleo."
            )

        frame_info = f"Frame provável: {frame.id}" if frame else "Frame ainda não definido."
        metrics_info = self._format_metrics_pt(metrics)
        return (
            "Entendi sua frase de forma simbólica e registrei na memória.\n"
            f"{frame_info}\n"
            f"Contexto recente:\n{summary}\n"
            f"{metrics_info}"
        )

    def _response_en(
        self,
        text: str,
        intent: EngineIntent,
        frame: Optional[FrameMatch],
        metrics: SemanticMetrics,
        rules: RuleAnalysis,
        summary: str,
    ) -> str:
        if intent.label == "social_greeting":
            return "Hello! Symbolic core is online and ready to continue."
        if intent.label == "social_thanks":
            return "You're welcome. Logging this interaction for future improvements."
        if intent.label == "ask_definition":
            return (
                "You requested a definition. I can explain it symbolically, "
                "although my factual knowledge base is still being assembled."
            )
        if intent.label == "ask_cause":
            return (
                "I recognised a causal question. I'm tracking cause-effect relations "
                "and will surface them as the ontology grows."
            )
        if intent.label.startswith("command"):
            return "Command received. The symbolic planner keeps evolving with each instruction."
        if intent.label.startswith("meta"):
            return "You're inspecting the meta layer. I'm logging reasoning routes deterministically."

        frame_info = f"Frame candidate: {frame.id}" if frame else "No clear frame yet."
        metrics_info = self._format_metrics_en(metrics)
        return (
            "Symbolic interpretation stored.\n"
            f"{frame_info}\n"
            f"Recent context:\n{summary}\n"
            f"{metrics_info}"
        )

    def _format_metrics_pt(self, metrics: SemanticMetrics) -> str:
        return (
            "Metacálculo:\n"
            f"- Surpresa: {metrics.surprise:.2f}\n"
            f"- Redundância: {metrics.redundancy:.2f}\n"
            f"- Coerência: {metrics.coherence:.2f}\n"
            f"- Distância conceitual: {metrics.conceptual_distance:.2f}\n"
            f"- Densidade lógica: {metrics.logical_density:.2f}"
        )

    def _format_metrics_en(self, metrics: SemanticMetrics) -> str:
        return (
            "Metacalc:\n"
            f"- Surprise: {metrics.surprise:.2f}\n"
            f"- Redundancy: {metrics.redundancy:.2f}\n"
            f"- Coherence: {metrics.coherence:.2f}\n"
            f"- Conceptual distance: {metrics.conceptual_distance:.2f}\n"
            f"- Logical density: {metrics.logical_density:.2f}"
        )
