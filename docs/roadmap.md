# Roadmap Núcleo Originário (2025–2030)

| Fase | Horizonte | Objetivos chave |
|------|-----------|-----------------|
| v0.3 | T1 2026   | Completar CTS básico (LIU/NSR/ΣVM/compilers), publicar LIPs iniciais |
| v0.5 | T2 2026   | Introduzir operadores Φ avançados (MAP/REDUCE/REWRITE) e snapshots SVMS | 
| v0.9 | T4 2026   | Versão candidata com ΣVM ABI estável, ferramentas de inspeção e pacote `code@1` | 
| v1.0 | 2027      | Congelar LIU-Core e ΣVM-ABI, publicar manifesto final, iniciar certificação externa |
| v1.x | 2027-2028 | Paralelismo determinístico no NSR, suporte a regras setoriais, biblioteca de ontologias |
| v2.0 | 2029      | Capabilities externas assinadas, prova parcial de preservação/progresso, bridging opcional ML |
| v3.0 | 2030+     | Exploradores de hardware dedicado, integração com pipelines industriais e regulação formal |

## Metas técnicas

- **CTS**: ampliar cobertura para >95% dos operadores, incluindo casos negativos e aleatoriedade controlada.
- **Ontologias**: publicar pacotes `core@1`, `code@1`, `domain/*` versionados.
- **Ferramentas**: CLI `nsr-run`, `svm-asm`, visualizador de `Trace`, gerador de snapshots com hashing BLAKE3.
- **Formalização**: iniciar prova Coq/Lean para preservation da LIU e terminologia do NSR.

## Métricas de sucesso

- *MOPS* (Meaning Ops/s) > 1e6 em CPU commodity.
- *TTA* (Time-to-answer) < 20 ms para consultas simples.
- *SRF* (Semantic Redundancy Factor) < 1.1 após NORMALIZE.
- 0 regressões de determinismo (hash mismatch) por release.
