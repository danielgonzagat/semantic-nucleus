# ΣVM Core Spec (Cycle 3 – ISA v0.5)

## 1. Arquitetura

- Máquina de pilha determinística com 8 registradores voláteis `R0..R7` e call stack explícita.
- Programa = `Program(constants: List[Any], instructions: List[Instruction])`.
- Estado interno: `{stack, registers, call_stack, pc, answer, session, isr}`.
  - `load()` reseta pilha/registradores, instancia `SessionCtx` e `ISR = initial_isr(initial_struct or struct(), session)`.
- Nenhuma instrução realiza IO. Toda mutação ocorre sobre nós LIU canônicos ou o `ISR` do NSR.

## 2. Formato de bytecode

```
MAGIC  : "SVMB"
MAJOR  : varint
MINOR  : varint
LEN    : varint (bytes do corpo)
BODY   : [ opcode:u8 | operand:varint ]
```

- `encode`/`decode` vivem em `svm.bytecode`.
- Varints usam LEB128 little-endian (`svm.encoding`).
- Versão atual `(1, 0)`; majors incompatíveis devem ser rejeitados.

## 3. ISA (resumo)

| Grupo                                    | Mnemonics principais                                                                              | Descrição                                                                                         |
|------------------------------------------|----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| Constantes                               | `PUSH_TEXT`, `PUSH_KEY`, `PUSH_CONST`, `PUSH_NUMBER`, `PUSH_BOOL`                                  | Empilham TEXT, chaves, nós arbitrários ou literais num/booleanos.                                  |
| Registradores                            | `LOAD_REG`, `STORE_REG`                                                                            | Acessam `R0..R7`; `LOAD` falha se o registrador estiver vazio.                                     |
| Construção de nós                        | `NEW_STRUCT`, `NEW_LIST`, `NEW_REL`, `NEW_OP`                                                      | Produzem STRUCT/LIST/REL/OP a partir dos itens da pilha (`NEW_REL/NEW_OP` usam label TEXT).        |
| Estruturas                               | `GET_FIELD`, `SET_FIELD`                                                                           | Consulta ou cria nova STRUCT com campo atualizado (pilha: struct, TEXT(key), valor).               |
| Estado ISR                               | `ADD_REL`, `HAS_REL`, `UNIFY_EQ`, `UNIFY_REL`                                                      | Dedup/consulta relações e executa unificação via `nsr.rules.unify`.                                |
| Orquestração Φ                           | `ENQ_OP`, `DISPATCH`, `PHI_NORMALIZE`, `PHI_INFER`, `PHI_ANSWER`, `PHI_EXPLAIN`, `PHI_SUMMARIZE`   | Manipulam `ops_queue` ou aplicam diretamente `nsr.operators.apply_operator`.                       |
| Fluxo                                    | `JMP`, `CALL`, `RET`, `NOOP`                                                                       | Saltos absolutos com call stack determinística.                                                    |
| Auditoria / saída                        | `HASH_STATE`, `STORE_ANSWER`, `TRAP`, `HALT`                                                       | Digest Blake2b-96 do ISR, persistência da resposta, abortos determinísticos e término do programa. |

Regras principais:

- `NEW_STRUCT n` consome `n` pares (TEXT(key), value). `NEW_LIST n` consome `n` valores.
- `NEW_REL/NEW_OP n` esperam label TEXT abaixo dos `n` argumentos.
- `DISPATCH` injeta `[ALIGN, STABILIZE, SUMMARIZE]` quando a fila fica vazia.
- `HASH_STATE` resume `{len(relations), len(context), len(ops_queue), quality, answer_text}` via Blake2b (96 bits).
- `TRAP` aceita índice de constante ou consome um TEXT no topo da pilha; sempre lança `RuntimeError`.

## 4. Assembler DSL

- Sintaxe: `MNEMONIC [operand]` por linha, comentários iniciados por `;`.
- Mnemonics com `Φ` podem ser escritos como `Φ_NORMALIZE` ou `PHI_NORMALIZE`.
- Validações:
  - registradores `0 ≤ r ≤ 7`;
  - contagens/targets não negativos;
  - `TRAP` sem operando recebe `-1` (diferenciando de índices legítimos).

Exemplo:

```
PUSH_CONST 1      ; texto
PUSH_TEXT 0       ; "answer"
NEW_STRUCT 1
STORE_ANSWER
HALT
```

`constants = ["answer", "O carro anda rápido."]`

## 5. Máquina virtual (`svm.vm.SigmaVM`)

- `load(program, initial_struct=None, session=None)` reseta pilha, registradores, call stack e cria `ISR = initial_isr(initial_struct or struct(), session)`.
- `run()` interpreta SVMB até `HALT`, mantendo `self.answer` sincronizada com `self.isr.answer`.
- Utilitários:
  - `_state_signature(isr)` (Blake2b-96) também exposto via `HASH_STATE`.
  - `snapshot()` retorna `{"pc", "stack_depth", "registers", "isr_digest", "answer"}`.
  - `TRAP` sempre gera `RuntimeError` com mensagem do operando ou do topo da pilha.
- Erros padrão: programa não carregado, underflow de pilha, registrador vazio, saltos fora da faixa, `RET` sem call stack, `HALT` sem resposta.

## 6. Testes de conformidade

`python3 -m pytest tests/svm`

1. `test_vm_struct_and_relation_ops` – constrói STRUCTs, adiciona relações ao ISR e usa `SET_FIELD`.
2. `test_vm_phi_pipeline_and_hash` – executa operadores Φ diretamente e valida `HASH_STATE`.
3. `test_encoding_roundtrip` – garante que `encode`/`decode` preservam instruções (incluindo `TRAP`/`HALT`).

## 7. Snapshots `.svms`

- `svm.snapshots` expõe `build_snapshot`, `save_snapshot`, `load_snapshot` e `SNAPSHOT_VERSION`.
- Snapshot = JSON determinístico com:
  - `version`: `"svms/1"`.
  - `program.bytecode`: SVMB codificado em base64 (`svm.bytecode.encode`).
  - `program.constants`: constantes serializadas (`Node` ⇒ objeto `{type:"node", value:<LIU-JSON>}`).
  - `state.isr`: ontologia/relações/contexto/goals/ops/answer/quality em JSON LIU.
  - `state.vm`: metadados (`pc`, `stack_depth`, `registers`, `isr_digest`, answer renderizado).
- `digest`: BLAKE3-256 quando disponível (fallback Blake2b-256) calculado sobre a carga ordenada.
- Extensão recomendada `.svms`; arquivos terminam com newline para compatibilidade com ferramentas Unix.

## 8. Roadmap imediato

- Assinaturas determinísticas das snapshots `.svms` (ed25519) e restauração incremental no VM.
- Verificador offline (fluxo, operandos, `HALT` obrigatório, cotas de fila/ops).
- Seções nomeadas (.CONST/.OPS/.KB) e tooling CLI para inspeção de traces/dumps.
