# NSR Reactor Spec (Cycle 2 – OMNIMETAL/APOLION)

## 1. Pipeline

```
texto → LxU (tokens) → PSE (STRUCT) → ISR₀
ISR_{n+1} = Φ(ISR_n, OP_n)
parar quando answer ≠ NIL ∧ quality ≥ τ ou assinatura do estado repete
renderização → texto final + trace hash
```

## 2. Estado ISR

`ISR = { ontology, relations, context, goals, ops_queue, answer, quality }`

- `ontology` / `relations` / `context`: tuplas imutáveis de nós LIU.
- `goals` / `ops_queue`: `deque` copiados a cada operador (`snapshot()`), evitando aliasing.
- `answer`: `STRUCT(answer=TEXT)`; vazio significa “não convergiu”.
- `quality ∈ [0,1]`, evolui determinística: NORMALIZE ≥0.3, ANSWER +0.2, STABILIZE aproxima `min_quality`.

## 3. Operadores Φ suportados

| Operador   | Assinatura (Sorts)                           | Efeito determinístico                                        |
|------------|----------------------------------------------|----------------------------------------------------------------|
| NORMALIZE  | `State → State`                              | Normaliza/ordena relações e incrementa qualidade mínima.      |
| ANSWER     | `Any → Answer`                               | Renderiza STRUCT em texto; +0.2 de qualidade.                 |
| EXPLAIN    | `(State, Any) → Answer`                      | Explica nº de relações/contexto e foco.                       |
| SUMMARIZE  | `State → Answer`                             | Produz resumo textual com top-3 rótulos.                      |
| INFER      | `State → State`                              | Aplica regras `Rule(if_all, then)` com deduplicação.          |
| COMPARE    | `(Any, Any) → Prop`                          | Cria `EQUAL`/`DIFFERENT`, adicionando a `relations/context`.  |
| EXTRACT    | `(Structure, Text) → Any`                    | Extrai campo e adiciona ao contexto.                          |
| MAP        | `(List, Operator?) → List`                   | Mapeia lista (gera OP wrappers se template fornecido).        |
| REDUCE     | `(List, Operator?) → Any`                    | Soma números ou retorna `STRUCT(count=n)`, anexando ao contexto. |
| REWRITE    | `Any → Any`                                  | Normaliza nó arbitrário e anexa ao contexto.                  |
| EXPAND     | `Any → State`                                | Adiciona `IS_A(entity, coisa)` para entidades vistas.         |
| ALIGN      | `State → State`                              | Ordena/deduplica `relations` e `context`.                     |
| STABILIZE  | `State → State`                              | Ajusta qualidade rumo a `min_quality` sem exceder 0.95.       |

Todos são puros, sem IO, e sempre retornam novo `ISR`.

## 4. LxU / PSE

- `nsr.lex` usa `DEFAULT_LEXICON` com sinônimos (“automóvel”→“carro”), heurística para advérbios (-mente) e mapeia palavras-rel (`tem`, `possui`, `parte`).
- `nsr.parser.build_struct` produz `STRUCT` com campos `subject/action/object/modifier` e lista `relations` (REL entre entidades extraídas do texto).
- `nsr.state.initial_isr` injeta essas relações diretamente em `ISR.relations`, garantindo que o grafo semântico inicial reflita imediatamente os vínculos textuais antes do loop Φ.
- Pacotes multilíngues: `nsr.lex.compose_lexicon(("pt","en","es","fr"))` combina léxicos embutidos e `nsr.lex.load_lexicon_file` aceita JSON auditável para estender sinônimos/qualificadores/palavras-rel em tempo de execução.

## 5. Loop de execução

- Enquanto `ops_queue` não estiver vazia: `op = pop_left`, `isr = apply_operator(isr, op, session)`.
- Se `ops_queue` esvazia sem resposta, injeta `[ALIGN, STABILIZE, SUMMARIZE]` ou próximo goal.
- `_state_signature` (Blake2b-96) acompanha repetição; duas assinaturas iguais encerram como “estável”.
- `Trace.add` registra `"<n>:<OP> q=<val> rel=<count> ctx=<count>"` e atualiza `digest` (Blake2b-128 cumulativo).

## 6. Garantias

- **Determinismo**: operadores puros + filas copiados + assinaturas garantem mesmo traço/hash para mesma entrada.
- **Fechamento**: todas as transformações retornam nós validados pela LIU (`normalize` + WF).
- **Auditoria**: `Trace.steps` + `Trace.digest` + assinatura final do estado permitem reconstruir execução.
- **Parada**: `quality` ≥ `min_quality`, resposta pronta ou estado repetido → interrompe antes de `max_steps` (padrão 32).

## 7. Testes mínimos

1. `tests/nsr/test_runtime.py::test_run_text_simple` — pipeline texto → resposta + digest.
2. `tests/nsr/test_runtime.py::test_infer_rule_adds_relation` — valida regra `PART_OF → HAS`.
3. `tests/nsr/test_runtime.py::test_map_and_reduce_enrich_context` — garante que MAP/REDUCE acrescentam nós ao contexto.

Execute com `python3 -m pytest tests/nsr`.
