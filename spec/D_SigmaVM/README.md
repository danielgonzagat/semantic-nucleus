# Especificação D — ΣVM / Ω-VM

## Objetivo

- Executar micro-ops de LIU/NSR com bytecode determinístico (SVMB), assembler e VM auditável.
- OpCodes atuais (subconjunto mínimo): `PUSH_TEXT`, `BUILD_STRUCT`, `STORE_ANSWER`, `HALT`.

## Formato SVMB

```
| MAGIC "SVMB" | varint major | varint minor | varint body_len | body(opcodes) |
body := [ opcode (1 byte) | varint operand ]*
```

- Implementação em `svm.bytecode` (funções `encode`/`decode`).
- Varints little-endian (LEB128) definidos em `svm.encoding`.

## Assembler/Disassembler

- `svm.assembler.assemble(text)` converte DSL textual (uma instrução por linha, comentários `;`).
- `disassemble` realiza o caminho inverso para auditoria humana.

## Máquina Virtual de Referência

- `svm.vm.SigmaVM` usa pilha de nós LIU e `Program(constants, instructions)`.
- Execução é puramente determinística:
  - `PUSH_TEXT idx` → empilha `TEXT(constants[idx])`.
  - `BUILD_STRUCT n` → consome `2*n` itens (key TEXT, valor Node) e empilha `STRUCT` canônico.
  - `STORE_ANSWER` → define `answer` (obrigatório antes do `HALT`).
  - `HALT` → encerra, retornando o `STRUCT` final.
- Snapshots conceituais podem serializar `Program` (instruções + constantes) e `answer`.

## Testes

- `tests/svm/test_vm.py` garante que (1) VM monta resposta válida e (2) encode/decode preserva opcodes.

## Extensões planejadas

- Adicionar pilha de registradores `R0..R7`, instruções de unificação e acesso direto a ISR.
- Introduzir seções adicionais (.ATOM, .KB_FACTS, .RULES) conforme manifesto.
- Implementar `ΣVM` ↔ `NSR` bridge para executar micro-ops Φ (NORMALIZE, ANSWER, etc.).
