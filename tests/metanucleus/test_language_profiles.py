from metanucleus.core.lang_profiles import (
    detect_language,
    extract_language_features,
    normalize_for_language,
)
from metanucleus.lang.lxu_pse import parse_utterance


def test_detect_language_spanish():
    guess = detect_language("Hola, ¿cómo estás?")
    assert guess.code == "es"
    assert guess.confidence > 0


def test_language_features_greeting_italian():
    lf = extract_language_features("Ciao, come stai?")
    assert lf.lang == "it"
    assert lf.is_greeting_like


def test_normalize_removes_stopwords():
    tokens = normalize_for_language("O Metanúcleo é realmente incrível", lang_code="pt")
    assert "metanúcleo" in tokens
    assert "o" not in tokens


def test_parse_utterance_handles_french():
    node = parse_utterance("Bonjour, explique le noyau symbolique.")
    assert node.fields["lang"].label == "fr"
    assert node.fields["intent"].label in {"question", "statement", "greeting"}
