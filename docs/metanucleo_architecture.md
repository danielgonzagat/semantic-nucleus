# Arquitetura Determinística do Metanúcleo

O Metanúcleo opera como uma cadeia irreversível reversível que leva qualquer entrada a uma forma de meta-representação e, a partir dela, produz meta-cálculo executável no hardware. Esta nota descreve as três visões oficiais do sistema — macro arquitetura, pipeline interno e topologia cognitiva — e documenta o estágio Meta-LER implementado pelo novo `MetaTransformer`.

## Meta-LER com `MetaTransformer`

O estágio Meta-LER recebe texto cru e determina, de maneira determinística, qual rota deve ser aplicada:

- **Matemática** (`MetaRoute.MATH`): ativa o `math_bridge`/`Math-Core` quando a entrada é equação ou instrução aritmética.
- **Lógica** (`MetaRoute.LOGIC`): roteia comandos `FACT/IF/QUERY` para o `logic_bridge`.
- **Código** (`MetaRoute.CODE`): detecta snippets Python determinísticos via `code_bridge` e converte diretamente para relações LIU de programação.
- **Instinto Linguístico** (`MetaRoute.INSTINCT`): aciona o IAN-Ω quando a frase corresponde a um instinto nativo (saudações, diagnósticos etc.).
- **Parser textual** (`MetaRoute.TEXT`): cai no LxU + PSE e produz um `STRUCT` LIU completo, anexando metadados de idioma.

Cada rota devolve um `MetaTransformResult` com a `struct_node`, contexto pré-semeado (sempre carrega `meta_route` + `meta_input` para auditoria), qualidade estimada e etiqueta de trace (`trace_label`). O `run_text_full` usa esse resultado para alimentar o ISR inicial e também publica `meta_summary = (meta_route, meta_input, meta_output, meta_plan)` — serializado como `{route, language, input_size, input_preview, answer, quality, halt, phi_plan_chain, phi_plan_ops}` — caracterizando formalmente o estágio **Meta-Resultado** (o CLI expõe o mesmo pacote via `--include-meta` e o helper `nsr.meta_summary_to_dict` produz o dicionário em Python). O `SessionCtx.meta_history` retém os últimos pacotes meta, com retenção determinística definida por `Config.meta_history_limit`.

O fallback textual não é mais “cego”: antes de despachar para o loop Φ, o MetaTransformer executa `lc_parse` e constrói um `lc_meta` LIU usando `nsr.meta_structures`. Esse pacote traz tokens normalizados, sequência semântica, termo LC-Ω e, quando identificado, o `meta_calculation` correspondente (`STATE_QUERY`, `FACT_QUERY`, `COMMAND_ROUTE`, etc.). Tanto a STRUCT inicial quanto o contexto pré-semeado carregam o `lc_meta`, garantindo que Meta-LER entregue ao próximo estágio uma visão explícita do meta-cálculo planejado, mesmo quando ainda não existe `preseed_answer`.

Além disso, sempre que o `lc_meta` contém um `meta_calculation`, o plano ΣVM emitido para a rota TEXT é parametrizado por esse operador (ex.: consultas usam `Φ_NORMALIZE → Φ_INFER → Φ_SUMMARIZE`, afirmações carregam `Φ_NORMALIZE → Φ_ANSWER → Φ_EXPLAIN → Φ_SUMMARIZE`) **e** finaliza com `PUSH_CONST → STORE_ANSWER` escrevendo um nó `lc_meta_calc` com o cálculo detectado. Assim, o estágio Meta-LER já informa ao executor de hardware exatamente qual sequência de Φ deve ser disparada e registra no hardware qual cálculo LC-Ω fundamenta o plano, reforçando o acoplamento Meta-LER → Meta-CALCULAR.

Antes mesmo de decidir a rota, o `language_detector` aplica heurísticas determinísticas sobre o texto bruto para identificar idioma natural e dialetos de código (Python/Rust/Elixir/JS). O resultado vira um nó `language_profile` anexado ao contexto inicial, alimenta `SessionCtx.language_hint` e garante que o parser/tokenizador use o léxico correto, além de sinalizar quando o conteúdo provavelmente é código antes do `code_bridge`.

Quando o perfil aponta para código Python (mesmo sem passar pelo `code_bridge`), geramos um `code_ast` LIU via `nsr.code_ast.build_python_ast_meta`: o AST serializado inclui o tronco completo (limitado a 512 nós), contagem de tipos e marcação de truncamento. Esse nó acompanha o contexto e o `meta_summary`, garantindo que entradas de código já entrem no Meta-LER como estrutura auditável e não apenas como texto.

