# Changelog

Todas as mudanças relevantes neste repositório serão documentadas aqui.

## [Unreleased]

- Adicionado operador determinístico `code/EVAL_PURE` ao NSR para avaliar estruturas `binop` (somar, multiplicar, dividir, concatenar texto) e anexar os resultados/erros ao contexto com aumento garantido de qualidade.
- Criados testes de runtime cobrindo avaliações numéricas/narrativas e a sinalização de erros determinística.
- Criado `MathInstinct` + `math_bridge`, permitindo que expressões (“2+2”, “quanto é 3*5?”) sejam respondidas antes do loop Φ, com suporte a `abs`/`sqrt` e compartilhamento do charset do IAN.
- IAN-Ω expandido com intents de agradecimento, despedida, confirmação e perguntas factuais multilíngues, novos verbos/conjugações e testes de runtime cobrindo o fluxo completo.
- Adicionados utilitários de governança:
  - `scripts/langpack_check.py --fail-on-warn` para auditoria dos LangPacks (agora executado em CI).
  - `scripts/ian_bench.py` com thresholds (`--max-p95-ms`, `--max-peak-mib`) e medição de textos longos.
  - `scripts/langpack_dsl.py` para gerar pacotes a partir de uma DSL JSON.
- Documentação ampliada (`docs/roadmap_official.md`, `docs/math_instinct.md`, `docs/security_checklist.md`) e README atualizado com roadmap v1.0→v2.0 e checklist de segurança.
- Parser sintático Fase 1.1 implementado: `nsr.parser.build_struct` agora usa perfis (`nsr.grammar`) para identificar sujeito/verbo/objeto, tipo de sentença, negação e foco de pergunta em PT/EN/ES/FR/IT; `nsr.runtime.run_text_full` passa `language`/`text_input` e novos testes (`tests/nsr/test_parser.py`) cobrem cenários afirmativos/interrogativos/imperativos.
- Lexicalizador expandido: `tokenize` preserva superfícies originais, `LANGUAGE_PACKS` inclui italiano e recebe automaticamente >100 verbos/conjugações por idioma via `nsr.langpacks_verbs`; grammars e LangPacks foram atualizados para garantir no mínimo 100 verbos canônicos em PT/EN/ES/FR/IT e alimentar o parser/IAN.
- Introduzido `nsr.meta_structures` com serializadores LC-Ω → LIU (`lc_term_to_node`, `meta_calculation_to_node`, `build_lc_meta_struct`), testes dedicados e integração no `MetaTransformer`: toda rota TEXT agora anexa um `lc_meta` (tokens, sequência semântica e meta-cálculo quando disponível) tanto na STRUCT quanto no contexto, conectando o estágio Meta-LER ao Meta-CÁLCULO, gerando planos ΣVM parametrizados pelo `meta_calculation` (`STATE_QUERY` → `Φ_NORMALIZE · Φ_INFER · Φ_SUMMARIZE`, `STATE_ASSERT` → `Φ_NORMALIZE · Φ_ANSWER · Φ_EXPLAIN · Φ_SUMMARIZE`, etc.), escrevendo um `lc_meta_calc` no `answer` via `PUSH_CONST → STORE_ANSWER`, expondo o `lc_meta` no `RunOutcome`/CLI (`--include-lc-meta`) e adicionando `meta_calculation` ao `meta_summary`/`meta_history`.
- `meta_summary` passa a incluir o bloco `meta_calc_exec`, espelhando cada execução ΣVM: rota/descrição do plano, flag `consistent`, erro (se houver), fingerprint da resposta e `snapshot_digest` (BLAKE2b). O CLI expõe os campos `calc_exec_*`, fechando o elo Meta-CALCULAR → Execução física.
- Novo `nsr.meta_calculus_router` compartilha o pipeline Φ das rotas textuais entre a ΣVM e o orquestrador: `MetaTransformResult` agora carrega o `meta_calculation`, o runtime injeta `NORMALIZE/INFER/SUMMARIZE` (ou `ANSWER/EXPLAIN`) diretamente na fila Φ quando um `lc_meta_calc` é detectado, registra o evento `Φ_PLAN[...]` no `trace`, persiste o `meta_plan` dentro de `meta_summary`/CLI (`phi_plan_chain`/`phi_plan_ops`) e novos testes/documentação cobrem o fluxo sincronizado Meta-LER → Meta-CALCULAR.
- Planos ΣVM agora deixam rastros auditáveis por rota: o `MetaTransformer` anexa `meta_plan` com descrição, digest BLAKE2b das instruções+constantes e contagens (`phi_plan_description`, `phi_plan_digest`, `phi_plan_program_len`, `phi_plan_const_len`) tanto no contexto quanto no `meta_summary`/CLI, cobrindo rotas math/logic/code/instinct/text com novos testes e documentação.
- Detector determinístico de idioma/dialeto (`nsr.language_detector`) alimenta `MetaTransformer`: cada entrada gera um nó `language_profile` (idioma natural, categoria text/code, confiança, pistas) anexado ao contexto/meta_summary, atualiza `SessionCtx.language_hint` antes do parser e identifica dialetos de código (Python/Rust/Elixir/JS) para orientar o roteamento; novos testes cobrem heurísticas e integração.
- Conversão estruturada de código: `nsr.code_ast.build_python_ast_meta` serializa ASTs Python para LIU (`code_ast`) e `nsr.code_ast.build_rust_ast_meta` gera outlines determinísticos para Rust (funções, parâmetros, retorno, corpo). O `code_bridge` usa esses nós como `code_ast` tanto na rota CODE quanto quando o detector sinaliza dialetos de código, expondo `code_ast_*` no `meta_summary`/CLI com contagens, linguagem e flag de truncamento.
- Auditoria end-to-end: todo `meta_summary` agora carrega um `meta_digest` (BLAKE2b sobre rota/inputs/ASTs/meta_calc), exposto pelo CLI e pela API via `meta_summary_to_dict`, permitindo verificar que nenhuma etapa entre Meta-LER e Meta-Resultado foi adulterada.
- Operador Φ `REWRITE_CODE`: detecta `code_ast` no contexto, gera resumos determinísticos (`code_ast_summary`) e relações `code/FUNCTION_COUNT`, aumentando a qualidade e preparando o Meta-PENSAR para reescritas formais antes de `Φ_NORMALIZE`/`Φ_INFER`.

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
