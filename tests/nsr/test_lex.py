import json

import pytest

from nsr.lex import compose_lexicon, load_lexicon_file


def test_compose_lexicon_merges_language_packs():
    lex = compose_lexicon(("pt", "es", "fr"))
    assert lex.synonyms["coche"] == "carro"
    assert lex.synonyms["voiture"] == "carro"
    assert lex.rel_words["tiene"] == "HAS"
    assert lex.rel_words["avec"] == "HAS"


def test_load_lexicon_file_builds_custom_pack(tmp_path):
    data = {
        "synonyms": {"árvore": "tree"},
        "pos_hint": {"voler": "ACTION"},
        "qualifiers": ["ágil"],
        "rel_words": {"sobre": "HAS"},
    }
    path = tmp_path / "lex.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    lex = load_lexicon_file(path)
    assert lex.synonyms["árvore"] == "tree"
    assert lex.pos_hint["voler"] == "ACTION"
    assert "ágil" in lex.qualifiers
    assert lex.rel_words["sobre"] == "HAS"


def test_compose_lexicon_raises_for_unknown_pack():
    with pytest.raises(ValueError):
        compose_lexicon(("xx",))
