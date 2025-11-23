from liu import struct, text

from nsr.meta_expressor import build_meta_expression
from nsr.meta_reasoner import build_meta_reasoning
from nsr.meta_transformer import MetaRoute


def test_meta_expressor_generates_preview_and_digests():
    answer = struct(answer=text("Resposta determinística do núcleo."))
    reasoning = build_meta_reasoning(["1:NORMALIZE q=0.30 rel=1 ctx=1"])
    node = build_meta_expression(
        answer,
        reasoning=reasoning,
        quality=0.82,
        halt_reason="QUALITY_THRESHOLD",
        route=MetaRoute.TEXT,
        language="pt",
    )
    assert node is not None
    fields = dict(node.fields)
    assert fields["tag"].label == "meta_expression"
    assert fields["preview"].label.startswith("Resposta determinística")
    assert abs(fields["quality"].value - 0.82) < 1e-6
    assert fields["halt"].label == "quality_threshold"
    assert fields["route"].label == "text"
    assert fields["language"].label == "pt"
    assert fields["answer_digest"].label
    assert "reasoning_digest" in fields


def test_meta_expressor_returns_none_without_answer():
    empty_answer = struct()
    node = build_meta_expression(
        empty_answer,
        reasoning=None,
        quality=0.5,
        halt_reason="OPS_QUEUE_EMPTY",
        route=MetaRoute.TEXT,
        language="pt",
    )
    assert node is None
