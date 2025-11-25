# Arquitetura Determinística do Metanúcleo

O Metanúcleo opera como uma cadeia irreversível reversível que leva qualquer entrada a uma forma de meta-representação e, a partir dela, produz meta-cálculo executável no hardware. Esta nota descreve as três visões oficiais do sistema — macro arquitetura, pipeline interno e topologia cognitiva — e documenta o estágio Meta-LER implementado pelo novo `MetaTransformer`.

## Meta-LER com `MetaTransformer`

O estágio Meta-LER recebe texto cru e determina, de maneira determinística, qual rota deve ser aplicada:

- **Matemática** (`MetaRoute.MATH`): ativa o `math_bridge`/`Math-Core` para expressões aritméticas e aceita comandos `POLY {json}` (fatoração determinística via `nsr.polynomial_engine`), devolvendo ast/fatores auditáveis.
- **Lógica** (`MetaRoute.LOGIC`): roteia comandos `FACT/IF/QUERY` para o `logic_bridge`.
- **Estatística / Bayes / Markov** (`MetaRoute.STAT`): interpreta comandos `BAYES {json}` (redes bayesianas discretas) e `MARKOV {json}` (cadeias/hmms determinísticos), executando inferência exata via `nsr.bayes_engine.BayesNetwork` ou `nsr.markov_engine.MarkovModel`, sempre emitindo meta-estruturas auditáveis e plano ΣVM direto (`stat_direct_answer`).
- **Código** (`MetaRoute.CODE`): detecta snippets Python determinísticos via `code_bridge` e converte diretamente para relações LIU de programação.
- **Instinto Linguístico** (`MetaRoute.INSTINCT`): aciona o IAN-Ω quando a frase corresponde a um instinto nativo (saudações, diagnósticos etc.).
- **Parser textual** (`MetaRoute.TEXT`): cai no LxU + PSE e produz um `STRUCT` LIU completo, anexando metadados de idioma.

Cada rota devolve um `MetaTransformResult` com a `struct_node`, contexto pré-semeado (sempre carrega `meta_route` + `meta_input` para auditoria), qualidade estimada e etiqueta de trace (`trace_label`). O `run_text_full` usa esse resultado para alimentar o ISR inicial e também publica `meta_summary = (meta_route, meta_input, meta_output, meta_plan)` — serializado como `{route, language, input_size, input_preview, answer, quality, halt, phi_plan_chain, phi_plan_ops}` — caracterizando formalmente o estágio **Meta-Resultado** (o CLI expõe o mesmo pacote via `--include-meta` e o helper `nsr.meta_summary_to_dict` produz o dicionário em Python). O `SessionCtx.meta_history` retém os últimos pacotes meta, com retenção determinística definida por `Config.meta_history_limit`.

O fallback textual não é mais “cego”: antes de despachar para o loop Φ, o MetaTransformer executa `lc_parse` e constrói um `lc_meta` LIU usando `nsr.meta_structures`. Esse pacote traz tokens normalizados, sequência semântica, termo LC-Ω e, quando identificado, o `meta_calculation` correspondente (`STATE_QUERY`, `FACT_QUERY`, `COMMAND_ROUTE`, etc.). Tanto a STRUCT inicial quanto o contexto pré-semeado carregam o `lc_meta`, garantindo que Meta-LER entregue ao próximo estágio uma visão explícita do meta-cálculo planejado, mesmo quando ainda não existe `preseed_answer`.

Além disso, sempre que o `lc_meta` contém um `meta_calculation`, o plano ΣVM emitido para a rota TEXT é parametrizado por esse operador (ex.: consultas usam `Φ_NORMALIZE → Φ_INFER → Φ_SUMMARIZE`, afirmações carregam `Φ_NORMALIZE → Φ_ANSWER → Φ_EXPLAIN → Φ_SUMMARIZE`) **e** finaliza com `PUSH_CONST → STORE_ANSWER` escrevendo um nó `lc_meta_calc` com o cálculo detectado. Assim, o estágio Meta-LER já informa ao executor de hardware exatamente qual sequência de Φ deve ser disparada e registra no hardware qual cálculo LC-Ω fundamenta o plano, reforçando o acoplamento Meta-LER → Meta-CALCULAR.

