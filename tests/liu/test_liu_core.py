import pytest

from liu import (
    entity,
    relation,
    struct,
    list_node,
    text,
    number,
    to_sexpr,
    parse_sexpr,
    to_json,
    from_json,
    normalize,
    dedup_relations,
    check,
    LIUError,
    fingerprint,
)


def sample_struct():
    return struct(
        subject=entity("carro"),
        action=entity("andar"),
        modifier=list_node([entity("rapido")]),
    )


def test_serialization_roundtrip_handles_text_and_numbers():
    node = struct(
        subject=entity("carro"),
        action=entity("andar"),
        metadata=list_node([text("rápido"), number(42)]),
    )
    serialized = to_sexpr(node)
    parsed = parse_sexpr(serialized)
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


def test_field_sort_validation():
    bad = struct(subject=number(7))
    with pytest.raises(LIUError):
        check(bad)


def test_relation_signature_mismatch():
    bad = relation("IS_A", entity("carro"))
    with pytest.raises(LIUError):
        check(bad)


def test_fingerprint_returns_stable_digest():
    node = normalize(sample_struct())
    assert fingerprint(node) == fingerprint(node)
    other = normalize(struct(subject=entity("carro")))
    assert fingerprint(node) != fingerprint(other)


def test_dedup_relations_removes_duplicates():
    rels = [
        relation("IS_A", entity("carro"), entity("veiculo")),
        relation("IS_A", entity("carro"), entity("veiculo")),
    ]
    deduped = dedup_relations(rels)
    assert len(deduped) == 1
