# Especificação B — Compiladores Multilíngue → LIU

## Pipeline comum

```
source → AST/HIR → UAST minimalista → lowering → LIU (REL/STRUCT/OP)
```

- Todos convertem símbolos em `ENTITY:"code/fn::<m>::<nome>"` / `code/type::*`.
- Relacionamentos padronizados (`code/DEFN`, `code/PARAM`, `code/RETURNS`) têm assinaturas em `liu.signatures`.
- Resultados são listas de nós LIU aptos a `liu.wf.check`.

## Frontend Python (`src/frontend_python/compiler.py`)

- Baseado em `ast` da stdlib.
- Abaixa `FunctionDef`, `Return`, `Assign`, `BinOp` em `STRUCT`s puros e `relation("code/DEFN", ...)`.
- Expressões puras podem ser encapsuladas em `struct(binop=...)` para `OP:code/EVAL_PURE` futuro.

## Frontend Elixir (`src/frontend_elixir/compiler.py`)

- Recebe AST macroexpandido (dicionários determinísticos).
- Cada função vira `code/DEFN` com `params` (LIST) e `body` textual.
- Pipeline de clauses/pipes pode ser enriquecido adicionando chaves extras (guards, pipes, etc.).

## Frontend Rust (`src/frontend_rust/compiler.py`)

- Consome HIR/MIR simplificado (`kind="fn"`, params com tipos, retorno).
- Emite `code/DEFN`, `code/PARAM` e `code/RETURNS` indicando assinatura tipada.
- Borrow/move futuros devem adicionar relações `code/BORROW`, `code/MOVE` seguindo o mesmo padrão.

## Frontend Lógico (`src/frontend_logic/compiler.py`)

- Analisa fatos/regas estilo Prolog.
- Retorna tupla `(facts, rules)` onde facts são `REL` LIU e rules instâncias de `LogicRule(premises, conclusion)` (base para `nsr.state.Rule`).

## Determinismo & testes

- `tests/compilers/test_frontends.py` valida presença de `code/DEFN`/`code/RETURNS` e parsing de lógica.
- Nenhum frontend executa código; tudo é estático e puro.
- Expansões adicionais devem manter as invariantes: ordem lexicográfica de campos, listas imutáveis e ausência de efeitos colaterais.
