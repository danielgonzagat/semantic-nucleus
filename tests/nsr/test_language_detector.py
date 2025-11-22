from nsr.language_detector import detect_language_profile, language_profile_to_node


def test_detects_portuguese_text():
    result = detect_language_profile("O carro está muito rápido e você sabe disso.")
    assert result.category == "text"
    assert result.language == "pt"
    assert result.confidence > 0.05
    assert "VOCÊ" in result.hints or "ESTÁ" in result.hints


def test_detects_spanish_text():
    result = detect_language_profile("El coche tiene una rueda nueva y no hay problema.")
    assert result.language == "es"
    assert result.category == "text"
    assert result.confidence > 0.05


def test_detects_python_code():
    code = """
def soma(x, y):
    return x + y
"""
    result = detect_language_profile(code)
    assert result.category == "code"
    assert result.dialect == "python"
    assert result.confidence > 0.05


def test_language_profile_node_serialization():
    result = detect_language_profile("Bonjour, comment est la voiture?")
    node = language_profile_to_node(result)
    assert node is not None
    fields = dict(node.fields)
    assert fields["tag"].label == "language_profile"
    assert fields["category"].label == "text"
    assert fields["language"].label == "fr"
