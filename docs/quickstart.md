# Quickstart — Núcleo Originário

## 1. Instalação

```bash
git clone https://github.com/nucleo-originario/nucleo.git
cd nucleo
python3 -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
pre-commit install
```

`blake3` é opcional, mas garante digests BLAKE3-256 para snapshots ΣVM.

## 2. Testes

```bash
python -m pytest
# ou com cobertura
coverage run -m pytest && coverage report
```

## 3. Pipeline texto → equação → texto

```bash
PYTHONPATH=src python -m nsr.cli "O carro anda rápido" --format both
```

Saída inclui `trace_digest`, `equation_hash` (Blake2b-128) e bundles JSON/S-expr.

## 4. ΣVM snapshots

```bash
PYTHONPATH=src python - <<'PY'
from svm import SigmaVM, build_program_from_assembly
from svm.snapshots import save_snapshot

asm = """
PUSH_CONST 1
PUSH_TEXT 0
NEW_STRUCT 1
STORE_ANSWER
HALT
"""
program = build_program_from_assembly(asm, ["answer", "Hello from snapshot."])
vm = SigmaVM()
vm.load(program)
vm.run()
save_snapshot(vm, "hello.svms")
PY
```

## 5. CI/CD

- Workflow GitHub Actions: `.github/workflows/tests.yml`.
- Gatilhos em `push` e `pull_request`.
- Executa `pip install -e .[dev]`, `pre-commit run --all-files` e `pytest`.

## 6. Contribuição

Leia `CONTRIBUTING.md`, siga o template de PR e respeite o `CODE_OF_CONDUCT.md`.
