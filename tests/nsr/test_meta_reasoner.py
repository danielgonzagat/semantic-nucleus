from nsr.meta_reasoner import build_meta_reasoning


def test_meta_reasoning_serializes_steps_and_stats():
    steps = [
        "1:NORMALIZE q=0.30 rel=2 ctx=1",
        "2:INFER q=0.35 rel=3 ctx=1",
        "3:HALT[OPS_QUEUE_EMPTY] q=0.35 rel=3 ctx=1",
    ]
    node = build_meta_reasoning(steps)
    assert node is not None
    fields = dict(node.fields)
    assert fields["tag"].label == "meta_reasoning"
    step_count = fields["step_count"]
    assert int(step_count.value) == 3
    digest = fields["digest"]
    assert len(digest.label) == 32
    operations = fields["operations"]
    assert operations.kind.name == "LIST"
    assert len(operations.args) == 3
    first_entry = dict(operations.args[0].fields)
    assert first_entry["label"].label == "NORMALIZE"
    assert abs(first_entry["quality"].value - 0.30) < 1e-6
    stats_node = fields["operator_stats"]
    assert stats_node.kind.name == "LIST"
    stats = {}
    for entry in stats_node.args:
        entry_fields = dict(entry.fields)
        label_node = entry_fields.get("label")
        count_node = entry_fields.get("count")
        if label_node and count_node:
            stats[label_node.label] = count_node.value
    assert stats["NORMALIZE"] == 1
    assert stats["INFER"] == 1
    assert stats["HALT"] == 1


def test_meta_reasoning_honors_step_limit():
    steps = [f"{i+1}:NORMALIZE q=0.{i} rel=1 ctx=1" for i in range(5)]
    node = build_meta_reasoning(steps, max_steps=2)
    assert node is not None
    operations = dict(node.fields)["operations"]
    assert len(operations.args) == 2
    stats_node = dict(node.fields)["operator_stats"]
    stats = [dict(entry.fields)["count"].value for entry in stats_node.args]
    assert stats == [2.0]
