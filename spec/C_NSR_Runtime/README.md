# Especificação C — NSR / ISR Runtime

## Componentes

1. **LxU (`nsr.lex`)** – tokeniza texto em `Token(lemma, tag)` com dic. determinístico, remoção de stopwords e mapeamento semântico.
2. **PSE (`nsr.parser`)** – converte tokens em `STRUCT(subject/action/object/modifier)` canônico.
3. **ISR (`nsr.state`)** – `ISR = {ontology, relations, context, goals, ops_queue, answer, quality}` imutável.
4. **Operadores Φ (`nsr.operators`)** – NORMALIZE, ANSWER, INFER, COMPARE, EXTRACT, EXPAND, SUMMARIZE, EXPLAIN.
5. **MCE / Loop (`nsr.runtime`)** – aplica `Φ` em FIFO, garante parada por `max_steps` ou `quality >= τ`.

## Contratos

- Nenhum operador executa IO; todos recebem `(isr, op, session)` e retornam novo `ISR`.
- `apply_operator` preserva determinismo; novas relações são normalizadas antes de entrar no estado.
- Inferência usa regras `Rule(if_all, then)` + unificação (`nsr.rules`).
- `SessionCtx` contém `Config`, ontologia base e lexicon; alterar config não altera semântica.

## Métrica de qualidade

- `OP_ANSWER` adiciona +0.2 (limitado a 1.0).
- `SUMMARIZE` garante mínimo 0.5.
- Critério de parada principal: `answer.fields` preenchido **e** `quality ≥ min_quality`.

## Determinismo e Auditoria

- Fila `ops_queue` é sempre FIFO (deque).
- `Trace` registra `"<step>: <OP> quality=<val>"` para auditoria.
- Falhas de progresso são absorvidas pelo limite `max_steps` (32 por padrão).

## Testes

- `tests/nsr/test_runtime.py` cobre: (1) parsing+answer textual, (2) inferência `PART_OF → HAS`.
- Conformidade adicional: expandir `kb_rules` e lexicons mantêm determinismo; use `pytest -k nsr`.
