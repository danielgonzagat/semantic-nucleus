"""
Indutor de Regras Simbólicas.

Extrai padrões estruturais dos dados na forma de regras simbólicas.
Inspirado em ILP (Inductive Logic Programming) e program synthesis.

Diferente de redes neurais que aprendem pesos implícitos,
aqui aprendemos regras EXPLÍCITAS e INTERPRETÁVEIS:
    
    SE <condição1> E <condição2> ENTÃO <conclusão>

Cada regra tem:
- Antecedentes: condições que devem ser verdadeiras
- Consequente: conclusão derivada
- Suporte: quantas vezes a regra foi observada
- Confiança: proporção de casos onde a regra é válida

As regras são selecionadas por MDL: preferimos regras que
comprimem bem os dados (explicam muito com pouca complexidade).
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from hashlib import blake2b
from typing import (
    Callable,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Mapping,
    Sequence,
    Set,
    Tuple,
)


@dataclass(frozen=True)
class Condition:
    """Uma condição em uma regra."""
    
    predicate: str  # Nome do predicado
    args: Tuple[str, ...]  # Argumentos (podem ser variáveis ?X ou constantes)
    negated: bool = False
    
    def matches(self, fact: "Condition", bindings: Dict[str, str]) -> Dict[str, str] | None:
        """Tenta unificar esta condição com um fato."""
        if self.predicate != fact.predicate:
            return None
        if len(self.args) != len(fact.args):
            return None
        if self.negated != fact.negated:
            return None
        
        new_bindings = dict(bindings)
        
        for pattern_arg, fact_arg in zip(self.args, fact.args):
            if pattern_arg.startswith("?"):
                # Variável
                if pattern_arg in new_bindings:
                    if new_bindings[pattern_arg] != fact_arg:
                        return None
                else:
                    new_bindings[pattern_arg] = fact_arg
            else:
                # Constante
                if pattern_arg != fact_arg:
                    return None
        
        return new_bindings
    
    def substitute(self, bindings: Dict[str, str]) -> "Condition":
        """Substitui variáveis por valores."""
        new_args = tuple(
            bindings.get(arg, arg) if arg.startswith("?") else arg
            for arg in self.args
        )
        return Condition(self.predicate, new_args, self.negated)
    
    def __str__(self) -> str:
        neg = "¬" if self.negated else ""
        args_str = ", ".join(self.args)
        return f"{neg}{self.predicate}({args_str})"


@dataclass(frozen=True)
class SymbolicRule:
    """Uma regra simbólica induzida."""
    
    antecedents: Tuple[Condition, ...]
    consequent: Condition
    support: int  # Quantas vezes foi observada
    confidence: float  # P(consequent | antecedents)
    lift: float  # Quanto a regra melhora sobre baseline
    
    @property
    def complexity(self) -> int:
        """Complexidade da regra (para MDL)."""
        return len(self.antecedents) + 1
    
    @property
    def mdl_score(self) -> float:
        """Score MDL: preferimos regras simples com alta confiança."""
        # Menor é melhor
        complexity_cost = self.complexity * 10
        coverage_gain = self.support * self.confidence * self.lift
        return complexity_cost - coverage_gain
    
    @property
    def id(self) -> str:
        hasher = blake2b(digest_size=8)
        for ant in self.antecedents:
            hasher.update(str(ant).encode("utf-8"))
        hasher.update(str(self.consequent).encode("utf-8"))
        return f"R{hasher.hexdigest()[:8]}"
    
    def applies(
        self,
        facts: Sequence[Condition],
    ) -> List[Dict[str, str]]:
        """Retorna todas as maneiras que a regra pode ser aplicada aos fatos."""
        # Inicia com binding vazio
        possible_bindings = [{}]
        
        for antecedent in self.antecedents:
            new_possible = []
            
            for bindings in possible_bindings:
                for fact in facts:
                    result = antecedent.matches(fact, bindings)
                    if result is not None:
                        new_possible.append(result)
            
            possible_bindings = new_possible
            
            if not possible_bindings:
                return []
        
        return possible_bindings
    
    def derive(
        self,
        facts: Sequence[Condition],
    ) -> List[Condition]:
        """Deriva novas conclusões a partir dos fatos."""
        bindings_list = self.applies(facts)
        conclusions = []
        
        for bindings in bindings_list:
            conclusion = self.consequent.substitute(bindings)
            conclusions.append(conclusion)
        
        return conclusions
    
    def __str__(self) -> str:
        ants = " ∧ ".join(str(a) for a in self.antecedents)
        return f"{ants} → {self.consequent} [sup={self.support}, conf={self.confidence:.2f}]"


@dataclass()
class RuleSet:
    """Conjunto de regras aprendidas."""
    
    rules: List[SymbolicRule] = field(default_factory=list)
    
    def add(self, rule: SymbolicRule) -> None:
        self.rules.append(rule)
    
    def sorted_by_quality(self) -> List[SymbolicRule]:
        """Retorna regras ordenadas por qualidade (MDL score)."""
        return sorted(self.rules, key=lambda r: r.mdl_score)
    
    def derive_all(
        self,
        facts: Sequence[Condition],
        max_iterations: int = 10,
    ) -> Set[Condition]:
        """Aplica todas as regras até saturação."""
        known = set(facts)
        new_facts = set(facts)
        
        for _ in range(max_iterations):
            derived = set()
            
            for rule in self.rules:
                conclusions = rule.derive(list(new_facts))
                for c in conclusions:
                    if c not in known:
                        derived.add(c)
                        known.add(c)
            
            if not derived:
                break
            
            new_facts = derived
        
        return known
    
    def filter_by_confidence(self, min_confidence: float) -> "RuleSet":
        """Filtra regras por confiança mínima."""
        filtered = [r for r in self.rules if r.confidence >= min_confidence]
        result = RuleSet()
        result.rules = filtered
        return result
    
    def __len__(self) -> int:
        return len(self.rules)
    
    def __iter__(self) -> Iterator[SymbolicRule]:
        return iter(self.rules)


@dataclass()
class RuleInductor:
    """
    Indutor de regras simbólicas a partir de dados.
    
    Usa uma abordagem bottom-up:
    1. Extrai padrões frequentes dos dados
    2. Generaliza padrões para regras com variáveis
    3. Calcula suporte e confiança
    4. Filtra por MDL (complexidade vs cobertura)
    
    Isso é similar a Apriori/FP-Growth para association rules,
    mas com extensões para regras lógicas de primeira ordem.
    """
    
    min_support: int = 2
    min_confidence: float = 0.5
    max_antecedents: int = 4
    max_rules: int = 1000
    
    def induce_from_sequences(
        self,
        sequences: Sequence[Sequence[str]],
    ) -> RuleSet:
        """
        Induz regras de sequências de tokens.
        
        Trata cada sequência como uma série de fatos:
        - follows(token_i, token_j) se j = i + 1
        - near(token_i, token_j) se |i - j| <= 2
        """
        facts_per_example: List[Set[Condition]] = []
        all_facts: List[Condition] = []
        
        for seq in sequences:
            example_facts: Set[Condition] = set()
            
            for i, token in enumerate(seq):
                # Fato: exists(token)
                example_facts.add(Condition("exists", (token,)))
                
                # Fato: follows(prev, curr)
                if i > 0:
                    prev = seq[i - 1]
                    example_facts.add(Condition("follows", (prev, token)))
                
                # Fato: near(token1, token2)
                for j in range(max(0, i - 2), min(len(seq), i + 3)):
                    if i != j:
                        other = seq[j]
                        pair = tuple(sorted([token, other]))
                        example_facts.add(Condition("near", pair))
            
            facts_per_example.append(example_facts)
            all_facts.extend(example_facts)
        
        return self._induce_from_facts(facts_per_example, all_facts)
    
    def induce_from_facts(
        self,
        examples: Sequence[Sequence[Condition]],
    ) -> RuleSet:
        """Induz regras a partir de exemplos de fatos."""
        facts_per_example = [set(ex) for ex in examples]
        all_facts = [f for ex in examples for f in ex]
        return self._induce_from_facts(facts_per_example, all_facts)
    
    def _induce_from_facts(
        self,
        facts_per_example: Sequence[Set[Condition]],
        all_facts: Sequence[Condition],
    ) -> RuleSet:
        """Implementação principal da indução."""
        rules = RuleSet()
        
        # Conta frequência de cada fato
        fact_counts = Counter(all_facts)
        total_examples = len(facts_per_example)
        
        if total_examples == 0:
            return rules
        
        # Encontra padrões frequentes
        frequent_facts = {
            f for f, count in fact_counts.items()
            if count >= self.min_support
        }
        
        # Agrupa por predicado para generalização
        by_predicate: Dict[str, List[Condition]] = defaultdict(list)
        for fact in frequent_facts:
            by_predicate[fact.predicate].append(fact)
        
        # Gera regras simples (1 antecedente -> 1 consequente)
        rules_generated = 0
        
        for pred1, facts1 in by_predicate.items():
            for pred2, facts2 in by_predicate.items():
                if rules_generated >= self.max_rules:
                    break
                
                # Tenta encontrar padrões A -> B
                cooc = self._compute_cooccurrence(
                    facts1, facts2, facts_per_example
                )
                
                for (ant, cons), (support, confidence) in cooc.items():
                    if support < self.min_support:
                        continue
                    if confidence < self.min_confidence:
                        continue
                    
                    # Calcula lift
                    cons_prob = sum(
                        1 for ex in facts_per_example if cons in ex
                    ) / total_examples
                    lift = confidence / cons_prob if cons_prob > 0 else 1.0
                    
                    rule = SymbolicRule(
                        antecedents=(ant,),
                        consequent=cons,
                        support=support,
                        confidence=confidence,
                        lift=lift,
                    )
                    
                    rules.add(rule)
                    rules_generated += 1
        
        # Gera regras com múltiplos antecedentes
        if self.max_antecedents > 1:
            simple_rules = list(rules)
            
            for rule1 in simple_rules:
                for rule2 in simple_rules:
                    if rules_generated >= self.max_rules:
                        break
                    
                    # Tenta combinar se têm o mesmo consequente
                    if rule1.consequent != rule2.consequent:
                        continue
                    if rule1.antecedents == rule2.antecedents:
                        continue
                    
                    # Combina antecedentes
                    combined_ants = tuple(set(rule1.antecedents) | set(rule2.antecedents))
                    
                    if len(combined_ants) > self.max_antecedents:
                        continue
                    
                    # Calcula métricas da regra combinada
                    support, confidence = self._compute_rule_metrics(
                        combined_ants, rule1.consequent, facts_per_example
                    )
                    
                    if support < self.min_support:
                        continue
                    if confidence < self.min_confidence:
                        continue
                    
                    cons_prob = sum(
                        1 for ex in facts_per_example if rule1.consequent in ex
                    ) / total_examples
                    lift = confidence / cons_prob if cons_prob > 0 else 1.0
                    
                    combined_rule = SymbolicRule(
                        antecedents=combined_ants,
                        consequent=rule1.consequent,
                        support=support,
                        confidence=confidence,
                        lift=lift,
                    )
                    
                    # Só adiciona se for melhor que as regras individuais
                    if combined_rule.mdl_score < rule1.mdl_score:
                        rules.add(combined_rule)
                        rules_generated += 1
        
        # Generaliza regras para usar variáveis
        generalized = self._generalize_rules(rules)
        
        return generalized
    
    def _compute_cooccurrence(
        self,
        facts1: Sequence[Condition],
        facts2: Sequence[Condition],
        examples: Sequence[Set[Condition]],
    ) -> Dict[Tuple[Condition, Condition], Tuple[int, float]]:
        """Computa co-ocorrência entre fatos para derivar regras."""
        result: Dict[Tuple[Condition, Condition], Tuple[int, float]] = {}
        
        for f1 in facts1:
            for f2 in facts2:
                if f1 == f2:
                    continue
                
                # Conta exemplos onde ambos ocorrem
                both = sum(1 for ex in examples if f1 in ex and f2 in ex)
                
                # Conta exemplos onde f1 ocorre
                f1_count = sum(1 for ex in examples if f1 in ex)
                
                if f1_count == 0:
                    continue
                
                support = both
                confidence = both / f1_count
                
                result[(f1, f2)] = (support, confidence)
        
        return result
    
    def _compute_rule_metrics(
        self,
        antecedents: Tuple[Condition, ...],
        consequent: Condition,
        examples: Sequence[Set[Condition]],
    ) -> Tuple[int, float]:
        """Computa suporte e confiança de uma regra."""
        ant_match = sum(
            1 for ex in examples
            if all(ant in ex for ant in antecedents)
        )
        
        if ant_match == 0:
            return 0, 0.0
        
        both_match = sum(
            1 for ex in examples
            if all(ant in ex for ant in antecedents) and consequent in ex
        )
        
        return both_match, both_match / ant_match
    
    def _generalize_rules(self, rules: RuleSet) -> RuleSet:
        """
        Generaliza regras substituindo constantes por variáveis.
        
        Exemplo:
            follows(gato, dorme) ∧ exists(gato) → near(gato, noite)
        Vira:
            follows(?X, dorme) ∧ exists(?X) → near(?X, noite)
        """
        generalized = RuleSet()
        seen_patterns: Set[str] = set()
        
        for rule in rules:
            # Encontra constantes que aparecem múltiplas vezes
            constant_counts: Counter[str] = Counter()
            
            for ant in rule.antecedents:
                for arg in ant.args:
                    if not arg.startswith("?"):
                        constant_counts[arg] += 1
            
            for arg in rule.consequent.args:
                if not arg.startswith("?"):
                    constant_counts[arg] += 1
            
            # Substitui constantes frequentes por variáveis
            var_mapping: Dict[str, str] = {}
            var_counter = 0
            
            for const, count in constant_counts.items():
                if count >= 2:  # Aparece em múltiplos lugares
                    var_counter += 1
                    var_mapping[const] = f"?X{var_counter}"
            
            if not var_mapping:
                # Sem generalização possível
                generalized.add(rule)
                continue
            
            # Cria versão generalizada
            new_antecedents = []
            for ant in rule.antecedents:
                new_args = tuple(
                    var_mapping.get(arg, arg) for arg in ant.args
                )
                new_antecedents.append(Condition(ant.predicate, new_args, ant.negated))
            
            new_consequent_args = tuple(
                var_mapping.get(arg, arg) for arg in rule.consequent.args
            )
            new_consequent = Condition(
                rule.consequent.predicate,
                new_consequent_args,
                rule.consequent.negated,
            )
            
            gen_rule = SymbolicRule(
                antecedents=tuple(new_antecedents),
                consequent=new_consequent,
                support=rule.support,
                confidence=rule.confidence,
                lift=rule.lift,
            )
            
            # Evita duplicatas
            pattern = str(gen_rule)
            if pattern not in seen_patterns:
                seen_patterns.add(pattern)
                generalized.add(gen_rule)
        
        return generalized


__all__ = ["RuleInductor", "SymbolicRule", "RuleSet", "Condition"]
