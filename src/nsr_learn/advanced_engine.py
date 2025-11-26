"""
Motor de Aprendizado Avançado: Integração de Todos os Componentes.

Este é o coração do sistema NSR-Learn avançado.
Integra:

1. COMPRESSÃO MDL: Aprende padrões por minimização de descrição
2. GRAFO DE CO-OCORRÊNCIA: Semântica via relações discretas
3. INDUÇÃO DE REGRAS: Extração de regras explícitas
4. MEMÓRIA ASSOCIATIVA: Storage e retrieval simbólico
5. ANALOGIA: Transferência de conhecimento entre domínios
6. CHAIN OF THOUGHT: Raciocínio multi-step explícito
7. ABSTRAÇÃO: Generalização hierárquica
8. ATENÇÃO: Foco dinâmico sem pesos
9. GERAÇÃO: Produção de texto via composição

O objetivo é aproximar capacidades de LLM com:
- Interpretabilidade total
- Sem pesos neurais
- Sem backpropagation
- Auditabilidade completa
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Mapping, Set, Tuple
import time

# Imports dos módulos NSR-Learn
from .compressor import MDLCompressor
from .graph import CooccurrenceGraph
from .inductor import RuleInductor, SymbolicRule, RuleSet, Condition
from .memory import AssociativeMemory, RetrievalResult
from .analogy import AnalogyEngine, Structure, Analogy
from .reasoning import ChainOfThoughtEngine, KnowledgeBase, ReasoningChain
from .abstraction import Taxonomy, PatternAbstractor, ConceptComposer, create_default_taxonomy
from .attention import SymbolicAttention, MultiHeadSymbolicAttention, AttentionContext
from .generator import TextGenerator, DialogueGenerator, create_default_generator


class ProcessingMode(Enum):
    """Modos de processamento."""
    
    LEARNING = auto()  # Aprendendo de dados
    INFERENCE = auto()  # Fazendo inferências
    DIALOGUE = auto()  # Modo conversacional
    ANALYSIS = auto()  # Analisando input


@dataclass
class AdvancedConfig:
    """Configuração do motor avançado."""
    
    # Compressão
    min_pattern_length: int = 2
    max_pattern_length: int = 10
    
    # Regras
    min_rule_support: int = 2
    min_rule_confidence: float = 0.5
    
    # Atenção
    attention_threshold: float = 0.3
    top_k_attention: int = 10
    
    # Raciocínio
    max_reasoning_steps: int = 15
    min_reasoning_confidence: float = 0.3
    
    # Geração
    max_generation_length: int = 100


@dataclass
class ProcessingResult:
    """Resultado de processamento."""
    
    mode: ProcessingMode
    input_text: str
    output_text: str
    reasoning_chain: ReasoningChain | None = None
    attention_focus: List[str] = field(default_factory=list)
    rules_applied: List[SymbolicRule] = field(default_factory=list)
    analogies_used: List[Analogy] = field(default_factory=list)
    memory_retrievals: List[RetrievalResult] = field(default_factory=list)
    confidence: float = 0.0
    processing_time_ms: float = 0.0
    
    def explain(self) -> str:
        """Gera explicação do processamento."""
        lines = [
            f"=== Resultado do Processamento ===",
            f"Modo: {self.mode.name}",
            f"Input: {self.input_text[:100]}...",
            f"Output: {self.output_text[:200]}...",
            f"Confiança: {self.confidence:.2%}",
            f"Tempo: {self.processing_time_ms:.1f}ms",
            "",
        ]
        
        if self.attention_focus:
            lines.append(f"Foco de Atenção: {', '.join(self.attention_focus[:5])}")
        
        if self.rules_applied:
            lines.append(f"Regras Aplicadas: {len(self.rules_applied)}")
            for rule in self.rules_applied[:3]:
                lines.append(f"  - {rule}")
        
        if self.analogies_used:
            lines.append(f"Analogias: {len(self.analogies_used)}")
            for ana in self.analogies_used[:2]:
                lines.append(f"  - {ana.source_domain} → {ana.target_domain}")
        
        if self.memory_retrievals:
            lines.append(f"Memórias Recuperadas: {len(self.memory_retrievals)}")
        
        if self.reasoning_chain:
            lines.append("")
            lines.append("Cadeia de Raciocínio:")
            lines.append(self.reasoning_chain.trace())
        
        return "\n".join(lines)


class AdvancedLearningEngine:
    """
    Motor de Aprendizado Avançado.
    
    Integra todos os componentes do NSR-Learn para criar
    um sistema de IA simbólica com capacidades avançadas.
    """
    
    def __init__(self, config: AdvancedConfig | None = None):
        self.config = config or AdvancedConfig()
        
        # Componentes principais
        # MDLCompressor usa: min_pattern_freq, min_pattern_length, max_pattern_length, max_dictionary_size
        self.compressor = MDLCompressor(
            min_pattern_length=self.config.min_pattern_length,
            max_pattern_length=self.config.max_pattern_length,
        )
        
        # CooccurrenceGraph é um dataclass, criamos diretamente
        self.graph = CooccurrenceGraph()
        
        # RuleInductor é um dataclass com defaults
        self.inductor = RuleInductor(
            min_support=self.config.min_rule_support,
            min_confidence=self.config.min_rule_confidence,
        )
        
        # AssociativeMemory é um dataclass
        self.memory = AssociativeMemory()
        
        self.analogy = AnalogyEngine()
        
        self.kb = KnowledgeBase()
        self.reasoner = ChainOfThoughtEngine(self.kb)
        
        self.taxonomy = create_default_taxonomy()
        self.pattern_abstractor = PatternAbstractor(self.taxonomy)
        self.composer = ConceptComposer(self.taxonomy)
        
        self.attention = MultiHeadSymbolicAttention()
        
        self.generator = create_default_generator()
        self.dialogue = DialogueGenerator(self.generator)
        
        # Regras aprendidas
        self.learned_rules: RuleSet = RuleSet()
        
        # Estado
        self._trained = False
        self._corpus_size = 0
    
    def train(
        self,
        corpus: List[str],
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """
        Treina o motor em um corpus de texto.
        
        Retorna estatísticas do treinamento.
        """
        start_time = time.time()
        stats = {
            "documents": len(corpus),
            "patterns_learned": 0,
            "rules_induced": 0,
            "concepts_abstracted": 0,
            "training_time_s": 0.0,
        }
        
        if verbose:
            print(f"Iniciando treinamento com {len(corpus)} documentos...")
        
        # 1. Tokeniza corpus
        tokenized = [doc.split() for doc in corpus]
        
        # 2. Treina compressor MDL
        if verbose:
            print("  [1/6] Treinando compressor MDL...")
        
        for doc in corpus:
            tokens = doc.split()
            self.compressor.learn(tokens)
        
        stats["patterns_learned"] = len(self.compressor.dictionary)
        
        # 3. Treina grafo de co-ocorrência
        if verbose:
            print("  [2/6] Construindo grafo de co-ocorrência...")
        
        for tokens in tokenized:
            self.graph.add_document(tokens)
        
        # 4. Induz regras
        if verbose:
            print("  [3/6] Induzindo regras simbólicas...")
        
        # Usa indução a partir de sequências
        self.learned_rules = self.inductor.induce_from_sequences(tokenized)
        stats["rules_induced"] = len(self.learned_rules.rules)
        
        # 5. Treina atenção
        if verbose:
            print("  [4/6] Treinando sistema de atenção...")
        
        self.attention.learn_corpus(tokenized)
        
        # 6. Treina gerador
        if verbose:
            print("  [5/6] Treinando gerador de texto...")
        
        self.generator.train_composer(corpus)
        
        # 7. Popula memória com fatos do corpus
        if verbose:
            print("  [6/6] Populando memória associativa...")
        
        for i, doc in enumerate(corpus[:1000]):  # Limita para performance
            tokens = doc.split()
            if len(tokens) >= 3:
                key = tuple(tokens[:3])
                value = " ".join(tokens[3:]) if len(tokens) > 3 else ""
                self.memory.store(key, value, context=[f"doc_{i}"])
        
        # Finaliza
        self._trained = True
        self._corpus_size = len(corpus)
        
        stats["training_time_s"] = time.time() - start_time
        
        if verbose:
            print(f"Treinamento concluído em {stats['training_time_s']:.2f}s")
            print(f"  Padrões: {stats['patterns_learned']}")
            print(f"  Regras: {stats['rules_induced']}")
        
        return stats
    
    def process(
        self,
        input_text: str,
        mode: ProcessingMode = ProcessingMode.INFERENCE,
        context: Dict[str, Any] | None = None,
    ) -> ProcessingResult:
        """
        Processa input e gera resposta.
        """
        start_time = time.time()
        
        # Tokeniza
        tokens = input_text.split()
        
        # Aplica atenção
        att_context = AttentionContext(query=input_text)
        attention_scores = self.attention.attend(
            tokens, 
            att_context, 
            self.config.top_k_attention
        )
        focus_items = [s.item for s in attention_scores]
        
        # Recupera memórias relevantes
        retrievals = self.memory.retrieve(tokens, top_k=5)
        
        # Busca regras aplicáveis
        applicable_rules = []
        input_lower = input_text.lower()
        for rule in self.learned_rules.rules:
            # Verifica se algum antecedente está presente no input
            for ant in rule.antecedents:
                # ant é um Condition, verifica se os argumentos estão no texto
                if any(arg.lower() in input_lower for arg in ant.args if not arg.startswith("?")):
                    applicable_rules.append(rule)
                    break
        
        # Raciocínio
        chain = self.reasoner.reason(input_text)
        
        # Gera output baseado no modo
        if mode == ProcessingMode.DIALOGUE:
            self.dialogue.user_says(input_text)
            output = self.dialogue.respond()
        
        elif mode == ProcessingMode.ANALYSIS:
            # Modo análise: retorna insights
            parts = [
                f"Análise de: '{input_text}'",
                f"Tokens focados: {', '.join(focus_items[:5])}",
            ]
            
            if retrievals:
                parts.append(f"Memórias relacionadas: {len(retrievals)}")
            
            if applicable_rules:
                parts.append(f"Regras aplicáveis: {len(applicable_rules)}")
                for rule in applicable_rules[:2]:
                    parts.append(f"  - SE {rule.antecedents} ENTÃO {rule.consequent}")
            
            output = "\n".join(parts)
        
        else:  # INFERENCE ou LEARNING
            # Tenta compor resposta
            response_parts = []
            
            # Usa padrões comprimidos
            compressed, ratio = self.compressor.compress(tokens)
            if ratio < 1.0:
                response_parts.append("Padrões reconhecidos.")
            
            # Usa regras
            for rule in applicable_rules[:2]:
                # consequent é um Condition, extrai informação útil
                response_parts.append(str(rule.consequent))
            
            # Usa memórias
            for ret in retrievals[:2]:
                if ret.trace.value:
                    response_parts.append(str(ret.trace.value))
            
            # Usa conclusão do raciocínio
            if chain.conclusion:
                response_parts.append(chain.conclusion)
            
            output = " ".join(response_parts) if response_parts else "Processado."
        
        # Computa confiança
        confidence = chain.total_confidence if chain else 0.5
        if retrievals:
            confidence = (confidence + retrievals[0].relevance) / 2
        
        processing_time = (time.time() - start_time) * 1000
        
        return ProcessingResult(
            mode=mode,
            input_text=input_text,
            output_text=output,
            reasoning_chain=chain,
            attention_focus=focus_items,
            rules_applied=applicable_rules,
            analogies_used=[],
            memory_retrievals=retrievals,
            confidence=confidence,
            processing_time_ms=processing_time,
        )
    
    def query(
        self,
        question: str,
        context: str = "",
    ) -> Tuple[str, float, str]:
        """
        Responde a uma pergunta.
        
        Retorna (resposta, confiança, explicação).
        """
        result = self.process(question, mode=ProcessingMode.INFERENCE)
        
        explanation = []
        
        if result.reasoning_chain:
            explanation.append("Raciocínio:")
            for step in result.reasoning_chain.steps[:5]:
                explanation.append(f"  {step}")
        
        if result.rules_applied:
            explanation.append("Regras usadas:")
            for rule in result.rules_applied[:3]:
                explanation.append(f"  {rule}")
        
        return (
            result.output_text,
            result.confidence,
            "\n".join(explanation),
        )
    
    def chat(self, message: str) -> str:
        """Interface de chat simples."""
        result = self.process(message, mode=ProcessingMode.DIALOGUE)
        return result.output_text
    
    def analyze(self, text: str) -> str:
        """Analisa um texto."""
        result = self.process(text, mode=ProcessingMode.ANALYSIS)
        return result.output_text
    
    def learn_fact(self, key: str, value: str, context: Dict[str, Any] | None = None) -> None:
        """Aprende um fato específico."""
        key_tokens = key.split()
        context_list = [f"{k}_{v}" for k, v in (context or {}).items()]
        self.memory.store(key_tokens, value, context=context_list)
        
        # Também adiciona ao grafo
        tokens = (key + " " + value).split()
        self.graph.add_document(tokens)
    
    def learn_rule(
        self,
        antecedents: Set[str],
        consequent: str,
        confidence: float = 1.0,
    ) -> None:
        """Aprende uma regra explicitamente."""
        # Converte strings para Conditions
        ant_conditions = tuple(Condition("is", (ant,)) for ant in antecedents)
        cons_condition = Condition("implies", (consequent,))
        
        rule = SymbolicRule(
            antecedents=ant_conditions,
            consequent=cons_condition,
            support=1,
            confidence=confidence,
            lift=1.0,
        )
        self.learned_rules.rules.append(rule)
    
    def find_analogy(
        self,
        source_name: str,
        source_facts: List[Tuple[str, ...]],
        target_name: str,
        target_facts: List[Tuple[str, ...]],
    ) -> Analogy | None:
        """
        Encontra analogia entre dois domínios.
        """
        source = Structure.from_facts(source_name, source_facts)
        target = Structure.from_facts(target_name, target_facts)
        
        self.analogy.register_structure(source)
        self.analogy.register_structure(target)
        
        return self.analogy.find_analogy(source, target)
    
    def get_similar(self, text: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Encontra textos similares na memória."""
        tokens = text.split()
        results = self.memory.retrieve(tokens, top_k=top_k)
        return [(" ".join(r.trace.key), r.relevance) for r in results]
    
    def explain(self, input_text: str) -> str:
        """Gera explicação detalhada do processamento."""
        result = self.process(input_text, mode=ProcessingMode.ANALYSIS)
        return result.explain()
    
    def status(self) -> Dict[str, Any]:
        """Retorna status do motor."""
        return {
            "trained": self._trained,
            "corpus_size": self._corpus_size,
            "patterns": len(self.compressor.dictionary),
            "rules": len(self.learned_rules.rules),
            "memory_items": len(self.memory),
            "graph_nodes": len(self.graph.token_counts),
        }


