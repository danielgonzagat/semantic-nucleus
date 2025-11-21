# Especificação D — ΣVM / Ω-VM

## Objetivo

- Executar micro-ops de LIU/NSR com bytecode determinístico (SVMB), assembler e VM auditável.
- Subconjunto atual cobre construção de STRUCTs, registradores `R0..R7`, instruções de controle (`NOOP`, `HALT`) e persistência de respostas (`STORE_ANSWER`).

## Formato SVMB

```
| MAGIC "SVMB" | varint major | varint minor | varint body_len | body(opcodes) |
body := [ opcode (1 byte) | varint operand ]*
```

- Implementação em `svm.bytecode` (funções `encode`/`decode`).
- Varints little-endian (LEB128) definidos em `svm.encoding`.

## ISA v0.2 (parcial)

| Opcode        | Operando | Semântica                                                                 |
|---------------|----------|---------------------------------------------------------------------------|
| `PUSH_TEXT k` | idx      | Empilha `TEXT(constants[idx])`.                                           |
| `PUSH_CONST`  | idx      | Igual ao anterior (compatibilidade).                                      |
| `PUSH_KEY`    | idx      | Empilha chave TEXT para STRUCT.                                           |
| `BUILD_STRUCT`/`BEGIN_STRUCT n` | n | Consome `2*n` itens (key TEXT + valor) → empilha `STRUCT`.       |
| `LOAD_REG r`  | idx      | Empilha valor armazenado no registrador `Rr`.                             |
| `STORE_REG r` | idx      | Remove topo da pilha e grava em `Rr`.                                     |
| `NOOP`        | –        | Nenhum efeito (alinhamento).                                              |
| `STORE_ANSWER`| –        | Pop → `answer`.                                                           |
| `HALT`        | –        | Finaliza execução retornando `answer`.                                    |

Todos os opcodes checam underflow de pilha e índices válidos (registros 0–7).

## Assembler/Disassembler

- `svm.assembler.assemble(text)` suporta comentários `;`, valida operandos (inclusive faixa de registradores).
- `disassemble` gera listagem textual determinística.

## Máquina Virtual de Referência

- `svm.vm.SigmaVM` mantém pilha de nós LIU, registradores `R0..R7` e `Program(constants, instructions)`.
- Execução determinística com verificações:
  - Empilhar chaves/valores exige TEXT para chaves.
  - `LOAD_REG` falha se registrador vazio.
  - `_pop()` detecta underflow.
- `run()` retorna `answer` e dispara `RuntimeError` se programa terminar sem armazená-lo.

## Documentação

- `spec/svm.md` detalha ABI, tabela de opcodes e exemplos de montagem.

## Testes

- `tests/svm/test_vm.py` garante:
  1. Construção de STRUCT com `PUSH_KEY`/`BEGIN_STRUCT`.
  2. Persistência via registradores (`STORE_REG/LOAD_REG`).
  3. Round-trip de `encode`/`decode`.

## Próximos passos

- Estender constantes para tipos além de TEXT.
- Adicionar verificador estático para operandos negativos.
- Introduzir seções (.CONST, .KB) e snapshots `.svms` conforme manifesto.
