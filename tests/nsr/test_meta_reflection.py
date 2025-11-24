from liu import NodeKind

from nsr.meta_reasoner import build_meta_reasoning
from nsr.meta_reflection import build_meta_reflection


def test_meta_reflection_builds_phase_tree():
    steps = [
        "1:TEXT[ROUTE] q=0.10 rel=0 ctx=1",
        "2:Φ_PLAN[STATE_QUERY:NORMALIZE→INFER→SUMMARIZE] q=0.10 rel=0 ctx=1",
        "3:Φ_NORMALIZE q=0.45 rel=2 ctx=2",
        "4:Φ_MEMORY[RECALL] q=0.55 rel=2 ctx=3",
        "5:HALT[OPS_QUEUE_EMPTY] q=0.55 rel=2 ctx=3",
    ]
    reasoning = build_meta_reasoning(steps)
    reflection = build_meta_reflection(reasoning)
    assert reflection is not None
    fields = dict(reflection.fields)
    assert fields["tag"].label == "meta_reflection"
    assert int(fields["phase_count"].value) == 5
    assert int(fields["decision_count"].value) == len(steps)
    assert "Meta-LER" in fields["phase_chain"].label
    phases_node = fields["phases"]
    assert phases_node.kind is NodeKind.LIST
    first_phase_fields = dict(phases_node.args[0].fields)
    assert first_phase_fields["name"].label == "meta_ler"
    decisions_node = first_phase_fields["decisions"]
    assert decisions_node.kind is NodeKind.LIST
    decision_fields = dict(decisions_node.args[0].fields)
    assert decision_fields["category"].label == "meta_ler"
    assert "justification" in decision_fields
    last_phase_fields = dict(phases_node.args[-1].fields)
    assert last_phase_fields["name"].label == "meta_halt"
    assert last_phase_fields.get("alert") is None


def test_meta_reflection_returns_none_without_operations():
    assert build_meta_reflection(None) is None