def create_demo_engine() -> AdvancedLearningEngine:
    """
    Cria motor com dados de demonstração.
    """
    engine = AdvancedLearningEngine()
    
    # Corpus de exemplo
    demo_corpus = [
        "O cachorro corre no parque todos os dias.",
        "O gato dorme no sofá durante a tarde.",
        "Pássaros voam pelo céu azul da manhã.",
        "O sol nasce no leste e se põe no oeste.",
        "A água ferve a cem graus celsius.",
        "Plantas precisam de luz solar para crescer.",
        "O cérebro humano processa informações complexas.",
        "Computadores executam instruções sequencialmente.",
        "Algoritmos resolvem problemas de forma sistemática.",
        "Linguagem natural é complexa e ambígua.",
        "Inteligência artificial aprende com dados.",
        "Redes neurais usam pesos e gradientes.",
        "Sistemas simbólicos usam regras explícitas.",
        "Compressão reduz redundância em dados.",
        "Memória armazena informações para recuperação.",
        "Raciocínio conecta premissas a conclusões.",
        "Analogia transfere conhecimento entre domínios.",
        "Abstração generaliza de casos específicos.",
        "Atenção foca em informações relevantes.",
        "Geração produz texto coerente e informativo.",
    ]
    
    # Treina
    engine.train(demo_corpus, verbose=False)
    
    # Adiciona alguns fatos
    engine.learn_fact("cachorro", "animal mamífero que late")
    engine.learn_fact("gato", "animal mamífero que mia")
    engine.learn_fact("sol", "estrela do sistema solar")
    engine.learn_fact("água", "H2O, líquido essencial")
    
    # Adiciona algumas regras
    engine.learn_rule({"animal"}, "ser vivo")
    engine.learn_rule({"mamífero"}, "animal de sangue quente")
    engine.learn_rule({"cachorro"}, "mamífero")
    engine.learn_rule({"gato"}, "mamífero")
    
    return engine


__all__ = [
    "ProcessingMode",
    "AdvancedConfig",
    "ProcessingResult",
    "AdvancedLearningEngine",
    "create_demo_engine",
]
