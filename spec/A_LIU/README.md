# Especificação A — LIU (Linguagem Interna Universal)

## Visão geral

- **Objetivo**: representar significado computável como grafos imutáveis e determinísticos.
- **Kinds**: `ENTITY`, `REL`, `OP`, `STRUCT`, `LIST`, `TEXT`, `NUMBER`, `BOOL`, `VAR`, `NIL`.
- **Sorts**: `Thing`, `Type`, `Prop`, `Operator`, `State`, `Context`, `Goal`, `Answer`, `Text`, `Number`, `Bool`, `List`, `Any`.
- **Gramática (EBNF reduzida)**
  ```
  <expr> ::= "NIL"
          | "(" "ENTITY:" <atom> ")"
          | "(" "REL:" <atom> <expr>* ")"
          | "(" "OP:" <atom> <expr>* ")"
          | "(" "STRUCT" (<field>)+ ")"
          | "[" <expr>* "]"
          | "(" "TEXT:" <string> ")" | ("NUMBER:" <float>) | ("BOOL:" (true|false))
  <field> ::= "(" <atom> <expr> ")"
  ```
- **Serializações**: S-expr canônica (ver `liu.serialize`) e JSON determinístico (`to_json`).

## Tipagem e bem-formação

- Assinaturas em `liu.signatures.REL_SIGNATURES` / `OP_SIGNATURES` definem aridade + sorts.
- `FIELD_SIGNATURES` restringem `STRUCT.subject/action/object/...`.
- `liu.wf.check(node)` garante preservação de sort e ausência de campos duplicados.
- Variáveis `VAR:?X` seguem α-equivalência; `infer_sort` cobre literais.

## Arena e imutabilidade

- `liu.arena.Arena` fornece interning estrutural; `liu.normalizer.normalize` devolve nós canônicos.
- `dedup_relations` ordena relações por `(label, args)` garantindo hash estável.

## Ontologia e pacotes

- `liu.ontology.BASE_ONTOLOGY` inicia com exemplos `IS_A(carros, veículo)`.
- Novos pacotes devem declarar `REL_SIGNATURES`/`OP_SIGNATURES` adicionais via namespace (`code/*`, `time/*`, etc.).

## Invariantes

1. **Determinismo** – mesmos nós ⇒ mesma serialização/hash.
2. **Fechamento** – toda operação sobre LIU retorna outro nó LIU válido.
3. **Sem IO** – construtores/serializadores não tocam disco/rede.
4. **Composicionalidade** – `STRUCT`/`LIST` são DAGs; sem ciclos.

## Auditoria

- `parse_sexpr` + `to_sexpr` garantem round-trip (testado em `tests/liu/test_liu_core.py`).
- JSON e S-expr usam apenas ASCII, com escape explícito.
