"""
Cadeia de Raciocínio Simbólica: Chain of Thought Sem Pesos Neurais.

Em LLMs, Chain of Thought emerge de forma implícita nos pesos.
Aqui, implementamos explicitamente como:

1. DECOMPOSIÇÃO: Quebra problema em sub-problemas
2. DERIVAÇÃO: Aplica regras/inferências passo a passo
3. COMPOSIÇÃO: Combina resultados intermediários
4. VERIFICAÇÃO: Valida consistência da cadeia

Cada passo é:
- Explícito e auditável
- Baseado em regras ou conhecimento prévio
- Interconectado com rastreamento de dependências

Diferença fundamental:
- LLM: "pensa" através de ativações implícitas
- Nós: "pensamos" através de derivações explícitas
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, FrozenSet, List, Mapping, Set, Tuple
from hashlib import blake2b
import time


class StepType(Enum):
    """Tipos de passos de raciocínio."""
    
    OBSERVATION = auto()  # Observação inicial
    DECOMPOSITION = auto()  # Quebra em sub-problemas
    RETRIEVAL = auto()  # Busca em memória/conhecimento
    INFERENCE = auto()  # Aplicação de regra
    ANALOGY = auto()  # Raciocínio por analogia
    HYPOTHESIS = auto()  # Geração de hipótese
    VERIFICATION = auto()  # Verificação de consistência
    SYNTHESIS = auto()  # Composição de resultados
    CONCLUSION = auto()  # Conclusão final


@dataclass(frozen=True)
class ReasoningStep:
    """Um passo individual na cadeia de raciocínio."""
    
    id: str
    step_type: StepType
    content: str
    premises: Tuple[str, ...]  # IDs dos passos anteriores
    confidence: float
    metadata: Mapping[str, Any] = field(default_factory=dict)
    
    def depends_on(self, other_id: str) -> bool:
        return other_id in self.premises
    
    def __str__(self) -> str:
        prefix = f"[{self.step_type.name}]"
        deps = f" (←{', '.join(self.premises)})" if self.premises else ""
        return f"{prefix}{deps}: {self.content}"


@dataclass
class ReasoningChain:
    """Uma cadeia completa de raciocínio."""
    
    query: str
    steps: List[ReasoningStep] = field(default_factory=list)
    conclusion: str = ""
    total_confidence: float = 0.0
    
    def add_step(self, step: ReasoningStep) -> None:
        self.steps.append(step)
    
    def get_step(self, step_id: str) -> ReasoningStep | None:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
    
    def get_premises_for(self, step: ReasoningStep) -> List[ReasoningStep]:
        return [s for s in self.steps if s.id in step.premises]
    
    def trace(self) -> str:
        """Gera trace legível da cadeia."""
        lines = [f"Query: {self.query}", ""]
        
        for i, step in enumerate(self.steps, 1):
            lines.append(f"{i}. {step}")
        
        lines.append("")
        lines.append(f"Conclusão: {self.conclusion}")
        lines.append(f"Confiança: {self.total_confidence:.2%}")
        
        return "\n".join(lines)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Valida a cadeia de raciocínio."""
        errors = []
        step_ids = {s.id for s in self.steps}
        
        for step in self.steps:
            # Verifica se todas as premises existem
            for premise_id in step.premises:
                if premise_id not in step_ids:
                    errors.append(f"Passo {step.id} depende de {premise_id} que não existe")
            
            # Verifica se não há ciclos
            visited = set()
            to_visit = list(step.premises)
            
            while to_visit:
                current = to_visit.pop()
                if current == step.id:
                    errors.append(f"Ciclo detectado envolvendo passo {step.id}")
                    break
                
                if current in visited:
                    continue
                
                visited.add(current)
                current_step = self.get_step(current)
                
                if current_step:
                    to_visit.extend(current_step.premises)
        
        return len(errors) == 0, errors