Para rotas matemáticas, o Math-Core produz instruções determinísticas (`MathInstruction`). O `math_bridge` converte cada instrução em um `math_ast` LIU (`nsr.math_ast.build_math_ast_node`), anexando operador, expressão, operandos e valor numérico, de modo que toda resposta matemática carregue o cálculo em forma de árvore e permita rastrear o meta-cálculo até o hardware.

Planos ΣVM emitidos por qualquer rota (MATH/LOGIC/CODE/INSTINCT/TEXT) agora geram um `meta_plan` rico em metadados tanto no contexto inicial quanto no `meta_summary`. Esse nó inclui: descrição humana (`phi_plan_description`), digest BLAKE2b das instruções+constantes (`phi_plan_digest`), contagem de instruções (`phi_plan_program_len`), contagem de constantes (`phi_plan_const_len`) e, sempre que existir, a cadeia Φ (`phi_plan_chain` + `phi_plan_ops`). O CLI expõe os mesmos campos via `--include-meta`, permitindo auditar o bytecode despachado para o hardware independentemente da rota.

O `RunOutcome` expõe diretamente o `lc_meta`, e o CLI pode serializá-lo via `--include-lc-meta`, facilitando auditorias sobre quais tokens/semânticas no LC-Ω originaram determinado meta-cálculo.

O pacote `meta_summary` também passa a carregar o `meta_calculation` e o `meta_plan` (cadeia Φ derivada), garantindo que o mesmo cálculo LC-Ω e sua sequência de operadores estejam disponíveis tanto no histórico meta quanto no `lc_meta_calc` anexado ao contexto.

Para fechar o elo, o runtime agora lê o `lc_meta_calc` antes de iniciar o loop Φ, injeta na fila de operadores a mesma sequência prevista para a ΣVM **e** registra o evento `Φ_PLAN[...]` no `trace`: `STATE_QUERY` passa imediatamente por `NORMALIZE → INFER → SUMMARIZE`, `STATE_ASSERT` executa `NORMALIZE → ANSWER → EXPLAIN → SUMMARIZE`, comandos e saudações recebem seus fluxos específicos. O plano LC-Ω deixa de ser apenas metadata e passa a comandar, de forma determinística e auditável, tanto o hardware quanto o executor simbólico.

Quando a rota já fornece um `preseed_answer`, o `MetaTransformResult` também embute um `MetaCalculationPlan`. Este plano descreve um programa ΣVM mínimo (atualmente: `PUSH_CONST → STORE_ANSWER → HALT`) que reproduz, em nível de hardware simbólico, o mesmo resultado pré-semeado. É o primeiro passo concreto da etapa **Meta-CALCULAR**, permitindo despachar diretamente para a ΣVM qualquer meta-resposta determinística sem depender do loop Φ. O runtime executa esse plano via `execute_meta_plan`, registrando o snapshot completo na nova estrutura `MetaCalculationResult`.

O `Config.calc_mode` define como o plano é usado:

- `hybrid` (padrão): roda o loop Φ completo e executa o plano para auditoria/consistência.
- `plan_only`: retorna imediatamente o resultado proveniente da ΣVM (`HALT=PLAN_EXECUTED`), útil para caminhos em que o meta-cálculo já é definitivo.
- `skip`: ignora totalmente os planos, preservando o comportamento clássico do NSR.

## Macro Arquitetura Oficial

