# Especificação C — NSR / ISR Runtime

## Componentes

1. **LxU (`nsr.lex`)** – tokeniza texto em `Token(lemma, tag)` com dicionário determinístico, sinônimos e heurísticas (`QUALIFIER` por sufixo *-mente*).
2. **PSE (`nsr.parser`)** – converte tokens em `STRUCT(subject/action/object/modifier)` canônico.
3. **ISR (`nsr.state`)** – `ISR = {ontology, relations, context, goals, ops_queue, answer, quality}` com snapshots imutáveis das filas.
4. **Operadores Φ (`nsr.operators`)** – NORMALIZE, ANSWER, INFER, COMPARE, EXTRACT, MAP, REDUCE, REWRITE, EXPAND, ALIGN, STABILIZE, SUMMARIZE, EXPLAIN.
5. **MCE / Loop (`nsr.runtime`)** – aplica `Φ` em FIFO, detecta assinaturas repetidas e encerra ao convergir (`quality ≥ τ` ou estado estável).

## Contratos

- Nenhum operador executa IO; todos recebem `(isr, op, session)` e retornam novo `ISR`.
- `apply_operator` cria cópias defensivas de `ops_queue` e `goals`, garantindo pureza e ausência de aliasing.
- Inferência usa regras `Rule(if_all, then)` + unificação (`nsr.rules`), deduplica e normaliza as relações derivadas.
- `SessionCtx` contém `Config`, ontologia base, regras e lexicon; alterar config não altera semântica.

## Métrica de qualidade

- `ANSWER` incrementa +0.2 (limitado a 1.0).
- `SUMMARIZE` garante qualidade mínima 0.5.
- `STABILIZE` aproxima a qualidade de `min_quality` sem ultrapassar 0.95.
- Critério principal: `answer.fields` preenchido **e** `quality ≥ min_quality`, ou a mesma assinatura de estado repetida em duas iterações.

## Determinismo e Auditoria

- `ops_queue` permanece FIFO; quando vazia, injeta `[ALIGN, STABILIZE, SUMMARIZE]`.
- `Trace` registra `"<n>:<OP> q=<val> rel=<count> ctx=<count>"` e mantém `digest` Blake2b-128 cumulativo.
- `_state_signature` (Blake2b-96) evita loops silenciosos antes do limite `max_steps` (32 por padrão).

## Testes

- `tests/nsr/test_runtime.py` cobre: pipeline texto→resposta (digest incluso), inferência `PART_OF → HAS` e MAP/REDUCE enriquecendo contexto.
- Para regressões, execute `python3 -m pytest tests/nsr -k runtime`.
