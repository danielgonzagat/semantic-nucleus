# ΣVM Core Spec (Cycle 3 – ISA v0.2)

## 1. Arquitetura

- Máquina de pilha determinística com 8 registradores voláteis `R0..R7`.
- Programa = `Program(constants: List[str], instructions: List[Instruction])`.
- Estado: `{stack, registers, pc, answer}`; `load()` reseta tudo.
- Entradas e saídas exclusivamente via pilha/registradores; sem IO.

## 2. Formato de bytecode

```
MAGIC  : "SVMB"
MAJOR  : varint
MINOR  : varint
LEN    : varint (bytes do corpo)
BODY   : [ opcode:u8 | operand:varint ]
```

- `encode`/`decode` em `svm.bytecode`.
- Varints = LEB128 little-endian (`svm.encoding`).
- Versão atual `(1,0)`; VMs futuras devem rejeitar major incompatível.

## 3. ISA (mnemonics)

| Opcode        | Operand | Descrição                                                                 |
|---------------|---------|----------------------------------------------------------------------------|
| `PUSH_TEXT k` | idx     | Empilha `TEXT(constants[idx])`.                                           |
| `PUSH_CONST`  | idx     | Alias para `PUSH_TEXT` (compat).                                          |
| `PUSH_KEY`    | idx     | Empilha chave TEXT; usada antes de `BEGIN_STRUCT`.                        |
| `BUILD_STRUCT n` / `BEGIN_STRUCT n` | n | Consome `2n` itens (chave, valor) → `STRUCT`. Keys devem ser TEXT. |
| `LOAD_REG r`  | idx     | Empilha conteúdo de `Rr`. Falha se `Rr` vazio.                            |
| `STORE_REG r` | idx     | Pop → `Rr`.                                                               |
| `NOOP`        | –       | Nenhum efeito (alinhamento/padding).                                      |
| `STORE_ANSWER`| –       | Pop → `answer`.                                                           |
| `HALT`        | –       | Encerra execução retornando `answer`.                                     |

Regras:

- Pilha verifica underflow (lança `RuntimeError`).
- Registradores aceitam qualquer `Node`.
- `HALT` sem `answer` ⇒ `RuntimeError`.

## 4. Assembler DSL

- Uma instrução por linha (`MNEMONIC [operand]`), comentários iniciados por `;`.
- Valida operandos obrigatórios e faixa `0 ≤ r ≤ 7`.
- Usa `Opcode[...]`, portanto novos mnemonics exigem atualização do enum.

Exemplo:

```
PUSH_KEY 0    ; "answer"
PUSH_CONST 1  ; texto
BEGIN_STRUCT 1
STORE_ANSWER
HALT
```

`constants = ["answer", "O carro anda rápido."]`

## 5. Máquina virtual (`svm.vm.SigmaVM`)

- Métodos:
  - `load(program)` – reseta pilha, registradores e PC.
  - `run()` – interpreta bytecode, retornando `answer` (`Node`).
  - Helpers `_pop()`, `_push()`, `_pop_text()` garantem validações.
- Erros lançados:
  - `RuntimeError("program not loaded")`
  - `RuntimeError("stack underflow")`
  - `RuntimeError("register Rn is empty")`
  - `RuntimeError("STRUCT keys must be TEXT nodes")`
  - `RuntimeError("program halted without answer")`
  - `ValueError("Unsupported opcode ...")`

## 6. Testes de conformidade

`python3 -m pytest tests/svm`

1. `test_vm_runs_and_produces_answer` – fluxo básico com `PUSH_KEY/BEGIN_STRUCT`.
2. `test_register_instructions_roundtrip` – garante `STORE_REG` + `LOAD_REG`.
3. `test_encoding_roundtrip` – encode/decode preserva sequências de opcodes (`NOOP` incluso).

## 7. Roadmap imediato

- Estender `constants` para suportar blobs estruturados (JSON/LIU nodes).
- Adicionar verificador offline (checa operandos negativos, `HALT` obrigatório).
- Introduzir snapshots `.svms` com hash do estado (capacidade futura).
