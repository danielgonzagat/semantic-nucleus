# Changelog

Todas as mudanças relevantes neste repositório serão documentadas aqui.

## [0.1.0] - 2025-11-21

- Adicionado LICENSE (MIT) e políticas de governança (CODE_OF_CONDUCT, CONTRIBUTING).
- Criados workflows de issues/PR, quickstart e pre-commit configurado.
- EquationSnapshot expandido com ontology/goals/ops_queue/quality + testes reforçados.
- Introduzido `svm.snapshots` com suporte a `.svms` (hash BLAKE3/BLAKE2b), restauração completa e assinaturas Ed25519 opcionais (`svm.signing`).
- Documentação (README, docs/quickstart.md, spec/svm.md) atualizada com CI, snapshots e instruções.
- Novo pacote `nsr_evo` para evolução simbólica determinística:
  - `run_text_learning` para execuções online com logging de episódios.
  - Indução de regras LIU→LIU (`kb_store`, `induction`, `policy`) + persistência JSONL.
  - Campo de energia (`nsr_evo.energy`) e ciclo CLI (`python -m nsr_evo.cli_cycle`) que só aceitam regras se a energia cair.
  - Testes cobrindo logging, API e CLI.
