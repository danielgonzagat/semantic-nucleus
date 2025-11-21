from liu import struct, list_node, text, entity, to_sexpr, parse_sexpr, normalize


def test_text_literals_survive_roundtrip():
    node = struct(
        subject=entity("carro"),
        metadata=list_node([text('rápido "demais"')]),
    )
    serialized = to_sexpr(node)
    assert '(TEXT:' in serialized
    parsed = parse_sexpr(serialized)
    assert parsed == normalize(node)
