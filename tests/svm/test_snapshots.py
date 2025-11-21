import json

import pytest

from svm import (
    SigmaVM,
    build_program_from_assembly,
    build_snapshot,
    save_snapshot,
    load_snapshot,
    restore_snapshot,
    sign_snapshot,
    verify_snapshot_signature,
    generate_ed25519_keypair,
    Ed25519Unavailable,
)


def _program():
    asm = """
    PUSH_CONST 1
    PUSH_TEXT 0
    NEW_STRUCT 1
    STORE_ANSWER
    HALT
    """
    return build_program_from_assembly(asm, ["answer", "Snapshot ok."])


def test_snapshot_is_deterministic_between_runs(tmp_path):
    program = _program()
    vm_a = SigmaVM()
    vm_a.load(program)
    vm_a.run()

    vm_b = SigmaVM()
    vm_b.load(program)
    vm_b.run()

    snap_a = build_snapshot(vm_a)
    snap_b = build_snapshot(vm_b)
    assert snap_a.digest == snap_b.digest
    path = tmp_path / "state.svms"
    saved = save_snapshot(vm_a, path)
    assert path.exists()
    loaded = load_snapshot(path)
    assert loaded.digest == saved.digest
    assert loaded.isr["quality"] >= 0.0
    assert loaded.bytecode_b64 == saved.bytecode_b64
    # JSON dump should be parseable back to the original dict for tooling integration
    json.loads(path.read_text())


def test_snapshot_restore_state_roundtrip():
    program = _program()
    vm = SigmaVM()
    vm.load(program)
    vm.run()
    snapshot = build_snapshot(vm)
    restored = restore_snapshot(snapshot)
    assert restored.pc == vm.pc
    assert restored.answer == vm.answer
    assert restored.isr.relations == vm.isr.relations
    assert restored.stack == vm.stack


def test_snapshot_signature_ed25519():
    program = _program()
    vm = SigmaVM()
    vm.load(program)
    vm.run()
    snapshot = build_snapshot(vm)
    try:
        public_key, private_key = generate_ed25519_keypair()
    except Ed25519Unavailable:
        pytest.skip("ed25519 unavailable in this environment")
    signature = sign_snapshot(snapshot, private_key)
    assert signature.public_key == public_key
    signed_snapshot = snapshot.with_signature(signature)
    assert verify_snapshot_signature(snapshot, signature) is True
    assert signed_snapshot.signatures
