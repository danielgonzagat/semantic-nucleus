import pytest

from nsr.ian import (
    DEFAULT_INSTINCT,
    encode_word,
    decode_codes,
    word_signature,
    respond,
    plan_reply,
    conjugate,
)
from nsr.ian_bridge import maybe_route_text


def test_encode_decode_roundtrip():
    codes = encode_word("Você")
    assert decode_codes(codes) == "VOCÊ"
    assert word_signature("Você") == word_signature("VOCÊ")


@pytest.mark.parametrize(
    "incoming,expected",
    [
        ("oi", "oi"),
        ("OI", "oi"),
    ],
)
def test_greeting_response(incoming: str, expected: str):
    assert respond(incoming) == expected


def test_health_question_response_and_plan_codes():
    assert respond("oi, tudo bem?") == "tudo bem, e você?"
    plan = plan_reply("tudo bem?", DEFAULT_INSTINCT)
    assert plan.role == "ANSWER_HEALTH_AND_RETURN"
    assert plan.tokens[:3] == ("tudo", "bem", ",")
    assert plan.token_codes[0] == encode_word("tudo")


def test_maybe_route_text_builds_struct_and_answer():
    hook = maybe_route_text("tudo bem?")
    assert hook is not None
    fields = dict(hook.answer_node.fields)
    assert "answer" in fields
    assert fields["answer"].label == "tudo bem, e você?"
    assert hook.context_nodes
    tags = []
    for node in hook.context_nodes:
        node_fields = dict(node.fields)
        tag_node = node_fields.get("tag")
        if tag_node is not None and tag_node.label:
            tags.append(tag_node.label)
    assert "ian_reply" in tags


def test_verbose_health_question_response():
    assert respond("como você está?") == "estou bem, e você?"


def test_state_positive_and_negative_responses():
    assert respond("estou bem") == "que bom!"
    assert respond("não estou bem") == "sinto muito. posso ajudar?"


def test_conjugation_table():
    assert conjugate("estar", "pres", 1, "sing") == "estou"
    assert conjugate("falar", "pres", 2, "sing") == "fala"
