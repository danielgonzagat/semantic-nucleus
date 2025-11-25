"""
Classificador Semântico Baseado em Compressão (NCD).

Implementa a Distância Normalizada de Compressão para classificação de texto
sem o uso de Redes Neurais ou Embeddings vetoriais.

Baseado na teoria da Complexidade de Kolmogorov: objetos similares compartilham
informação, tornando sua compressão conjunta mais eficiente do que a soma
de suas compressões individuais.
"""

import lzma
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

@dataclass
class Exemplar:
    text: str
    label: str
    compressed_size: int

class NCDClassifier:
    def __init__(self, preset: str = "lzma"):
        self.exemplars: List[Exemplar] = []
        self.preset = preset
    
    def _compress(self, data: str) -> int:
        """Retorna o tamanho em bytes da string comprimida."""
        encoded = data.encode('utf-8')
        # Preset 4: equilíbrio entre compressão e velocidade para textos curtos.
        return len(lzma.compress(encoded, preset=4))

    def train(self, data: Dict[str, List[str]]):
        """
        'Treina' o classificador armazenando exemplos e seus tamanhos comprimidos.
        data: Dicionário onde chave é o label (intenção) e valor é lista de frases de exemplo.
        """
        self.exemplars.clear()
        for label, sentences in data.items():
            for text in sentences:
                size = self._compress(text)
                self.exemplars.append(Exemplar(text=text, label=label, compressed_size=size))

    def predict(self, query: str, top_k: int = 1) -> List[Tuple[str, float]]:
        """
        Classifica a query comparando sua entropia com os exemplos conhecidos.
        Retorna lista de (label, score) onde score é similaridade (1 - NCD médio).
        """
        query_len = self._compress(query)
        scores: List[Tuple[float, str]] = []

        for ex in self.exemplars:
            combined = query + " " + ex.text
            combined_len = self._compress(combined)
            
            # NCD(x, y) = (C(xy) - min(C(x), C(y))) / max(C(x), C(y))
            min_len = min(query_len, ex.compressed_size)
            max_len = max(query_len, ex.compressed_size)
            
            if max_len == 0:
                ncd = 0.0
            else:
                ncd = (combined_len - min_len) / max_len
            
            # Clip NCD entre 0 e 1.2
            ncd = min(max(ncd, 0.0), 1.2)
            
            similarity = 1.0 - ncd
            scores.append((similarity, ex.label))

        # Ordenar pelos vizinhos mais próximos (menor NCD, maior similarity)
        scores.sort(key=lambda x: x[0], reverse=True)
        
        # k-NN Voting: Pega os K vizinhos mais próximos e faz votação ponderada
        k_neighbors = min(len(scores), 7)
        candidates = scores[:k_neighbors]
        
        label_weights: Dict[str, float] = {}
        label_counts: Dict[str, int] = {}
        
        for score, label in candidates:
            # Peso quadrático para dar muito mais valor a matches muito próximos
            weight = score * score
            label_weights[label] = label_weights.get(label, 0.0) + weight
            label_counts[label] = label_counts.get(label, 0) + 1
            
        final_scores = []
        for label, total_weight in label_weights.items():
            # Normaliza pelo número de hits (average linkage)
            avg_score = total_weight / label_counts[label]
            final_scores.append((label, avg_score))
            
        final_scores.sort(key=lambda x: x[1], reverse=True)
        return final_scores[:top_k]

    def debug_distances(self, query: str) -> List[dict]:
        """Retorna detalhes brutos para auditoria."""
        query_len = self._compress(query)
        details = []
        for ex in self.exemplars:
            combined = query + " " + ex.text
            combined_len = self._compress(combined)
            min_len = min(query_len, ex.compressed_size)
            max_len = max(query_len, ex.compressed_size)
            ncd = (combined_len - min_len) / max_len if max_len > 0 else 0
            details.append({
                "label": ex.label,
                "text": ex.text,
                "ncd": ncd,
                "similarity": 1.0 - ncd
            })
        return sorted(details, key=lambda x: x["ncd"])
