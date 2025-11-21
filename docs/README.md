# Documentação pública

- `manifesto.md` — princípios éticos/técnicos e governança.
- `roadmap.md` — metas semestrais e métricas (MOPS, TTA, SRF, determinismo).
- `spec/*` — anexos normativos por camada (LIU, Compilers, NSR, ΣVM, Manifesto).

## Como contribuir

1. Abra uma LIP (LIU Improvement Proposal) descrevendo motivação e impacto.
2. Atualize as especificações relevantes em `/spec` e adicione casos na suíte `tests/`.
3. Execute `python3 -m pytest`; anexe o log + hash dos snapshots se aplicável.
4. Submeta PR com referência cruzada ao manifesto (capítulo "Governança").

## Conformidade

- `pytest.ini` garante que `src` esteja no `PYTHONPATH`.
- Tests categories: `liu`, `nsr`, `svm`, `compilers`.
- Para validar apenas uma camada: `python3 -m pytest tests/svm -k encode`.
