import pytest

from liu import (
    entity,
    relation,
    struct,
    list_node,
    text,
    to_sexpr,
    parse_sexpr,
    to_json,
    from_json,
    normalize,
    check,
    LIUError,
)


def sample_struct():
    return struct(
        subject=entity("carro"),
        action=entity("andar"),
        modifier=list_node([entity("rapido")]),
    )


def test_serialization_roundtrip():
    node = sample_struct()
    sexpr = to_sexpr(node)
    parsed = parse_sexpr(sexpr)
    assert parsed == normalize(node)
    as_json = to_json(node)
    back = from_json(as_json)
    assert back == normalize(node)


def test_wf_detects_unknown_relation():
    bad = relation("UNKNOWN", entity("x"))
    with pytest.raises(LIUError):
        check(bad)


def test_wf_struct_fields_sorted():
    struct_a = struct(action=entity("andar"), subject=entity("carro"))
    struct_b = struct(subject=entity("carro"), action=entity("andar"))
    assert normalize(struct_a) == normalize(struct_b)
