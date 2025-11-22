from liu import NodeKind

from nsr import build_struct, tokenize
from nsr.lex import DEFAULT_LEXICON


def _field(node, name):
    return dict(node.fields).get(name)


def test_parser_detects_negation_and_subject_pt():
    text = "Eu não falo com você"
    tokens = tokenize(text, DEFAULT_LEXICON)
    struct_node = build_struct(tokens, language="pt", text_input=text)
    assert _field(struct_node, "sentence_type").label == "statement"
    negation_field = _field(struct_node, "negation")
    assert negation_field is not None and negation_field.kind is NodeKind.LIST
    assert negation_field.args[0].label == "não"
    action = _field(struct_node, "action")
    assert action is not None
    action_fields = dict(action.fields)
    assert action_fields["negated"].value is True
    subject = _field(struct_node, "subject")
    assert subject is not None
    subject_fields = dict(subject.fields)
    assert subject_fields["person"].label == "1"
    obj = _field(struct_node, "object")
    assert obj is not None
    assert obj.kind is NodeKind.ENTITY


def test_parser_identifies_questions_en():
    text = "What do you build?"
    tokens = tokenize(text, DEFAULT_LEXICON)
    struct_node = build_struct(tokens, language="en", text_input=text)
    assert _field(struct_node, "sentence_type").label == "question"
    assert _field(struct_node, "question_focus").label == "what"
    action = _field(struct_node, "action")
    assert action is not None
    assert dict(action.fields)["mood"].label == "interrogative"
    subject = _field(struct_node, "subject")
    assert subject is not None
    assert dict(subject.fields)["lemma"].label == "you"


def test_parser_handles_commands_es():
    text = "Ejecuta el plan ahora"
    tokens = tokenize(text, DEFAULT_LEXICON)
    struct_node = build_struct(tokens, language="es", text_input=text)
    assert _field(struct_node, "sentence_type").label == "command"
    action = _field(struct_node, "action")
    assert action is not None
    assert dict(action.fields)["mood"].label == "imperative"
    # commands often omit subject; ensure object recognized
    obj = _field(struct_node, "object")
    assert obj is not None
    assert obj.kind is NodeKind.ENTITY
