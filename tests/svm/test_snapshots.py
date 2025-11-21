import json

from svm import SigmaVM, build_program_from_assembly
from svm.snapshots import build_snapshot, save_snapshot, load_snapshot


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
    raw = load_snapshot(path)
    assert raw["digest"] == saved.digest
    assert raw["state"]["isr"]["quality"] >= 0.0
    assert raw["program"]["bytecode"] == saved.bytecode_b64
    # JSON dump should be parseable back to the original dict for tooling integration
    json.loads(path.read_text())
