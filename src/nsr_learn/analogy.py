"""
Analogia Estrutural: Raciocínio por Analogia Sem Pesos Neurais.

Analogia é uma das formas mais poderosas de raciocínio humano.
Em vez de aprender por gradiente, aprendemos por MAPEAMENTO ESTRUTURAL.

Teoria base: Structure-Mapping Theory (Gentner, 1983)
- Analogias são mapeamentos entre estruturas relacionais
- O que importa são as RELAÇÕES, não os objetos

Exemplo:
    "Átomo é como sistema solar"
    
    FONTE (sistema solar):
        - sol ATRAI planetas
        - planetas ORBITAM sol
        - sol é MAIOR que planetas
    
    ALVO (átomo):
        - núcleo ATRAI elétrons
        - elétrons ORBITAM núcleo
        - núcleo é MAIOR que elétrons
    
    MAPEAMENTO:
        sol → núcleo
        planetas → elétrons
        ATRAI → ATRAI (preservado)
        ORBITAM → ORBITAM (preservado)

Isso permite TRANSFERÊNCIA de conhecimento sem treinamento!
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterator, List, Mapping, Sequence, Set, Tuple
from hashlib import blake2b


@dataclass(frozen=True)
class Relation:
    """Uma relação entre entidades."""
    
    predicate: str
    args: Tuple[str, ...]
    
    @property
    def arity(self) -> int:
        return len(self.args)
    
    def __str__(self) -> str:
        return f"{self.predicate}({', '.join(self.args)})"


@dataclass(frozen=True)
class Structure:
    """Uma estrutura relacional (conjunto de relações)."""
    
    name: str
    entities: FrozenSet[str]
    relations: Tuple[Relation, ...]
    
    @staticmethod
    def from_facts(name: str, facts: Sequence[Tuple[str, ...]]) -> "Structure":
        """Cria estrutura a partir de fatos (predicado, arg1, arg2, ...)."""
        entities: Set[str] = set()
        relations: List[Relation] = []
        
        for fact in facts:
            if len(fact) < 2:
                continue
            pred = fact[0]
            args = tuple(fact[1:])
            entities.update(args)
            relations.append(Relation(pred, args))
        
        return Structure(
            name=name,
            entities=frozenset(entities),
            relations=tuple(relations),
        )
    
    def relation_signature(self) -> Tuple[Tuple[str, int], ...]:
        """Assinatura estrutural (predicados e aridades)."""
        sig = [(r.predicate, r.arity) for r in self.relations]
        return tuple(sorted(set(sig)))
    
    def __str__(self) -> str:
        rels = ", ".join(str(r) for r in self.relations)
        return f"{self.name}: {{{rels}}}"


@dataclass(frozen=True)
class StructuralMapping:
    """Mapeamento entre duas estruturas."""
    
    source: Structure
    target: Structure
    entity_map: Mapping[str, str]  # source_entity → target_entity
    relation_map: Mapping[str, str]  # source_predicate → target_predicate
    score: float  # Qualidade do mapeamento
    
    def apply_to_relation(self, rel: Relation) -> Relation | None:
        """Aplica o mapeamento a uma relação."""
        new_pred = self.relation_map.get(rel.predicate)
        if new_pred is None:
            return None
        
        new_args = []
        for arg in rel.args:
            mapped = self.entity_map.get(arg)
            if mapped is None:
                return None
            new_args.append(mapped)
        
        return Relation(new_pred, tuple(new_args))
    
    def transfer_inference(self, source_conclusion: Relation) -> Relation | None:
        """Transfere uma inferência da fonte para o alvo."""
        return self.apply_to_relation(source_conclusion)


@dataclass(frozen=True)
class Analogy:
    """Uma analogia completa entre domínios."""
    
    source_domain: str
    target_domain: str
    mapping: StructuralMapping
    inferences: Tuple[Relation, ...]  # Inferências transferidas
    confidence: float
    
    def explain(self) -> str:
        """Gera explicação textual da analogia."""
        lines = [
            f"Analogia: {self.source_domain} → {self.target_domain}",
            f"Confiança: {self.confidence:.2%}",
            "",
            "Mapeamento de entidades:",
        ]
        
        for src, tgt in self.mapping.entity_map.items():
            lines.append(f"  {src} → {tgt}")
        
        lines.append("")
        lines.append("Mapeamento de relações:")
        
        for src, tgt in self.mapping.relation_map.items():
            lines.append(f"  {src} → {tgt}")
        
        if self.inferences:
            lines.append("")
            lines.append("Inferências transferidas:")
            for inf in self.inferences:
                lines.append(f"  {inf}")
        
        return "\n".join(lines)


class AnalogyEngine:
    """
    Motor de raciocínio por analogia.
    
    Encontra mapeamentos estruturais entre domínios e
    transfere conhecimento SEM usar pesos ou gradientes.
    
    Algoritmo:
    1. Encontra correspondência de predicados (mesma aridade)
    2. Encontra correspondência de entidades (consistência estrutural)
    3. Pontua mapeamento por:
       - Quantidade de relações mapeadas
       - Sistematicidade (relações conectadas)
       - Consistência (sem conflitos)
    4. Transfere inferências do domínio fonte para o alvo
    """
    
    def __init__(self):
        self.known_structures: Dict[str, Structure] = {}
        self.known_analogies: List[Analogy] = []
    
    def register_structure(self, structure: Structure) -> None:
        """Registra uma estrutura conhecida."""
        self.known_structures[structure.name] = structure
    
    def find_analogy(
        self,
        source: Structure,
        target: Structure,
        min_score: float = 0.3,
    ) -> Analogy | None:
        """
        Encontra a melhor analogia entre fonte e alvo.
        """
        # Encontra mapeamento de predicados
        pred_mapping = self._map_predicates(source, target)
        
        if not pred_mapping:
            return None
        
        # Encontra mapeamento de entidades
        entity_mapping = self._map_entities(source, target, pred_mapping)
        
        if not entity_mapping:
            return None
        
        # Calcula score
        score = self._compute_mapping_score(
            source, target, pred_mapping, entity_mapping
        )
        
        if score < min_score:
            return None
        
        mapping = StructuralMapping(
            source=source,
            target=target,
            entity_map=entity_mapping,
            relation_map=pred_mapping,
            score=score,
        )
        
        # Encontra inferências que podem ser transferidas
        inferences = self._find_transferable_inferences(source, target, mapping)
        
        analogy = Analogy(
            source_domain=source.name,
            target_domain=target.name,
            mapping=mapping,
            inferences=tuple(inferences),
            confidence=score,
        )
        
        self.known_analogies.append(analogy)
        return analogy
    
    def find_similar_domain(
        self,
        target: Structure,
        min_score: float = 0.3,
    ) -> List[Tuple[Structure, float]]:
        """Encontra domínios conhecidos similares ao alvo."""
        candidates = []
        
        for name, source in self.known_structures.items():
            if name == target.name:
                continue
            
            # Compara assinaturas estruturais
            sig_similarity = self._signature_similarity(source, target)
            
            if sig_similarity >= min_score:
                candidates.append((source, sig_similarity))
        
        return sorted(candidates, key=lambda x: -x[1])
    
    def reason_by_analogy(
        self,
        query_structure: Structure,
        query_relation: Relation,
    ) -> List[Tuple[Relation, float, str]]:
        """
        Responde a uma query usando raciocínio analógico.
        
        Retorna lista de (conclusão, confiança, fonte).
        """
        conclusions = []
        
        # Encontra domínios similares
        similar = self.find_similar_domain(query_structure)
        
        for source, sim_score in similar[:5]:  # Top 5
            # Tenta encontrar analogia
            analogy = self.find_analogy(source, query_structure)
            
            if analogy is None:
                continue
            
            # Procura relação correspondente na fonte
            for source_rel in source.relations:
                # Mapeia query_relation para ver se corresponde
                mapped = analogy.mapping.apply_to_relation(source_rel)
                
                if mapped is not None:
                    # Verifica se é relevante para a query
                    if self._relations_compatible(mapped, query_relation):
                        confidence = analogy.confidence * sim_score
                        conclusions.append((mapped, confidence, source.name))
        
        return sorted(conclusions, key=lambda x: -x[1])
    
    def _map_predicates(
        self,
        source: Structure,
        target: Structure,
    ) -> Dict[str, str]:
        """Mapeia predicados da fonte para o alvo."""
        mapping = {}
        
        # Agrupa por aridade
        source_by_arity: Dict[int, List[str]] = defaultdict(list)
        target_by_arity: Dict[int, List[str]] = defaultdict(list)
        
        for rel in source.relations:
            source_by_arity[rel.arity].append(rel.predicate)
        
        for rel in target.relations:
            target_by_arity[rel.arity].append(rel.predicate)
        
        # Mapeia predicados da mesma aridade
        for arity in source_by_arity:
            if arity not in target_by_arity:
                continue
            
            src_preds = list(set(source_by_arity[arity]))
            tgt_preds = list(set(target_by_arity[arity]))
            
            # Mapeamento simples: primeiro com primeiro
            # Em versão avançada, usaríamos similaridade semântica
            for i, src in enumerate(src_preds):
                if i < len(tgt_preds):
                    mapping[src] = tgt_preds[i]
        
        return mapping
    
    def _map_entities(
        self,
        source: Structure,
        target: Structure,
        pred_mapping: Dict[str, str],
    ) -> Dict[str, str]:
        """Mapeia entidades mantendo consistência estrutural."""
        entity_mapping: Dict[str, str] = {}
        
        # Para cada relação mapeada, tenta alinhar entidades
        source_rels_by_pred = defaultdict(list)
        target_rels_by_pred = defaultdict(list)
        
        for rel in source.relations:
            source_rels_by_pred[rel.predicate].append(rel)
        
        for rel in target.relations:
            target_rels_by_pred[rel.predicate].append(rel)
        
        # Alinha entidades por posição nas relações
        for src_pred, tgt_pred in pred_mapping.items():
            src_rels = source_rels_by_pred.get(src_pred, [])
            tgt_rels = target_rels_by_pred.get(tgt_pred, [])
            
            for i, src_rel in enumerate(src_rels):
                if i >= len(tgt_rels):
                    break
                
                tgt_rel = tgt_rels[i]
                
                for j, src_ent in enumerate(src_rel.args):
                    if j >= len(tgt_rel.args):
                        break
                    
                    tgt_ent = tgt_rel.args[j]
                    
                    # Verifica consistência
                    if src_ent in entity_mapping:
                        if entity_mapping[src_ent] != tgt_ent:
                            # Conflito - ignora este mapeamento
                            continue
                    else:
                        entity_mapping[src_ent] = tgt_ent
        
        return entity_mapping
    
    def _compute_mapping_score(
        self,
        source: Structure,
        target: Structure,
        pred_mapping: Dict[str, str],
        entity_mapping: Dict[str, str],
    ) -> float:
        """Computa qualidade do mapeamento."""
        if not pred_mapping or not entity_mapping:
            return 0.0
        
        # Cobertura de predicados
        pred_coverage = len(pred_mapping) / max(1, len(set(r.predicate for r in source.relations)))
        
        # Cobertura de entidades
        entity_coverage = len(entity_mapping) / max(1, len(source.entities))
        
        # Sistematicidade: relações conectadas que são mapeadas
        mapped_relations = 0
        for rel in source.relations:
            if rel.predicate in pred_mapping:
                if all(arg in entity_mapping for arg in rel.args):
                    mapped_relations += 1
        
        relation_coverage = mapped_relations / max(1, len(source.relations))
        
        # Score combinado
        return (pred_coverage + entity_coverage + relation_coverage) / 3
    
    def _find_transferable_inferences(
        self,
        source: Structure,
        target: Structure,
        mapping: StructuralMapping,
    ) -> List[Relation]:
        """Encontra relações da fonte que podem ser transferidas."""
        target_preds = {rel.predicate for rel in target.relations}
        inferences = []
        
        for rel in source.relations:
            mapped = mapping.apply_to_relation(rel)
            
            if mapped is None:
                continue
            
            # Verifica se já existe no alvo
            exists_in_target = any(
                t.predicate == mapped.predicate and t.args == mapped.args
                for t in target.relations
            )
            
            if not exists_in_target:
                inferences.append(mapped)
        
        return inferences
    
    def _signature_similarity(
        self,
        source: Structure,
        target: Structure,
    ) -> float:
        """Similaridade baseada em assinatura estrutural."""
        sig1 = set(source.relation_signature())
        sig2 = set(target.relation_signature())
        
        if not sig1 and not sig2:
            return 0.0
        
        intersection = len(sig1 & sig2)
        union = len(sig1 | sig2)
        
        return intersection / union if union > 0 else 0.0
    
    def _relations_compatible(self, rel1: Relation, rel2: Relation) -> bool:
        """Verifica se duas relações são compatíveis."""
        return rel1.predicate == rel2.predicate and rel1.arity == rel2.arity


# Estruturas de exemplo pré-definidas
SOLAR_SYSTEM = Structure.from_facts("sistema_solar", [
    ("atrai", "sol", "planetas"),
    ("orbita", "planetas", "sol"),
    ("maior_que", "sol", "planetas"),
    ("centro", "sol"),
    ("periferia", "planetas"),
])

ATOM = Structure.from_facts("atomo", [
    ("atrai", "nucleo", "eletrons"),
    ("orbita", "eletrons", "nucleo"),
    ("maior_que", "nucleo", "eletrons"),
    ("centro", "nucleo"),
    ("periferia", "eletrons"),
])

TEACHER_STUDENT = Structure.from_facts("professor_aluno", [
    ("ensina", "professor", "aluno"),
    ("aprende", "aluno", "professor"),
    ("avalia", "professor", "aluno"),
    ("mais_experiente", "professor", "aluno"),
])

DOCTOR_PATIENT = Structure.from_facts("medico_paciente", [
    ("trata", "medico", "paciente"),
    ("recebe_tratamento", "paciente", "medico"),
    ("diagnostica", "medico", "paciente"),
    ("mais_experiente", "medico", "paciente"),
])


__all__ = [
    "Relation",
    "Structure",
    "StructuralMapping",
    "Analogy",
    "AnalogyEngine",
    "SOLAR_SYSTEM",
    "ATOM",
    "TEACHER_STUDENT",
    "DOCTOR_PATIENT",
]
