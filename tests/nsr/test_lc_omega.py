from nsr.lc_omega import LCTerm, lc_parse, lc_term_from_pattern, lc_normalize, lc_synthesize


def test_lc_term_from_pattern_pt_question():
    term = lc_term_from_pattern("pt", "QUESTION_HEALTH_VERBOSE")
    assert term.kind == "SEQ"
    assert [child.label for child in term.children] == ["QUESTION_HOW", "YOU", "BE_STATE"]


def test_lc_normalize_removes_duplicates():
    term = LCTerm(kind="SEQ", children=(LCTerm(kind="SYM", label="A"), LCTerm(kind="SYM", label="A")))
    normalized = lc_normalize(term)
    assert len(normalized.children) == 1


def test_lc_synthesize_uses_language_pack():
    term = lc_term_from_pattern("es", "QUESTION_HEALTH_ES")
    tokens = lc_synthesize(term, "es")
    assert tokens == ("todo", "bien")


def test_lc_parse_produces_meta_calculus_for_question():
    result = lc_parse("pt", "como você está?")
    assert result.pattern == "QUESTION_HEALTH_VERBOSE"
    assert result.calculus is not None
    calc = result.calculus
    assert calc.operator == "STATE_QUERY"
    equation = calc.operands[0]
    assert equation.kind == "EQ"
    assert equation.label == "?"
    lhs = equation.children[0]
    assert lhs.label == "STATE_OF"
    assert lhs.children[0].label == "YOU"


def test_lc_parse_tracks_literals_and_numbers():
    result = lc_parse("pt", "tudo bem 9")
    assert result.semantics[-1] == "NUM:9"
    assert result.calculus is None
