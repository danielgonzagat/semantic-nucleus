from nsr.langpacks import build_language_pack_from_dict
from nsr.langpacks_validator import has_errors, validate_pack


def _make_payload():
    return {
        "lexemes": [
            {"lemma": "CIAO", "semantics": "GREETING_SIMPLE", "pos": "INTERJ", "forms": ["CIAO"]},
        ],
        "dialog_rules": [
            {
                "trigger_role": "GREETING_SIMPLE_IT",
                "reply_role": "GREETING_SIMPLE_IT_REPLY",
                "reply_semantics": "GREETING_SIMPLE",
                "surface_tokens": ["ciao"],
                "language": "it",
            }
        ],
        "conjugations": [
            {"lemma": "stare", "tense": "pres", "person": 1, "number": "sing", "form": "STO"},
        ],
        "stopwords": [],
        "syntactic_patterns": [
            {"name": "GREETING_SIMPLE_IT", "sequence": ["GREETING_SIMPLE"]},
        ],
    }


def test_validate_pack_ok():
    payload = _make_payload()
    pack = build_language_pack_from_dict("it", payload)
    issues = validate_pack(pack)
    assert not issues
    assert has_errors(issues) is False


def test_validate_pack_detects_lowercase_forms():
    payload = _make_payload()
    payload["lexemes"][0]["forms"] = ["Ciao"]
    pack = build_language_pack_from_dict("it", payload)
    issues = validate_pack(pack)
    assert has_errors(issues) is True
    assert any("must be uppercase" in issue.message for issue in issues)
