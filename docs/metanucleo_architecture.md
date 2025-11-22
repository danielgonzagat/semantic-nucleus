# Arquitetura Determinística do Metanúcleo

O Metanúcleo opera como uma cadeia irreversível reversível que leva qualquer entrada a uma forma de meta-representação e, a partir dela, produz meta-cálculo executável no hardware. Esta nota descreve as três visões oficiais do sistema — macro arquitetura, pipeline interno e topologia cognitiva — e documenta o estágio Meta-LER implementado pelo novo `MetaTransformer`.

## Meta-LER com `MetaTransformer`

O estágio Meta-LER recebe texto cru e determina, de maneira determinística, qual rota deve ser aplicada:

- **Matemática** (`MetaRoute.MATH`): ativa o `math_bridge`/`Math-Core` quando a entrada é equação ou instrução aritmética.
- **Lógica** (`MetaRoute.LOGIC`): roteia comandos `FACT/IF/QUERY` para o `logic_bridge`.
- **Instinto Linguístico** (`MetaRoute.INSTINCT`): aciona o IAN-Ω quando a frase corresponde a um instinto nativo (saudações, diagnósticos etc.).
- **Parser textual** (`MetaRoute.TEXT`): cai no LxU + PSE e produz um `STRUCT` LIU completo, anexando metadados de idioma.

Cada rota devolve um `MetaTransformResult` com a `struct_node`, contexto pré-semeado (sempre carrega `meta_route` + `meta_input` para auditoria), qualidade estimada e etiqueta de trace (`trace_label`). O `run_text_full` usa esse resultado para alimentar o ISR inicial e também publica `meta_summary = (meta_route, meta_input, meta_output)`, caracterizando formalmente o estágio **Meta-Resultado** (o CLI expõe o mesmo trio via `--include-meta`).

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
