import pytest

from nsr.ian import (
    DEFAULT_INSTINCT,
    encode_word,
    decode_codes,
    word_signature,
    respond,
    plan_reply,
)


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
