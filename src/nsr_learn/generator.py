"""
Gerador de Texto via Composição: Produção de Linguagem Sem Pesos Neurais.

LLMs geram texto token por token usando distribuições de probabilidade
derivadas de pesos aprendidos. Nós geramos texto através de:

1. SELEÇÃO: Escolha de templates/fragmentos baseada em contexto
2. COMPOSIÇÃO: Montagem de fragmentos em estruturas coerentes
3. SUBSTITUIÇÃO: Preenchimento de slots com valores apropriados
4. REFINAMENTO: Ajuste de concordância e coesão

Inspiração:
- Gramáticas de atributos (Knuth)
- Systemic Functional Grammar (Halliday)
- Template-based NLG (clássico)
- Markov chains (para fluência local)

A geração é DETERMINÍSTICA e AUDITÁVEL:
- Cada decisão pode ser rastreada
- Não há "alucinação" - só templates e regras
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, FrozenSet, Iterator, List, Mapping, Set, Tuple
import random
import re


class FragmentType(Enum):
    """Tipos de fragmentos de texto."""
    
    SUBJECT = auto()  # Sujeito
    PREDICATE = auto()  # Predicado
    OBJECT = auto()  # Objeto
    MODIFIER = auto()  # Modificador
    CONNECTOR = auto()  # Conector
    TEMPLATE = auto()  # Template completo


@dataclass(frozen=True, slots=True)
class TextFragment:
    """Um fragmento de texto com metadados."""
    
    text: str
    fragment_type: FragmentType
    tags: FrozenSet[str] = frozenset()
    slots: Tuple[str, ...] = ()  # Ex: {SUBJECT}, {OBJECT}
    
    def has_slot(self, slot_name: str) -> bool:
        return f"{{{slot_name}}}" in self.text
    
    def fill_slot(self, slot_name: str, value: str) -> "TextFragment":
        new_text = self.text.replace(f"{{{slot_name}}}", value)
        new_slots = tuple(s for s in self.slots if s != slot_name)
        return TextFragment(
            text=new_text,
            fragment_type=self.fragment_type,
            tags=self.tags,
            slots=new_slots,
        )
    
    def fill_all(self, values: Mapping[str, str]) -> str:
        result = self.text
        for slot, value in values.items():
            result = result.replace(f"{{{slot}}}", value)
        return result


@dataclass
class TextPlan:
    """Plano de geração de texto."""
    
    goal: str
    fragments: List[TextFragment] = field(default_factory=list)
    bindings: Dict[str, str] = field(default_factory=dict)
    
    def add_fragment(self, fragment: TextFragment) -> None:
        self.fragments.append(fragment)
    
    def bind(self, slot: str, value: str) -> None:
        self.bindings[slot] = value
    
    def realize(self) -> str:
        """Realiza o plano em texto."""
        parts = []
        
        for fragment in self.fragments:
            text = fragment.fill_all(self.bindings)
            parts.append(text)
        
        return " ".join(parts)


@dataclass
class Template:
    """Template de texto com slots e condições."""
    
    name: str
    pattern: str
    slots: List[str]
    required_tags: Set[str] = field(default_factory=set)
    examples: List[str] = field(default_factory=list)
    
    def matches_context(self, context_tags: Set[str]) -> bool:
        return self.required_tags.issubset(context_tags)
    
    def instantiate(self, bindings: Mapping[str, str]) -> str:
        result = self.pattern
        for slot, value in bindings.items():
            result = result.replace(f"{{{slot}}}", value)
        return result
    
    def missing_slots(self, bindings: Mapping[str, str]) -> List[str]:
        return [s for s in self.slots if s not in bindings]


class MarkovComposer:
    """
    Compositor baseado em Markov para fluência local.
    
    Não usa pesos - usa contagens discretas de transições.
    """
    
    def __init__(self, order: int = 2):
        self.order = order
        self.transitions: Dict[Tuple[str, ...], Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.starts: Dict[Tuple[str, ...], int] = defaultdict(int)
    
    def learn(self, sentences: List[str]) -> None:
        """Aprende transições de um corpus."""
        for sentence in sentences:
            words = sentence.split()
            
            if len(words) <= self.order:
                continue
            
            # Registra início
            start = tuple(words[:self.order])
            self.starts[start] += 1
            
            # Registra transições
            for i in range(len(words) - self.order):
                context = tuple(words[i:i + self.order])
                next_word = words[i + self.order]
                self.transitions[context][next_word] += 1
    
    def complete(self, prefix: str, max_words: int = 10) -> str:
        """Completa um prefixo usando transições aprendidas."""
        words = prefix.split()
        
        if len(words) < self.order:
            return prefix
        
        result = list(words)
        
        for _ in range(max_words):
            context = tuple(result[-self.order:])
            
            if context not in self.transitions:
                break
            
            candidates = self.transitions[context]
            
            if not candidates:
                break
            
            # Escolhe próxima palavra por frequência (determinístico: pega a mais frequente)
            next_word = max(candidates.items(), key=lambda x: (x[1], x[0]))[0]
            result.append(next_word)
            
            # Para em pontuação final
            if next_word.endswith((".", "!", "?")):
                break
        
        return " ".join(result)
    
    def generate(self, max_words: int = 15) -> str:
        """Gera sentença do início."""
        if not self.starts:
            return ""
        
        # Começa com o início mais comum
        start = max(self.starts.items(), key=lambda x: (x[1], x[0]))[0]
        return self.complete(" ".join(start), max_words)


class FragmentLibrary:
    """Biblioteca de fragmentos de texto organizados."""
    
    def __init__(self):
        self.fragments: Dict[FragmentType, List[TextFragment]] = defaultdict(list)
        self.by_tag: Dict[str, List[TextFragment]] = defaultdict(list)
    
    def add(self, fragment: TextFragment) -> None:
        self.fragments[fragment.fragment_type].append(fragment)
        for tag in fragment.tags:
            self.by_tag[tag].append(fragment)
    
    def get_by_type(self, ftype: FragmentType) -> List[TextFragment]:
        return self.fragments.get(ftype, [])
    
    def get_by_tag(self, tag: str) -> List[TextFragment]:
        return self.by_tag.get(tag, [])
    
    def find_matching(
        self,
        required_type: FragmentType | None = None,
        required_tags: Set[str] | None = None,
    ) -> List[TextFragment]:
        """Encontra fragmentos que correspondem aos critérios."""
        candidates = []
        
        if required_type is not None:
            candidates = list(self.fragments.get(required_type, []))
        else:
            for frags in self.fragments.values():
                candidates.extend(frags)
        
        if required_tags:
            candidates = [
                f for f in candidates
                if required_tags.issubset(f.tags)
            ]
        
        return candidates


class TextGenerator:
    """
    Gerador de texto simbólico principal.
    
    Combina:
    - Templates estruturados
    - Biblioteca de fragmentos
    - Compositor Markov para fluência
    - Sistema de slots e bindings
    """
    
    def __init__(self):
        self.templates: Dict[str, Template] = {}
        self.library = FragmentLibrary()
        self.composer = MarkovComposer(order=2)
        self.default_bindings: Dict[str, str] = {}
    
    def add_template(self, template: Template) -> None:
        self.templates[template.name] = template
    
    def add_fragment(self, fragment: TextFragment) -> None:
        self.library.add(fragment)
    
    def train_composer(self, sentences: List[str]) -> None:
        self.composer.learn(sentences)
    
    def set_default(self, slot: str, value: str) -> None:
        self.default_bindings[slot] = value
    
    def generate_from_template(
        self,
        template_name: str,
        bindings: Dict[str, str] | None = None,
        context_tags: Set[str] | None = None,
    ) -> str:
        """Gera texto a partir de um template."""
        template = self.templates.get(template_name)
        
        if template is None:
            return f"[Template '{template_name}' não encontrado]"
        
        if context_tags and not template.matches_context(context_tags):
            return f"[Template '{template_name}' não aplicável ao contexto]"
        
        # Combina bindings
        all_bindings = dict(self.default_bindings)
        if bindings:
            all_bindings.update(bindings)
        
        # Verifica slots faltantes
        missing = template.missing_slots(all_bindings)
        
        if missing:
            # Tenta preencher com fragmentos da biblioteca
            for slot in missing:
                fragment = self._find_fragment_for_slot(slot, context_tags or set())
                if fragment:
                    all_bindings[slot] = fragment.text
        
        return template.instantiate(all_bindings)
    
    def generate_response(
        self,
        topic: str,
        context_tags: Set[str] | None = None,
        style: str = "neutral",
    ) -> str:
        """
        Gera resposta sobre um tópico.
        
        Usa templates, fragmentos e composição Markov.
        """
        tags = context_tags or set()
        tags.add(style)
        
        # Busca template apropriado
        matching_templates = [
            t for t in self.templates.values()
            if t.matches_context(tags)
        ]
        
        if matching_templates:
            # Usa o primeiro template que corresponde
            template = matching_templates[0]
            bindings = {"TOPIC": topic}
            
            return self.generate_from_template(
                template.name,
                bindings,
                tags,
            )
        
        # Fallback: composição direta
        return self._compose_response(topic, tags)
    
    def _find_fragment_for_slot(
        self,
        slot: str,
        context_tags: Set[str],
    ) -> TextFragment | None:
        """Encontra fragmento apropriado para um slot."""
        # Mapeia slot para tipo de fragmento
        slot_to_type = {
            "SUBJECT": FragmentType.SUBJECT,
            "PREDICATE": FragmentType.PREDICATE,
            "OBJECT": FragmentType.OBJECT,
            "MODIFIER": FragmentType.MODIFIER,
        }
        
        ftype = slot_to_type.get(slot.upper())
        
        if ftype:
            candidates = self.library.find_matching(ftype, context_tags)
            if candidates:
                # Retorna o primeiro (determinístico)
                return candidates[0]
        
        return None
    
    def _compose_response(
        self,
        topic: str,
        tags: Set[str],
    ) -> str:
        """Compõe resposta usando fragmentos."""
        parts = []
        
        # Adiciona sujeito
        subjects = self.library.find_matching(FragmentType.SUBJECT, tags)
        if subjects:
            parts.append(subjects[0].text)
        else:
            parts.append(topic)
        
        # Adiciona predicado
        predicates = self.library.find_matching(FragmentType.PREDICATE, tags)
        if predicates:
            parts.append(predicates[0].text)
        
        # Adiciona objeto
        objects = self.library.find_matching(FragmentType.OBJECT, tags)
        if objects:
            parts.append(objects[0].text)
        
        result = " ".join(parts)
        
        # Tenta expandir com Markov
        if self.composer.transitions:
            expanded = self.composer.complete(result, max_words=5)
            if len(expanded) > len(result):
                return expanded
        
        return result if result else f"Sobre {topic}."


class DialogueGenerator:
    """
    Gerador de diálogos multi-turno.
    
    Mantém contexto e gera respostas coerentes.
    """
    
    def __init__(self, generator: TextGenerator):
        self.generator = generator
        self.history: List[Tuple[str, str]] = []  # (speaker, utterance)
        self.context_tags: Set[str] = set()
        self.topic: str = ""
    
    def set_topic(self, topic: str) -> None:
        self.topic = topic
        self.context_tags.add(topic.lower())
    
    def add_context(self, *tags: str) -> None:
        self.context_tags.update(tags)
    
    def user_says(self, utterance: str) -> None:
        """Registra fala do usuário."""
        self.history.append(("user", utterance))
        
        # Extrai tags do utterance
        words = utterance.lower().split()
        for word in words:
            if len(word) > 4:
                self.context_tags.add(word)
    
    def respond(self) -> str:
        """Gera resposta do sistema."""
        if not self.history:
            return "Como posso ajudar?"
        
        last_user = self.history[-1][1] if self.history[-1][0] == "user" else ""
        
        # Gera resposta contextual
        response = self.generator.generate_response(
            topic=self.topic or last_user,
            context_tags=self.context_tags,
        )
        
        self.history.append(("system", response))
        return response
    
    def get_history(self) -> str:
        """Retorna histórico formatado."""
        lines = []
        for speaker, utterance in self.history:
            prefix = "Usuário:" if speaker == "user" else "Sistema:"
            lines.append(f"{prefix} {utterance}")
        return "\n".join(lines)


def create_default_generator() -> TextGenerator:
    """Cria gerador com templates e fragmentos padrão."""
    gen = TextGenerator()
    
    # Templates
    gen.add_template(Template(
        name="explanation",
        pattern="{TOPIC} é {DEFINITION}. {ELABORATION}",
        slots=["TOPIC", "DEFINITION", "ELABORATION"],
        required_tags={"explain"},
    ))
    
    gen.add_template(Template(
        name="comparison",
        pattern="{TOPIC_A} é similar a {TOPIC_B} porque {REASON}.",
        slots=["TOPIC_A", "TOPIC_B", "REASON"],
        required_tags={"compare"},
    ))
    
    gen.add_template(Template(
        name="question_answer",
        pattern="Sobre {TOPIC}: {ANSWER}.",
        slots=["TOPIC", "ANSWER"],
        required_tags={"answer"},
    ))
    
    gen.add_template(Template(
        name="neutral_statement",
        pattern="{TOPIC} {PREDICATE} {DETAIL}.",
        slots=["TOPIC", "PREDICATE", "DETAIL"],
        required_tags={"neutral"},
    ))
    
    # Fragmentos
    gen.add_fragment(TextFragment(
        text="é um conceito importante",
        fragment_type=FragmentType.PREDICATE,
        tags=frozenset({"neutral", "academic"}),
    ))
    
    gen.add_fragment(TextFragment(
        text="pode ser entendido como",
        fragment_type=FragmentType.PREDICATE,
        tags=frozenset({"explain", "neutral"}),
    ))
    
    gen.add_fragment(TextFragment(
        text="relaciona-se com",
        fragment_type=FragmentType.PREDICATE,
        tags=frozenset({"neutral", "compare"}),
    ))
    
    gen.add_fragment(TextFragment(
        text="diversos aspectos",
        fragment_type=FragmentType.OBJECT,
        tags=frozenset({"neutral"}),
    ))
    
    gen.add_fragment(TextFragment(
        text="uma perspectiva interessante",
        fragment_type=FragmentType.OBJECT,
        tags=frozenset({"neutral", "academic"}),
    ))
    
    # Treina compositor com frases de exemplo
    example_sentences = [
        "Isso é um exemplo de composição textual.",
        "O sistema gera texto de forma determinística.",
        "Templates são preenchidos com valores apropriados.",
        "A geração de texto segue regras explícitas.",
        "Fragmentos são combinados para formar sentenças.",
    ]
    gen.train_composer(example_sentences)
    
    return gen


__all__ = [
    "FragmentType",
    "TextFragment",
    "TextPlan",
    "Template",
    "MarkovComposer",
    "FragmentLibrary",
    "TextGenerator",
    "DialogueGenerator",
    "create_default_generator",
]