Antes mesmo de decidir a rota, o `language_detector` aplica heurísticas determinísticas sobre o texto bruto para identificar idioma natural e dialetos de código (Python/Rust/Elixir/JS). O resultado vira um nó `language_profile` anexado ao contexto inicial, alimenta `SessionCtx.language_hint` e garante que o parser/tokenizador use o léxico correto, além de sinalizar quando o conteúdo provavelmente é código antes do `code_bridge`.

O mesmo estágio agora consulta o `MultiOntologyManager`: domínios `core`, `code`, `medical`, `legal` e `finance` são registrados por sessão, e a partir dos tokens/entidades presentes no `struct_node` o gerenciador infere quais domínios devem ser ativados. A ativação atualiza imediatamente `SessionCtx.kb_ontology` e gera um nó `ontology_scope` no contexto/meta_summary descrevendo domínios ativos/inferidos, contagem de relações por domínio e um digest BLAKE2b do escopo; esse nó prova exatamente quais ontologias suportaram a resposta e fecha a auditoria “entrada → ontologia → cálculo”.

Quando o perfil aponta para código Python (mesmo sem passar pelo `code_bridge`), geramos um `code_ast` LIU via `nsr.code_ast.build_python_ast_meta`: o AST serializado inclui o tronco completo (limitado a 512 nós), contagem de tipos e marcação de truncamento. Para Rust, um outline determinístico (`nsr.code_ast.build_rust_ast_meta`) lista todas as funções detectadas (assinaturas, parâmetros, retorno, corpo) antes mesmo do frontend completo existir. Esses nós acompanham o contexto e o `meta_summary`, garantindo que entradas de código já entrem no Meta-LER como estrutura auditável e não apenas como texto.

Para rotas matemáticas, o Math-Core produz instruções determinísticas (`MathInstruction`). O `math_bridge` converte cada instrução em um `math_ast` LIU (`nsr.math_ast.build_math_ast_node`), anexando operador, expressão, operandos e valor numérico, de modo que toda resposta matemática carregue o cálculo em forma de árvore e permita rastrear o meta-cálculo até o hardware.

Planos ΣVM emitidos por qualquer rota (MATH/LOGIC/CODE/INSTINCT/TEXT) agora geram um `meta_plan` rico em metadados tanto no contexto inicial quanto no `meta_summary`. Esse nó inclui: descrição humana (`phi_plan_description`), digest BLAKE2b das instruções+constantes (`phi_plan_digest`), contagem de instruções (`phi_plan_program_len`), contagem de constantes (`phi_plan_const_len`) e, sempre que existir, a cadeia Φ (`phi_plan_chain` + `phi_plan_ops`). O CLI expõe os mesmos campos via `--include-meta`, permitindo auditar o bytecode despachado para o hardware independentemente da rota. Antes de carregar qualquer programa na ΣVM, o verificador estático (`svm.verifier.verify_program`) garante operandos válidos, saltos seguros e `HALT` obrigatório; se a validação falha, `execute_meta_plan` aborta com erro determinístico. Além disso, o `meta_summary` passa a carregar um nó `meta_equation`, derivado do `EquationSnapshot`, com digests de entrada/resposta, qualidade, contagens/hashes de ontologia/relações/contexto/goals/fila Φ **e** os deltas determinísticos em relação à execução anterior (delta de qualidade e delta de contagem/digest por seção), acompanhados de um `trend` categórico (`initial`/`expanding`/`stable`/`regressing`) — o pacote completo conecta entrada → equação → plano ΣVM → execução e monitora a evolução simbólica passo a passo.

