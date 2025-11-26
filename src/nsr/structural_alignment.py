"""
Alinhamento Estrutural: Encontra padrões mesmo quando estruturas não são idênticas.

Permite aprender padrões mesmo quando estruturas são similares mas não exatas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from liu import Node, NodeKind, fingerprint, var


@dataclass(frozen=True)
class Alignment:
    """Alinhamento entre duas estruturas."""
    
    source: Node
    target: Node
    similarity: float  # 0.0 a 1.0
    mappings: Dict[str, str]  # Mapeia entidades de source para target
    common_structure: Node  # Estrutura comum (generalizada)


class StructuralAligner:
    """
    Alinha estruturas similares para encontrar padrões comuns.
    
    Exemplo:
    - "O carro tem rodas" → "A bicicleta tem pedais"
    - Alinhamento: ambos têm estrutura "X tem Y"
    - Padrão aprendido: "veiculo tem parte"
    """
    
    def align(self, struct1: Node, struct2: Node) -> Alignment | None:
        """Alinha duas estruturas e retorna similaridade."""
        
        # Calcula similaridade estrutural
        similarity = self._structural_similarity(struct1, struct2)
        
        if similarity < 0.3:  # Muito diferentes
            return None
        
        # Encontra mapeamentos de entidades
        mappings = self._find_entity_mappings(struct1, struct2)
        
        # Cria estrutura comum (generalizada)
        common = self._extract_common_structure(struct1, struct2, mappings)
        
        return Alignment(
            source=struct1,
            target=struct2,
            similarity=similarity,
            mappings=mappings,
            common_structure=common,
        )
    
    def _structural_similarity(self, struct1: Node, struct2: Node) -> float:
        """Calcula similaridade estrutural (0.0 a 1.0)."""
        
        # Se tipos diferentes, similaridade baixa
        if struct1.kind != struct2.kind:
            return 0.0
        
        # Se labels diferentes (e não são entidades), similaridade baixa
        if struct1.kind not in (NodeKind.ENTITY, NodeKind.VAR) and struct1.label != struct2.label:
            return 0.0
        
        # Similaridade baseada em estrutura
        if struct1.kind is NodeKind.STRUCT:
            return self._struct_similarity(struct1, struct2)
        
        if struct1.kind is NodeKind.REL:
            return self._rel_similarity(struct1, struct2)
        
        # Para outros tipos, compara labels
        if struct1.label == struct2.label:
            return 1.0
        
        return 0.0
    
    def _struct_similarity(self, struct1: Node, struct2: Node) -> float:
        """Similaridade entre estruturas."""
        fields1 = dict(struct1.fields)
        fields2 = dict(struct2.fields)
        
        # Campos comuns
        common_fields = set(fields1.keys()) & set(fields2.keys())
        total_fields = set(fields1.keys()) | set(fields2.keys())
        
        if not total_fields:
            return 1.0
        
        # Similaridade baseada em campos comuns
        field_similarity = len(common_fields) / len(total_fields)
        
        # Similaridade dos valores dos campos comuns
        value_similarities = []
        for field in common_fields:
            val1 = fields1[field]
            val2 = fields2[field]
            val_sim = self._structural_similarity(val1, val2)
            value_similarities.append(val_sim)
        
        avg_value_sim = sum(value_similarities) / len(value_similarities) if value_similarities else 0.0
        
        # Similaridade de argumentos
        arg_similarities = []
        min_args = min(len(struct1.args), len(struct2.args))
        for i in range(min_args):
            arg_sim = self._structural_similarity(struct1.args[i], struct2.args[i])
            arg_similarities.append(arg_sim)
        
        avg_arg_sim = sum(arg_similarities) / len(arg_similarities) if arg_similarities else 0.0
        
        # Combina similaridades
        return (field_similarity * 0.4) + (avg_value_sim * 0.4) + (avg_arg_sim * 0.2)
    
    def _rel_similarity(self, rel1: Node, rel2: Node) -> float:
        """Similaridade entre relações."""
        # Labels devem ser iguais
        if rel1.label != rel2.label:
            return 0.0
        
        # Similaridade dos argumentos
        if len(rel1.args) != len(rel2.args):
            return 0.0
        
        arg_similarities = []
        for arg1, arg2 in zip(rel1.args, rel2.args):
            arg_sim = self._structural_similarity(arg1, arg2)
            arg_similarities.append(arg_sim)
        
        return sum(arg_similarities) / len(arg_similarities) if arg_similarities else 0.0
    
    def _find_entity_mappings(
        self, struct1: Node, struct2: Node
    ) -> Dict[str, str]:
        """Encontra mapeamentos de entidades entre estruturas."""
        entities1 = self._extract_entities(struct1)
        entities2 = self._extract_entities(struct2)
        
        mappings: Dict[str, str] = {}
        
        # Mapeia entidades na mesma posição estrutural
        # Simplificação: mapeia por ordem de aparição
        min_len = min(len(entities1), len(entities2))
        for i in range(min_len):
            if entities1[i] != entities2[i]:  # Diferentes
                mappings[entities1[i]] = entities2[i]
        
        return mappings
    
    def _extract_entities(self, node: Node) -> List[str]:
        """Extrai todas as entidades de um nó."""
        entities = []
        
        if node.kind is NodeKind.ENTITY and node.label:
            entities.append(node.label)
        
        for arg in node.args:
            entities.extend(self._extract_entities(arg))
        
        if node.kind is NodeKind.STRUCT:
            for _, value in node.fields:
                entities.extend(self._extract_entities(value))
        
        return entities
    
    def _extract_common_structure(
        self, struct1: Node, struct2: Node, mappings: Dict[str, str]
    ) -> Node:
        """Extrai estrutura comum generalizada."""
        # Cria estrutura onde entidades mapeadas viram variáveis
        return self._generalize_with_mappings(struct1, mappings)
    
    def _generalize_with_mappings(
        self, node: Node, mappings: Dict[str, str]
    ) -> Node:
        """Generaliza nó substituindo entidades mapeadas por variáveis."""
        from liu import entity, relation, struct
        
        if node.kind is NodeKind.ENTITY and node.label:
            if node.label in mappings:
                # Substitui por variável
                return var("?X")
            return node
        
        if node.kind is NodeKind.REL:
            generalized_args = tuple(
                self._generalize_with_mappings(arg, mappings) for arg in node.args
            )
            return relation(node.label or "", *generalized_args)
        
        if node.kind is NodeKind.STRUCT:
            generalized_fields = tuple(
                (k, self._generalize_with_mappings(v, mappings))
                for k, v in node.fields
            )
            return struct(**dict(generalized_fields))
        
        # Para outros tipos, generaliza argumentos
        generalized_args = tuple(
            self._generalize_with_mappings(arg, mappings) for arg in node.args
        )
        return Node(
            kind=node.kind,
            label=node.label,
            args=generalized_args,
            fields=node.fields,
            value=node.value,
        )


def find_common_patterns(structures: List[Node], min_similarity: float = 0.5) -> List[Node]:
    """
    Encontra padrões comuns em uma lista de estruturas.
    
    Agrupa estruturas similares e extrai padrão comum.
    """
    aligner = StructuralAligner()
    groups: List[List[Node]] = []
    
    # Agrupa estruturas similares
    for struct in structures:
        added = False
        for group in groups:
            # Compara com primeiro da grupo
            alignment = aligner.align(group[0], struct)
            if alignment and alignment.similarity >= min_similarity:
                group.append(struct)
                added = True
                break
        
        if not added:
            groups.append([struct])
    
    # Extrai padrão comum de cada grupo
    common_patterns = []
    for group in groups:
        if len(group) < 2:
            continue
        
        # Alinha todas as estruturas do grupo
        alignments = []
        for i in range(1, len(group)):
            alignment = aligner.align(group[0], group[i])
            if alignment:
                alignments.append(alignment)
        
        if alignments:
            # Usa estrutura comum do primeiro alinhamento
            common_patterns.append(alignments[0].common_structure)
    
    return common_patterns


__all__ = [
    "Alignment",
    "StructuralAligner",
    "find_common_patterns",
]
