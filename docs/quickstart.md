# Quickstart — Núcleo Originário

## 1. Instalação

```bash
git clone https://github.com/nucleo-originario/nucleo.git
cd nucleo
python3 -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
pre-commit install
```

`blake3` é opcional, mas garante digests BLAKE3-256 para snapshots ΣVM. `cryptography` habilita assinaturas Ed25519.

## 2. Testes

```bash
python -m pytest
# ou com cobertura
coverage run -m pytest && coverage report
```

## 3. Pipeline texto → equação → texto

```bash
PYTHONPATH=src python -m nsr.cli "O carro anda rápido" --format both --include-report --include-stats
```

Saída inclui `trace_digest`, `equation_hash` (Blake2b-128), lista determinística `invariant_failures`
(vazia quando todas as invariantes passam), bundles JSON/S-expr, relatório texto←equação e estatísticas
de contagens/digests para auditoria estrutural.

## 4. ΣVM snapshots

```bash
PYTHONPATH=src python - <<'PY'
from svm import (
    SigmaVM,
    build_program_from_assembly,
    save_snapshot,
    load_snapshot,
    restore_snapshot,
    generate_ed25519_keypair,
    sign_snapshot,
    verify_snapshot_signature,
    Ed25519Unavailable,
)

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
snapshot = save_snapshot(vm, "hello.svms")
print("digest:", snapshot.digest)

restored = restore_snapshot(load_snapshot("hello.svms"))
assert restored.answer == vm.answer

try:
    pub, priv = generate_ed25519_keypair()
    signature = sign_snapshot(snapshot, priv)
    assert verify_snapshot_signature(snapshot, signature)
    snapshot = snapshot.with_signature(signature)
    print("signature:", signature.signature[:16], "...")
except Ed25519Unavailable:
    print("ed25519 unavailable; skipping signature demo")
PY
```

## 5. CI/CD

- Workflow GitHub Actions: `.github/workflows/tests.yml`.
- Gatilhos em `push` e `pull_request`.
- Executa `pip install -e .[dev]`, `pre-commit run --all-files` e `pytest`.

## 6. Aprendizado simbólico contínuo

```bash
PYTHONPATH=src python - <<'PY'
from pathlib import Path
from nsr_evo.api import run_text_learning

episodes = Path(".nsr_learning/episodes.jsonl")
rules = Path(".nsr_learning/learned_rules.jsonl")

for prompt in ("O carro tem roda", "O carro anda rápido"):
    answer, outcome = run_text_learning(prompt, episodes_path=episodes, rules_path=rules)
    print(prompt, "->", answer, outcome.quality)
PY
```

Cada chamada loga um episódio (`episodes.jsonl`) e tenta induzir novas regras LIU→LIU; se aprovadas, vão para `learned_rules.jsonl` e passam a fazer parte do `SessionCtx(kb_rules=...)`.

## 7. Ciclos offline guiados por energia

```bash
PYTHONPATH=src python -m nsr_evo.cli_cycle \
  --episodes .nsr_learning/episodes.jsonl \
  --rules .nsr_learning/learned_rules.jsonl \
  --max-prompts 32 \
  --max-rules 8 \
  --min-quality 0.6 \
  --min-support 3
```

O ciclo reexecuta prompts recentes, mede energia simbólica (contradições, cobertura, qualidade) e só grava regras se a energia cair. Útil para evolução batch controlada.

## 8. Inspeção do genoma simbólico

```bash
PYTHONPATH=src python -m nsr_evo.cli_genome list --rules .nsr_learning/learned_rules.jsonl
# desativar regra 0
PYTHONPATH=src python -m nsr_evo.cli_genome toggle --rules .nsr_learning/learned_rules.jsonl --index 0 --disable
```

Você pode auditar versões, suportes e energia de cada regra e desativar manualmente o que não fizer sentido.

## 9. Contribuição

Leia `CONTRIBUTING.md`, siga o template de PR e respeite o `CODE_OF_CONDUCT.md`.