Sempre que um plano é executado na ΣVM, registramos um bloco `meta_calc_exec` dentro do `meta_summary`: rota e descrição do plano, flag `consistent`, erro (quando ocorre), fingerprint da resposta e `snapshot_digest` calculado com BLAKE2b-128 (digest_size=16, sem chave/salt) do snapshot ΣVM serializado com `pc` e `stack_depth`. Os mesmos campos aparecem no CLI como `calc_exec_*`, garantindo que o Meta-Cálculo esteja ligado à execução física auditável.

Por fim, cada `meta_summary` recebe um `meta_digest` (BLAKE2b-128, digest_size=16, sem chave/salt, sobre a sequência `meta_route/meta_input/.../ASTs`), o que permite verificar end-to-end que nenhuma etapa Meta-LER → Meta-Resultado foi adulterada. Esse hash acompanha tanto a API (`meta_summary_to_dict`) quanto o CLI.

O módulo de operadores Φ foi expandido com `REWRITE_CODE`: sempre que há um `code_ast` no contexto, essa Φ gera resumos determinísticos (`code_ast_summary`) e relações `code/FUNCTION_COUNT`, alimentando o Meta-PENSAR com estatísticas estruturais do código antes de `Φ_NORMALIZE`/`Φ_INFER`. É o primeiro passo da biblioteca de reescrita formal para programação.
O `RunOutcome` expõe diretamente o `lc_meta`, e o CLI pode serializá-lo via `--include-lc-meta`, facilitando auditorias sobre quais tokens/semânticas no LC-Ω originaram determinado meta-cálculo.

O pacote `meta_summary` também passa a carregar o `meta_calculation` e o `meta_plan` (cadeia Φ derivada), garantindo que o mesmo cálculo LC-Ω e sua sequência de operadores estejam disponíveis tanto no histórico meta quanto no `lc_meta_calc` anexado ao contexto.

O estágio **Meta-Pensar** agora deixa rastros explícitos: `meta_reasoner` sintetiza cada passo Φ do `trace`, gera estatísticas por operador e produz um digest auditável associado à execução, além de registrar `delta_quality` e `delta_relations` para cada `reasoning_step`, quantificando exatamente o impacto de cada Φ sobre o grafo LIU. Em seguida, o novo módulo **Meta-Expressar** coleta a resposta LIU final, referencia o digest de raciocínio e materializa um nó `meta_expression` com preview determinístico, idioma, rota, fingerprint e um `memory_context` contendo resumos/digests das memórias utilizadas. Ambos os blocos são anexados ao `meta_summary`, permitindo reconstruir — de entrada até a expressão final — toda a cadeia Meta-LER → Meta-Pensar → Meta-Expressar com reversibilidade comprovável.

Para tornar o raciocínio ativo, os operadores Φ `TRACE_SUMMARY`, `MEMORY_RECALL` e `MEMORY_LINK` consomem o `meta_reasoner` e os nós `meta_memory`, injetam `trace_summary` e `memory_link` diretamente no contexto LIU (estatísticas de Φ, digestos anteriores e vínculos explícitos) e alimentam os estágios seguintes com estatísticas simbólicas prontas para reuso determinístico em memória, reescrita e síntese. Quando há memória disponível, o LC-Ω promove consultas/textos para `STATE_FOLLOWUP`, `FACT_FOLLOWUP` ou `COMMAND_FOLLOWUP`: o plano ΣVM inserido executa `Φ_MEMORY_RECALL → Φ_MEMORY_LINK` antes das Φ normais, garantindo continuidade multi-turno auditável para perguntas, fatos e comandos. Em paralelo, `Φ_NORMALIZE` evoluiu para `normalize_summary`: além de normalizar e ordenar o grafo LIU, ele deduplica relações repetidas, registra (total, deduplicados, removidos) no contexto e aumenta a qualidade quando elimina redundâncias, de forma que cada linha do trace indique exatamente o impacto estrutural daquela Φ. Quando `Config.normalize_aggressive=True`, o mesmo operador aplica heurísticas determinísticas para considerar apenas os argumentos não textuais como assinatura, escolher a forma mais curta/leves das relações redundantes e registrar `aggressive_removed`, informação que também é propagada no trace/meta_reasoner (`NORMALIZE[tot=...,dedup=...,rem=...,agg=...]`). Para lógica proposicional, `Φ_PROVE` integra o `logic_engine` diretamente ao loop: consultas `FACT_QUERY/FACT_FOLLOWUP` produzem um `logic_proof` determinístico com fatos atuais, derivadas e a verdade do enunciado, espelhado tanto no contexto quanto no `meta_summary` por meio de um bloco `meta_proof` consumível pelo CLI (`--include-proof`).