@dataclass
class KnowledgeBase:
    """Base de conhecimento para raciocínio."""
    
    facts: Dict[str, Set[str]] = field(default_factory=lambda: {})
    rules: List[Tuple[str, str, str]] = field(default_factory=list)  # (condition, action, name)
    definitions: Dict[str, str] = field(default_factory=dict)
    
    def add_fact(self, category: str, fact: str) -> None:
        if category not in self.facts:
            self.facts[category] = set()
        self.facts[category].add(fact)
    
    def add_rule(self, condition: str, action: str, name: str = "") -> None:
        self.rules.append((condition, action, name))
    
    def add_definition(self, term: str, definition: str) -> None:
        self.definitions[term] = definition
    
    def query_facts(self, category: str) -> Set[str]:
        return self.facts.get(category, set())
    
    def find_applicable_rules(self, context: str) -> List[Tuple[str, str, str]]:
        """Encontra regras aplicáveis ao contexto."""
        applicable = []
        context_lower = context.lower()
        
        for condition, action, name in self.rules:
            if condition.lower() in context_lower:
                applicable.append((condition, action, name))
        
        return applicable


class ChainOfThoughtEngine:
    """
    Motor de Cadeia de Raciocínio Simbólico.
    
    Implementa raciocínio multi-step explícito:
    1. Recebe query
    2. Decompõe em sub-problemas
    3. Busca conhecimento relevante
    4. Aplica regras/inferências
    5. Sintetiza conclusão
    """
    
    def __init__(self, knowledge_base: KnowledgeBase | None = None):
        self.kb = knowledge_base or KnowledgeBase()
        self._step_counter = 0
    
    def _new_step_id(self) -> str:
        self._step_counter += 1
        return f"S{self._step_counter}"
    
    def reason(
        self,
        query: str,
        max_steps: int = 20,
        min_confidence: float = 0.3,
    ) -> ReasoningChain:
        """
        Executa raciocínio sobre uma query.
        """
        chain = ReasoningChain(query=query)
        self._step_counter = 0
        
        # Passo 1: Observação inicial
        obs_step = self._observe(query)
        chain.add_step(obs_step)
        
        # Passo 2: Decomposição
        sub_problems = self._decompose(query, obs_step.id)
        for sp in sub_problems:
            chain.add_step(sp)
        
        # Passo 3: Busca de conhecimento
        for sp in sub_problems:
            retrieval = self._retrieve(sp.content, sp.id)
            if retrieval:
                chain.add_step(retrieval)
        
        # Passo 4: Inferências
        inference_steps = self._infer(chain)
        for inf in inference_steps[:max_steps]:
            chain.add_step(inf)
        
        # Passo 5: Síntese
        synthesis = self._synthesize(chain)
        chain.add_step(synthesis)
        
        # Passo 6: Conclusão
        conclusion = self._conclude(chain, synthesis.id)
        chain.add_step(conclusion)
        
        chain.conclusion = conclusion.content
        chain.total_confidence = self._compute_chain_confidence(chain)
        
        return chain
    
    def reason_step_by_step(
        self,
        query: str,
    ) -> "ReasoningIterator":
        """Retorna iterador para raciocínio passo a passo."""
        return ReasoningIterator(self, query)
    
    def _observe(self, query: str) -> ReasoningStep:
        """Cria passo de observação inicial."""
        # Extrai termos-chave
        words = query.lower().split()
        key_terms = [w for w in words if len(w) > 3]
        
        content = f"Analisar: '{query}'. Termos-chave: {', '.join(key_terms[:5])}"
        
        return ReasoningStep(
            id=self._new_step_id(),
            step_type=StepType.OBSERVATION,
            content=content,
            premises=(),
            confidence=1.0,
        )
    
    def _decompose(self, query: str, obs_id: str) -> List[ReasoningStep]:
        """Decompõe query em sub-problemas."""
        steps = []
        
        # Heurísticas de decomposição
        if " e " in query.lower():
            parts = query.lower().split(" e ")
            for i, part in enumerate(parts[:3], 1):
                step = ReasoningStep(
                    id=self._new_step_id(),
                    step_type=StepType.DECOMPOSITION,
                    content=f"Sub-problema {i}: {part.strip()}",
                    premises=(obs_id,),
                    confidence=0.9,
                )
                steps.append(step)
        
        elif "?" in query:
            # Pergunta - identificar o que está sendo perguntado
            step = ReasoningStep(
                id=self._new_step_id(),
                step_type=StepType.DECOMPOSITION,
                content=f"Identificar: O que está sendo perguntado?",
                premises=(obs_id,),
                confidence=0.95,
            )
            steps.append(step)
        
        else:
            # Afirmação - analisar componentes
            step = ReasoningStep(
                id=self._new_step_id(),
                step_type=StepType.DECOMPOSITION,
                content=f"Analisar componentes da afirmação",
                premises=(obs_id,),
                confidence=0.85,
            )
            steps.append(step)
        
        return steps
    
    def _retrieve(self, context: str, premise_id: str) -> ReasoningStep | None:
        """Busca conhecimento relevante."""
        relevant = []
        context_words = set(context.lower().split())
        
        # Busca em fatos
        for category, facts in self.kb.facts.items():
            for fact in facts:
                fact_words = set(fact.lower().split())
                if fact_words & context_words:
                    relevant.append(f"[{category}] {fact}")
        
        # Busca em definições
        for term, definition in self.kb.definitions.items():
            if term.lower() in context.lower():
                relevant.append(f"[DEF] {term}: {definition}")
        
        if not relevant:
            return None
        
        content = "Conhecimento relevante: " + "; ".join(relevant[:3])
        
        return ReasoningStep(
            id=self._new_step_id(),
            step_type=StepType.RETRIEVAL,
            content=content,
            premises=(premise_id,),
            confidence=0.8,
        )
    
    def _infer(self, chain: ReasoningChain) -> List[ReasoningStep]:
        """Aplica regras de inferência."""
        inferences = []
        
        # Coleta contexto dos passos anteriores
        context = " ".join(s.content for s in chain.steps)
        premise_ids = tuple(s.id for s in chain.steps[-3:] if s.step_type != StepType.OBSERVATION)
        
        # Encontra regras aplicáveis
        applicable = self.kb.find_applicable_rules(context)
        
        for condition, action, name in applicable[:3]:
            step = ReasoningStep(
                id=self._new_step_id(),
                step_type=StepType.INFERENCE,
                content=f"Aplicando regra '{name}': SE {condition} ENTÃO {action}",
                premises=premise_ids if premise_ids else (chain.steps[0].id,),
                confidence=0.75,
                metadata={"rule_name": name},
            )
            inferences.append(step)
        
        # Adiciona inferência padrão se não houver regras
        if not inferences:
            step = ReasoningStep(
                id=self._new_step_id(),
                step_type=StepType.INFERENCE,
                content=f"Análise direta do contexto sem regras específicas aplicáveis",
                premises=premise_ids if premise_ids else (chain.steps[0].id,),
                confidence=0.6,
            )
            inferences.append(step)
        
        return inferences
    
    def _synthesize(self, chain: ReasoningChain) -> ReasoningStep:
        """Sintetiza resultados intermediários."""
        # Coleta passos relevantes
        relevant_steps = [
            s for s in chain.steps
            if s.step_type in (StepType.RETRIEVAL, StepType.INFERENCE, StepType.ANALOGY)
        ]
        
        if relevant_steps:
            synthesis_content = "Síntese: " + " + ".join(
                s.content.split(":")[0] if ":" in s.content else s.content[:30]
                for s in relevant_steps[:3]
            )
            premise_ids = tuple(s.id for s in relevant_steps[:3])
        else:
            synthesis_content = "Síntese baseada na observação inicial"
            premise_ids = (chain.steps[0].id,)
        
        return ReasoningStep(
            id=self._new_step_id(),
            step_type=StepType.SYNTHESIS,
            content=synthesis_content,
            premises=premise_ids,
            confidence=0.7,
        )
    
    def _conclude(self, chain: ReasoningChain, synthesis_id: str) -> ReasoningStep:
        """Gera conclusão final."""
        # Coleta evidências
        evidence_count = len([
            s for s in chain.steps
            if s.step_type in (StepType.RETRIEVAL, StepType.INFERENCE)
        ])
        
        if evidence_count > 2:
            conclusion = f"Com base em {evidence_count} evidências, conclui-se que a análise é fundamentada."
            confidence = min(0.9, 0.5 + evidence_count * 0.1)
        elif evidence_count > 0:
            conclusion = f"Conclusão preliminar baseada em evidências limitadas ({evidence_count})."
            confidence = 0.5 + evidence_count * 0.1
        else:
            conclusion = "Conclusão incerta devido à falta de evidências diretas."
            confidence = 0.3
        
        return ReasoningStep(
            id=self._new_step_id(),
            step_type=StepType.CONCLUSION,
            content=conclusion,
            premises=(synthesis_id,),
            confidence=confidence,
        )
    
    def _compute_chain_confidence(self, chain: ReasoningChain) -> float:
        """Computa confiança total da cadeia."""
        if not chain.steps:
            return 0.0
        
        # Média ponderada das confianças
        total_weight = 0.0
        weighted_sum = 0.0
        
        for step in chain.steps:
            weight = 1.0
            
            if step.step_type == StepType.CONCLUSION:
                weight = 2.0
            elif step.step_type == StepType.INFERENCE:
                weight = 1.5
            elif step.step_type == StepType.RETRIEVAL:
                weight = 1.3
            
            weighted_sum += step.confidence * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0