```
                         ┌─────────────────────────────┐
                         │         ENTRADA              │
                         │  Texto • Código • Matemática │
                         └───────────────┬─────────────┘
                                         │
                                         ▼
                         ┌─────────────────────────────┐
                         │     META-TRANSFORMADOR      │
                         │ (Linguagem → META-Linguagem)│
                         │ (Código → META-Programação) │
                         │ (Matemática → META-Matemát.)│
                         └───────────────┬─────────────┘
                                         │
                                         ▼
                         ┌─────────────────────────────┐
                         │    META-REPRESENTAÇÃO       │
                         │   (Estruturas universais)   │
                         │       (LIU / META)          │
                         └───────────────┬─────────────┘
                                         │
                                         ▼
                         ┌─────────────────────────────┐
                         │      META-CÁLCULO           │
                         │ Regras Φ-meta • Inferência  │
                         │ Reescrita • Normalização    │
                         │ Redução → Forma Computável  │
                         └───────────────┬─────────────┘
                                         │
                                         ▼
                         ┌─────────────────────────────┐
                         │ EXECUTOR ATÔMICO DE CÁLCULO │
                         │      (Hardware: CPU)         │
                         │ Redução total → Resultado    │
                         └───────────────┬─────────────┘
                                         │
                                         ▼
                         ┌─────────────────────────────┐
                         │       META-RESULTADO         │
                         │  (Meta-estruturas pós-cálc.) │
                         └───────────────┬─────────────┘
                                         │
                                         ▼
                         ┌─────────────────────────────┐
                         │    META-SÍNTESE / EXPRESSÃO │
                         │   META → Linguagem/Código   │
                         └───────────────┬─────────────┘
                                         │
                                         ▼
                         ┌─────────────────────────────┐
                         │           SAÍDA             │
                         │ Resposta • Código • Texto   │
                         └─────────────────────────────┘
```

## Pipeline do Meta-Cálculo

```
┌─────────────────────────────────────────────────────────────┐
│                         METANÚCLEO                           │
└─────────────────────────────────────────────────────────────┘

Entrada ─────────────────────────────────────────────────────────►
      Texto • Código • Matemática • Dados

                    ▼
        ┌────────────────────┐
        │ META-PARSER        │
        │ (Normaliza entrada)│
        └───────┬────────────┘
                ▼
        ┌────────────────────┐
        │ META-IR (LIU/META) │
        │ Estrutura universal│
        └───────┬────────────┘
                ▼
        ┌────────────────────┐
        │ META-RACIOCÍNIO    │
        │   Φ-meta Operators │
        │ Inferência/Reescr. │
        └───────┬────────────┘
                ▼
        ┌────────────────────┐
        │ META-CÁLCULO       │
        │ Redução simbólica  │
        │ → cálculo real     │
        └───────┬────────────┘
                ▼
        ┌────────────────────┐
        │ EXECUTOR DE CÁLCULO│
        │   (Hardware CPU)   │
        └───────┬────────────┘
                ▼
        ┌────────────────────┐
        │ META-RESULTADO     │
        │ Cálculo → Estrutura│
        └───────┬────────────┘
                ▼
        ┌────────────────────┐
        │ META-SÍNTESE       │
        │ Estrutura → Saída  │
        └───────┬────────────┘
                ▼
Saída ◄──────────────────────────────────────────────────────────
   Resposta • Código • Texto
```

## Topologia Cognitiva

```
                   ┌────────────────────────┐
                   │      META-PARSER       │
                   │ Linguagem / Código /   │
                   │ Matemática → META      │
                   └───────────┬────────────┘
                               │
                      ┌────────▼─────────┐
                      │ META-STRUCTURES  │
                      │ LIU • META-Tree  │
                      │ Ontologia interna│
                      └──────────┬────────┘
                                 │
               ┌─────────────────┼──────────────────┐
               ▼                 ▼                  ▼
   ┌──────────────────┐ ┌──────────────────┐ ┌────────────────────┐
   │ META-LÓGICA      │ │ META-MATEMÁTICA  │ │ META-PROGRAMAÇÃO   │
   │ Regras Φ-meta     │ │ Reescrita alg.   │ │ AST universal      │
   │ Inferência        │ │ Simplificação    │ │ IR simbólico       │
   └─────────┬──────────┘ └────────┬─────────┘ └─────────┬──────────┘
             │                     │                     │
             └─────────────────────┼─────────────────────┘
                                   ▼
                        ┌──────────────────────┐
                        │     META-CÁLCULO     │
                        │ Redução → Cálculo     │
                        │ Execução determinística│
                        └──────────┬────────────┘
                                   ▼
                       ┌────────────────────────┐
                       │      META-SÍNTESE      │
                       │ META → Linguagem/Código│
                       └──────────┬─────────────┘
                                  ▼
                             SAÍDA FINAL
```

Estas três camadas formam o guia de implementação contínua. O `MetaTransformer` resolve o primeiro gargalo (Meta-LER), garantindo que toda entrada seja imediatamente normalizada em LIU antes de acionar os operadores Φ. Próximos passos evolutivos devem expandir os módulos Meta-PENSAR, Meta-CALCULAR e Meta-Expressar seguindo o manifesto determinístico descrito no README.
