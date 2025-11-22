from nsr import MetaTransformer, MetaRoute, SessionCtx


def test_meta_transformer_routes_math():
    session = SessionCtx()
    transformer = MetaTransformer(session)
    result = transformer.transform("2+2")
    assert result.route is MetaRoute.MATH
    assert result.preseed_answer is not None
    assert result.trace_label and result.trace_label.startswith("MATH[")
    assert session.language_hint == result.language_hint


def test_meta_transformer_routes_logic():
    session = SessionCtx()
    transformer = MetaTransformer(session)
    result = transformer.transform("FACT chuva")
    assert result.route is MetaRoute.LOGIC
    assert result.preseed_answer is not None
    assert result.trace_label == "LOGIC[FACT]"
    assert session.logic_engine is not None


def test_meta_transformer_routes_instinct():
    session = SessionCtx()
    transformer = MetaTransformer(session)
    result = transformer.transform("oi, tudo bem?")
    assert result.route is MetaRoute.INSTINCT
    assert result.preseed_quality and result.preseed_quality > 0.8
    assert result.trace_label and result.trace_label.startswith("IAN[")
    assert session.language_hint == result.language_hint


def test_meta_transformer_falls_back_to_text_route():
    session = SessionCtx()
    transformer = MetaTransformer(session)
    result = transformer.transform("O carro tem roda")
    assert result.route is MetaRoute.TEXT
    assert result.preseed_answer is None
    assert result.trace_label is None
    assert result.preseed_context is not None
    tags = {dict(node.fields)["tag"].label for node in result.preseed_context}
    assert "meta_route" in tags
    assert "meta_input" in tags
    language_field = dict(result.struct_node.fields).get("language")
    assert language_field is not None
    assert (language_field.label or "").startswith("pt")


def test_meta_transformer_routes_code_snippet():
    session = SessionCtx()
    transformer = MetaTransformer(session)
    code_text = """
def soma(x, y):
    return x + y
"""
    result = transformer.transform(code_text)
    assert result.route is MetaRoute.CODE
    assert result.preseed_answer is not None
    assert result.trace_label == "CODE[PYTHON]"
    assert result.preseed_quality and result.preseed_quality >= 0.85
    assert any((dict(node.fields)["tag"].label == "meta_route") for node in result.preseed_context)