O MetaPlanner e a biblioteca de síntese formal também operam sem intervenção humana: `detect_plan_goal` dispara `Φ_PLAN_DECOMPOSE`, e o runtime monitora os `plan_decompose` no contexto para enfileirar automaticamente `Φ_SYNTH_PLAN` (apenas quando não existe um `synth_plan` com o mesmo digest). Na trilha lógica, toda vez que `Φ_PROVE` produz um `logic_proof`, o núcleo agenda `Φ_SYNTH_PROOF`, gerando um `synth_proof` com o mesmo fingerprint e anexando relações `logic/SYNTH`. Assim, a cadeia plano/prova → síntese fica registrada por digest (`source_digest`/`proof_digest`) e passa a aparecer direto no `meta_summary`, garantindo rastreabilidade integral do processo de síntese.

Para fechar o elo de auditoria, o `meta_summary` agora inclui um bloco `meta_synthesis` agregando todos os `synth_plan`, `synth_proof` e `synth_prog` presentes no contexto. Esse nó expõe contagens por categoria, listas resumidas (com digest de origem, contagem de passos, idioma e status) e é convertido em campos estruturados por `meta_summary_to_dict`, permitindo acompanhar, em JSON, o ciclo completo “estrutura detectada → síntese Φ → digest rastreável”.

Além disso, `Φ_SYNTH_PROG` passou a ser disparado automaticamente: sempre que `REWRITE_CODE` cria um `code_ast_summary`, o runtime identifica resumos ainda não sintetizados (via digest) e agenda `SYNTH_PROG` antes do halt. O operador grava o `source_digest` no próprio nó e nas relações `code/SYNTH`, garantindo que o bloco `meta_synthesis` consiga rastrear com o mesmo nível de detalhe usado para planos e provas.

Por fim, `meta_memory` incorpora esses mesmos campos: cada `memory_entry` guarda os totais de síntese detectados na execução atual e uma lista determinística dos digests (`source_digest`/`proof_digest`) utilizados. Isso significa que chamadas subsequentes a `MEMORY_RECALL` podem reativar não apenas rota/preview/razões, mas também quais planos, provas e programas foram concretizados naquele ponto da linha do tempo.

Para consumir esse bloco fora do runtime, `meta_memory_to_dict(meta_memory_node)` retorna um dicionário pronto (`size`, `digest`, `entries[...]`) em que cada entrada replica exatamente os campos persistidos (inclusive os `synthesis_*`). Isso simplifica integrações externas e ferramentas de auditoria que precisam analisar o histórico determinístico sem reimplementar parsing LIU.

O histórico curto também é materializado: `meta_memory` agrega os últimos meta-resultados (rota, digestos de raciocínio/expressão e prévias) e é anexado no `meta_summary`, garantindo que cada execução carregue um mapa determinístico das iterações anteriores — base para memória auditável e evolução multi-turno.

Esse mesmo pacote é persistido automaticamente em `.nsr_memory/memory.jsonl` (JSONL com hashes BLAKE2b), permitindo recarregar sessões seguintes e iniciar cada Meta-LER com operações `MEMORY_RECALL` que inserem, no contexto LIU, as entradas anteriores antes do novo raciocínio Φ.

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
