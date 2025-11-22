from metanucleus.lang.lxu_pse import parse_utterance, UtteranceIntent


def test_parse_utterance_detects_intent_and_subject():
    utter = parse_utterance("Oi Metanúcleo, tudo bem com você?")
    assert utter.fields["intent"].label == UtteranceIntent.QUESTION.value
    assert utter.fields["lang"].label == "pt"
    assert "tokens" in utter.fields
    # subject fallback to pronoun or main token
    assert utter.fields.get("subject").label.lower() in {"metanúcleo", "metanucleo", "oi", "você", "voce"}


def test_parse_command_in_english():
    utter = parse_utterance("Explain 2 + 2 to me")
    assert utter.fields["intent"].label == UtteranceIntent.COMMAND.value
    assert utter.fields["lang"].label in {"en", "pt"}
    tokens_struct = utter.fields["tokens"]
    assert len(tokens_struct.fields) >= 3
