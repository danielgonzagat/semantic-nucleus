# Especificação D — ΣVM / Ω-VM

## Objetivo

- Executar micro-ops LIU e operar diretamente sobre o estado ISR/NSR usando bytecode determinístico (SVMB).
- Fornecer assembler/disassembler auditável, verificação estrita de operandos e mecanismos de auditoria (`HASH_STATE`, `TRACE` externo).

## Formato SVMB

```
| MAGIC "SVMB" | varint major | varint minor | varint body_len | body(opcodes) |
body := [ opcode (1 byte) | varint operand ]*
```

- Implementação em `svm.bytecode` (funções `encode`/`decode`).
- Varints little-endian (LEB128) definidos em `svm.encoding`.

## ISA v0.5 (determinística)

| Opcode/Grupo                              | Operando | Semântica principal                                                                 |
|-------------------------------------------|----------|--------------------------------------------------------------------------------------|
| `PUSH_TEXT`, `PUSH_KEY`, `PUSH_CONST`     | idx      | Empilham TEXT (ou qualquer nó constante no caso de `PUSH_CONST`).                    |
| `PUSH_NUMBER`, `PUSH_BOOL`                | idx      | Convertem constantes numéricas/booleanas em nós LIU.                                 |
| `LOAD_REG r`, `STORE_REG r`               | idx      | Registradores voláteis `R0..R7`.                                                     |
| `NEW_STRUCT n`, `NEW_LIST n`              | n        | Consomem pares chave/valor ou itens → criam `STRUCT`/`LIST`.                         |
| `NEW_REL n`, `NEW_OP n`                   | n        | Constróem relações/ops com `n` argumentos + label TEXT.                              |
| `GET_FIELD`, `SET_FIELD`                  | –        | Projeta/atualiza campos de STRUCT sem mutação (gera nova STRUCT).                    |
| `ADD_REL`, `HAS_REL`                      | –        | Manipulam `ISR.relations` (dedupe + checagem de presença).                           |
| `UNIFY_EQ`, `UNIFY_REL`                   | –        | Igualdade estrutural ou unificação padrão (`nsr.rules.unify`).                       |
| `ENQ_OP`, `DISPATCH`                      | –        | Manipulam `ISR.ops_queue`, com fallback `[ALIGN, STABILIZE, SUMMARIZE]`.             |
| `PHI_NORMALIZE/INFER/ANSWER/EXPLAIN/SUMMARIZE` | –   | Atalhos que instanciam `operation("Φ", args)` e aplicam `nsr.operators.apply_operator`. |
| `JMP`, `CALL`, `RET`                      | idx      | Controle de fluxo absoluto + call stack.                                            |
| `HASH_STATE`                              | –        | Empilha digest Blake2b-96 de `{relations, context, ops_queue, quality, answer}`.     |
| `STORE_ANSWER`, `NOOP`, `TRAP`, `HALT`    | opt      | Persistência, padding, abortos determinísticos (`TRAP [const|TEXT]`) e término.      |

Todos os opcodes verificam underflow, tipos esperados e limites (registradores e constantes). `TRAP` aceita literal direto ou valor textual da pilha.

## Assembler/Disassembler

- `svm.assembler.assemble(text)`:
  - normaliza mnemonics (`Φ_*` → `PHI_*`);
  - valida operandos, inclusive registradores (0–7) e contagens não negativas;
  - codifica `TRAP` sem operando como `-1` (diferenciando de índices legítimos).
- `disassemble` imprime operandos obrigatórios mesmo que zero.

## Máquina Virtual de Referência

- `svm.vm.SigmaVM` mantém `{stack, registers, call_stack, answer, session, isr}`.
- `load(program, initial_struct, session)` reseta o runtime e instancia `ISR` via `nsr.state.initial_isr`.
- `run()` interpreta SVMB, atualizando `self.isr` com cópias defensivas (deque).
- Hooks adicionais:
  - `_state_signature(isr)` (Blake2b-96) compartilhado com `HASH_STATE`.
  - `snapshot()` expõe `{pc, stack_depth, registers, isr_digest, answer}` para auditoria.
  - `TRAP` gera `RuntimeError` com mensagem configurável.

## Documentação complementar

- `spec/svm.md` traz ABI detalhada, exemplos de montagem e integração com o NSR.
- `docs/manifesto.md` define princípios de determinismo/auditoria que a VM segue.

## Testes

- `tests/svm/test_vm.py` cobre:
  1. Construção de STRUCTs + manipulação de relações (`ADD_REL`/`HAS_REL`/`SET_FIELD`).
  2. Pipeline Φ + `HASH_STATE` determinístico.
  3. Round-trip `encode/decode` incluindo instruções de controle/erros (`TRAP`).
- `tests/cts/test_conformance.py` garante interoperabilidade básica com o runtime.

## Próximos passos

- Exportar snapshots `.svms` (bytecode + estado ISR + digest).
- Verificador estático de bytecode (operandos, fluxo, `HALT` obrigatório).
- Seções nomeadas (.CONST/.OPS) e tooling para inspeção de traces.
