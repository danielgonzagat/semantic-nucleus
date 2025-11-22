from nsr.lc_omega import LCTerm, lc_term_from_pattern, lc_normalize, lc_synthesize


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