class ReasoningIterator:
    """Iterador para raciocínio passo a passo."""
    
    def __init__(self, engine: ChainOfThoughtEngine, query: str):
        self.engine = engine
        self.query = query
        self.chain = ReasoningChain(query=query)
        self._phase = 0  # 0=obs, 1=decomp, 2=retrieve, 3=infer, 4=synth, 5=conclude, 6=done
        self._sub_index = 0
        self._decomp_steps: List[ReasoningStep] = []
        self.engine._step_counter = 0
    
    def __iter__(self):
        return self
    
    def __next__(self) -> ReasoningStep:
        if self._phase == 0:
            # Observação
            step = self.engine._observe(self.query)
            self.chain.add_step(step)
            self._phase = 1
            return step
        
        elif self._phase == 1:
            # Decomposição
            if not self._decomp_steps:
                self._decomp_steps = self.engine._decompose(
                    self.query, 
                    self.chain.steps[0].id
                )
            
            if self._sub_index < len(self._decomp_steps):
                step = self._decomp_steps[self._sub_index]
                self.chain.add_step(step)
                self._sub_index += 1
                return step
            else:
                self._phase = 2
                self._sub_index = 0
                return self.__next__()
        
        elif self._phase == 2:
            # Retrieval
            if self._sub_index < len(self._decomp_steps):
                sp = self._decomp_steps[self._sub_index]
                self._sub_index += 1
                
                retrieval = self.engine._retrieve(sp.content, sp.id)
                if retrieval:
                    self.chain.add_step(retrieval)
                    return retrieval
                
                return self.__next__()
            else:
                self._phase = 3
                return self.__next__()
        
        elif self._phase == 3:
            # Inferência
            inferences = self.engine._infer(self.chain)
            for inf in inferences:
                self.chain.add_step(inf)
            self._phase = 4
            
            if inferences:
                return inferences[0]
            return self.__next__()
        
        elif self._phase == 4:
            # Síntese
            synthesis = self.engine._synthesize(self.chain)
            self.chain.add_step(synthesis)
            self._phase = 5
            return synthesis
        
        elif self._phase == 5:
            # Conclusão
            synthesis_id = self.chain.steps[-1].id
            conclusion = self.engine._conclude(self.chain, synthesis_id)
            self.chain.add_step(conclusion)
            
            self.chain.conclusion = conclusion.content
            self.chain.total_confidence = self.engine._compute_chain_confidence(self.chain)
            
            self._phase = 6
            return conclusion
        
        else:
            raise StopIteration


# Exemplo de base de conhecimento
def create_example_kb() -> KnowledgeBase:
    """Cria base de conhecimento de exemplo."""
    kb = KnowledgeBase()
    
    # Fatos
    kb.add_fact("matemática", "adição é comutativa")
    kb.add_fact("matemática", "multiplicação é distributiva sobre adição")
    kb.add_fact("lógica", "modus ponens: se P então Q, P, logo Q")
    kb.add_fact("lógica", "modus tollens: se P então Q, não Q, logo não P")
    
    # Definições
    kb.add_definition("algoritmo", "sequência finita de instruções para resolver um problema")
    kb.add_definition("recursão", "definição de algo em termos de si mesmo")
    kb.add_definition("inferência", "processo de derivar conclusões a partir de premissas")
    
    # Regras
    kb.add_rule("número par", "divisível por 2", "paridade")
    kb.add_rule("soma de pares", "resultado é par", "soma_paridade")
    kb.add_rule("contradição", "conclusão inválida", "princípio_não_contradição")
    
    return kb


__all__ = [
    "StepType",
    "ReasoningStep",
    "ReasoningChain",
    "KnowledgeBase",
    "ChainOfThoughtEngine",
    "ReasoningIterator",
    "create_example_kb",
]
