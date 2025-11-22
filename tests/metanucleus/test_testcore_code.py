from metanucleus.test.testcore import compare_code_versions


def test_compare_code_versions_equivalent():
    original = """
def soma(a, b):
    return a + b
"""
    candidate = """
def soma(a, b):
    return a + b
"""
    report = compare_code_versions(original, candidate)
    assert report["equivalent"] is True
    assert report["diff"] == ""


def test_compare_code_versions_detects_change():
    original = "def inc(x):\n    return x + 1\n"
    candidate = "def inc(x):\n    return x + 2\n"
    report = compare_code_versions(original, candidate)
    assert report["equivalent"] is False
    assert "-    return x + 1" in report["diff"]
