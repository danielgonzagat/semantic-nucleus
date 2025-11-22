from nsr.ian import CONJUGATION_TABLE, IANInstinct
from nsr.langpacks import get_language_pack, iter_language_packs


def test_language_pack_exposes_dialog_rules():
    pack = get_language_pack("fr")
    assert any(rule.reply_role == "ANSWER_HEALTH_FR" for rule in pack.dialog_rules)
    assert any(lex.lemma == "BONJOUR" for lex in pack.lexemes)


def test_iter_language_packs_returns_all_requested_codes():
    packs = iter_language_packs(("pt", "en"))
    assert {pack.code for pack in packs} == {"pt", "en"}


def test_conjugations_from_language_packs_register_on_default_instinct():
    instinct = IANInstinct.default()
    assert instinct.lexicon  # sanity
    key = ("aller", "pres", "1", "sing")
    assert CONJUGATION_TABLE[key] == "vais"
