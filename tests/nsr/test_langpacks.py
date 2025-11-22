import json

from nsr.ian import CONJUGATION_TABLE, IANInstinct
from nsr import langpacks
from nsr.langpacks import get_language_pack, iter_language_packs, list_available_codes


def test_language_pack_exposes_dialog_rules():
    langpacks.reload_external_packs()
    pack = get_language_pack("fr")
    assert any(rule.reply_role == "ANSWER_HEALTH_FR" for rule in pack.dialog_rules)
    assert any(lex.lemma == "BONJOUR" for lex in pack.lexemes)
    assert "LE" in pack.stopwords
    pack_it = get_language_pack("it")
    assert any(rule.reply_role == "ANSWER_HEALTH_IT" for rule in pack_it.dialog_rules)
    assert any(lex.lemma == "CIAO" for lex in pack_it.lexemes)
    assert "IL" in pack_it.stopwords


def test_iter_language_packs_returns_all_requested_codes():
    langpacks.reload_external_packs()
    packs = iter_language_packs(("pt", "en"))
    assert {pack.code for pack in packs} == {"pt", "en"}


def test_conjugations_from_language_packs_register_on_default_instinct():
    langpacks.reload_external_packs()
    instinct = IANInstinct.default()
    assert instinct.lexicon  # sanity
    key = ("aller", "pres", "1", "sing")
    assert CONJUGATION_TABLE[key] == "vais"


def test_list_available_codes_includes_base_languages():
    langpacks.reload_external_packs()
    codes = list_available_codes()
    assert {"pt", "en", "es", "fr", "it"}.issubset(set(codes))


def test_import_language_pack(tmp_path, monkeypatch):
    monkeypatch.setattr(langpacks, "LANGPACKS_DIR", tmp_path, raising=False)
    tmp_path.mkdir(parents=True, exist_ok=True)
    langpacks.reload_external_packs()
    payload = {
        "code": "it",
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
        "conjugations": [],
    }
    source_file = tmp_path / "it_pack.json"
    source_file.write_text(json.dumps(payload), encoding="utf-8")
    code = langpacks.import_language_pack(None, str(source_file))
    langpacks.reload_external_packs()
    pack = get_language_pack(code)
    assert pack.code == "it"
    assert any(rule.reply_role == "GREETING_SIMPLE_IT_REPLY" for rule in pack.dialog_rules)
