# Núcleo Originário — LIU / NSR / ΣVM

Núcleo Originário é a implementação de referência de uma arquitetura simbólica CPU-first composta pela **Linguagem Interna Universal (LIU)**, pelo **Núcleo Semântico Reativo (NSR)** e pela **Máquina Virtual Semântica (ΣVM / Ω-VM)**. Tudo é determinístico, auditável e livre de dependências de GPU ou modelos estatísticos.

## Camadas principais

1. **LIU** – IR semântico tipado com S-expressions/json equivalentes, arena imutável de nós e verificações de bem-formação.
2. **NSR/ISR** – Motor reativo com LxU, PSE, operadores Φ (NORMALIZE/EXTRACT/COMPARE/INFER/etc.), mecanismo de convergência e renderização textual.
3. **ΣVM / Ω-VM** – Bytecode SVMB com opcodes para construir nós LIU, manipular o estado ISR e despachar operadores Φ de forma determinística/auditável.
4. **Compiladores multilíngue** – Frontends para Python, Elixir, Rust e lógica Prolog-like que abaixam construtos para LIU.
5. **Manifesto e governança** – Diretrizes públicas de ética, segurança, versionamento e roadmap.

## Estrutura do repositório

```
/spec                # Especificações normativas (LIU, Compilers, Runtime, ΣVM, Manifesto)
/src                 # Implementações em Python 3.11+
  ├── liu            # Tipos, serialização, normalização e ontologia base
  ├── ontology       # Pacotes core/code para o NSR
  ├── nsr            # Estado ISR, operadores Φ, LxU/PSE e orquestrador
  ├── svm            # Bytecode, assembler, opcodes e VM de referência
  ├── frontend_*     # Frontends determinísticos (python/elixir/rust/logic)
/tests               # Suites de conformidade (WF, runtime, VM, compilers)
/docs                # Manifesto, roadmap e documentação pública
```

## Requisitos & instalação

- Python 3.11+ (CPU comum).
- Dependências de runtime: apenas biblioteca padrão.
- Testes: `pytest>=9` (instale via `python3 -m pip install pytest`).

## Como executar

```bash
# Executar testes de conformidade
python3 -m pytest
# Suite rápida (CTS)
python3 -m pytest tests/cts

# Rodar o NSR em modo textual
PYTHONPATH=src python3 - <<'PY'
from nsr import run_text, run_text_full
answer, trace = run_text("O carro anda rapido")
print(answer)
print(trace.steps)

# Obter a equação LIU (entrada → grafo → resposta)
outcome = run_text_full("O carro anda rapido")
print(outcome.equation.to_sexpr_bundle())
PY

# CLI determinístico (texto → equação → texto)
PYTHONPATH=src python3 -m nsr.cli "O carro anda rapido" --format both --enable-contradictions

# Montar e rodar um programa ΣVM
PYTHONPATH=src python3 - <<'PY'
from svm import build_program_from_assembly, SigmaVM
asm = """
PUSH_CONST 1
PUSH_TEXT 0
NEW_STRUCT 1
STORE_ANSWER
HALT
"""
program = build_program_from_assembly(asm, ["answer", "O carro anda rápido."])
vm = SigmaVM()
vm.load(program)
print(vm.run())
PY
```

## Determinismo e segurança

- Sem IO dentro de LIU/NSR/ΣVM; qualquer capacidade externa deve ser encapsulada e auditada antes de ativar.
- Estruturas imutáveis e arenas canônicas garantem hashes de estado reprodutíveis.
- Operadores Φ são puros, tipados e fechados sob transformação.
- Testes cobrem bem-formação, normalização, inferência, compiladores, ΣVM e CTS.

## Licença

Código e especificações sob MIT/CC-BY-SA (ver Manifesto em `/docs/manifesto.md`).
