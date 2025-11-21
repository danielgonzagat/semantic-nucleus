# Especificação LIU — Linguagem Interna Universal (OMNIMETAL v0.1)

## 1. Objetivo

A LIU é o IR semântico único utilizado pelo Núcleo Originário. Ela representa significado computável (entidades, relações, operações, estruturas) com propriedades:

- **Determinismo** – mesma entrada ⇒ mesma estrutura ⇒ mesmo hash.
- **Fechamento** – qualquer operador Φ produz outro nó LIU bem formado.
- **Imutabilidade** – nós são internados/canônicos; comparação é estrutural.
- **Auditabilidade** – serialização S-expression/JSON e fingerprint Blake2b.
- **Tipagem estática** – assinaturas (`Σ_rel`, `Σ_op`) e sort lattice garantem contratos.

## 2. Gramática (EBNF)

```
<expr>      ::= <rel> | <op> | <entity> | <struct> | <list> | <literal> | "NIL"
<rel>       ::= "(" "REL" ":" <atom> { <expr> } ")"
<op>        ::= "(" "OP"  ":" <atom> { <expr> } ")"
<entity>    ::= "(" "ENTITY" ":" <atom> ")"
<struct>    ::= "(" "STRUCT" { "(" <atom> <expr> ")" } ")"
<list>      ::= "[" { <expr> } "]"
<literal>   ::= "(" "TEXT"   ":" <json-string> ")"
              | "(" "NUMBER" ":" <number> ")"
              | "(" "BOOL"   ":" ("true"|"false") ")"
              | "(" "VAR"    ":" <atom> ")"             ; variáveis estilo ?X
<atom>      ::= [A-Za-z0-9_./:-]+ (internado)
```

## 3. Kinds e Sorts

| Kind            | Sort padrão    | Descrição                                      |
|-----------------|----------------|-----------------------------------------------|
| `ENTITY`        | `Thing`        | Símbolos atômicos canônicos (`code/fn::...`). |
| `REL`           | `Prop`         | Relações verificadas contra `Σ_rel`.          |
| `OP`            | `Operator`     | Operadores Φ verificados em `Σ_op`.           |
| `STRUCT`        | `State`        | Registros imutáveis (campos ordenados).       |
| `LIST`          | `List`         | Sequências imutáveis.                         |
| `TEXT`          | `Text`         | Literais Unicode (JSON‑escaped).              |
| `NUMBER`        | `Number`       | Literais float.                               |
| `BOOL`          | `Bool`         | Literais booleanos.                           |
| `VAR`           | `Any`          | Variáveis para unificação (`?X`).             |
| `NIL`           | `Any`          | Ausência/tomada neutra.                       |

Sort lattice estendido inclui `Thing`, `Type`, `Action`, `Event`, `Structure`, `Code`, `Context`, `Goal`, `Answer`, `Any`.

## 4. Assinaturas principais

### Relações (`Σ_rel`)

- Ontologia: `IS_A(Thing, Type)`, `PART_OF(Thing, Thing)`, `HAS_PART`, `HAS`, `CAUSE(Event, Event)`, `BEFORE(Event, Event)`, `EQUAL`, `DIFFERENT`, `DESCRIBES(Context, Thing)`.
- Código (`code@1`): `code/DEFN(Code, Structure)`, `code/PARAM(Code, Structure)`, `code/RETURNS(Code, Type)`, `code/CALL(Code, Code, Structure)`, `code/ASSIGN(Structure, Structure)`, `code/IF(Structure, Structure, Structure)`, `code/LOOP(...)`, `code/BORROW(Code, Text, Text)`, `code/MOVE(Code)`, `code/TYPE(Code, Type)`, `code/ANNOTATION(Code, Context)`.

### Operadores (`Σ_op`)

```
NORMALIZE  : State -> State
EXTRACT    : (Structure, Text) -> Any
COMPARE    : (Any, Any) -> Prop
INFER      : State -> State
MAP        : (List, Operator) -> List
REDUCE     : (List, Operator) -> Any
REWRITE    : Any -> Any
EXPAND     : Any -> State
ANSWER     : Any -> Answer
EXPLAIN    : (State, Any) -> Answer
SUMMARIZE  : State -> Answer
ALIGN      : State -> State
STABILIZE  : State -> State
code/EVAL_PURE : Any -> Any
```

## 5. STRUCT fields

Fields são ordenados lexicograficamente e possuem sorts esperados; exemplos:

| Campo     | Sort      |
|-----------|-----------|
| `subject` | Thing     |
| `action`  | Any       |
| `object`  | Thing     |
| `context` | Context   |
| `modifier`| List      |
| `params`  | List      |
| `body`    | List      |
| `ret`     | Type      |
| `guard`   | Any       |
| `pattern` | Any       |
| `answer`  | Text      |
| `assign`  | Structure |

Campos desconhecidos assumem `Any`, mas duplicatas ou ordem incorreta invalidam o nó.

## 6. Normalização e hashing

- `liu.normalizer.normalize` produz forma canônica (ordenando campos, deduplicando relações).
- `liu.hash.fingerprint` gera Blake2b‑128 do nó. Use após `normalize` para auditoria/hashes de estado.

## 7. Serialização

- **S-expression**: `to_sexpr` segue a gramática acima (`(REL:IS_A (ENTITY:carro) (ENTITY:veiculo))`).
- **JSON**: `to_json` emite objetos determinísticos (`{"kind":"REL","label":"IS_A","args":[...]}`).
- `parse_sexpr`/`from_json` garantem round-trip quando acompanhados de `normalize`.

## 8. Validação (WF)

`liu.wf.check(node)`:

1. Verifica registro em `Σ_rel` / `Σ_op`.
2. Confere aridade e sorts de argumentos.
3. Assegura STRUCT com campos únicos, ordenados e com sorts compatíveis.
4. Propaga checagem recursiva em LIST/STRUCT.

Erros levantam `LIUError`.

## 9. Testes de conformidade (Cycle 1)

Cobertura mínima (ver `tests/liu/`):

- Round-trip de serialização com TEXT/NUMBER.
- Detecção de relações desconhecidas / violações de sort.
- Deduplificação de relações.
- Hash determinístico (`fingerprint`).

## 10. Procedimento de uso

1. Construir nós via `liu.nodes` (ou via compiladores/frontends).
2. Normalizar com `normalize`.
3. Validar com `check`.
4. Serializar (`to_sexpr`/`to_json`) ou calcular fingerprint conforme necessário.

Esses passos são obrigatórios antes de injetar estruturas no NSR/ΣVM para garantir determinismo e segurança.
