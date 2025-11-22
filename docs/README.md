# Documentação pública

- `manifesto.md` — princípios éticos/técnicos e governança.
- `roadmap.md` — metas semestrais e métricas (MOPS, TTA, SRF, determinismo).
- `spec/*` — anexos normativos por camada (LIU, Compilers, NSR, ΣVM, Manifesto).
- `ian_langpacks.md` — guia para instinto IAN-Ω, gramáticas unificadas e benchmark de performance.
- `math_instinct.md` — documentação do instinto matemático e integração com o NSR.

## Como contribuir

1. Abra uma LIP (LIU Improvement Proposal) descrevendo motivação e impacto.
2. Atualize as especificações relevantes em `/spec` e adicione casos na suíte `tests/`.
3. Execute `python3 -m pytest` (ou `python3 -m pytest tests/cts` para o bundle mínimo); anexe o log + hash dos snapshots se aplicável.
4. Submeta PR com referência cruzada ao manifesto (capítulo "Governança").

## Conformidade

- `pytest.ini` garante que `src` esteja no `PYTHONPATH`.
- Tests categories: `liu`, `nsr`, `svm`, `compilers`, `cts`.
- Suite rápida de conformidade: `python3 -m pytest tests/cts`.
- Para validar apenas uma camada: `python3 -m pytest tests/svm -k encode`.
