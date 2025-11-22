from liu import entity, list_node, relation, struct

from nsr.explain import render_struct_sentence


def _ian_answer_stub(language_code: str):
    return struct(plan_language=entity(language_code))


def _relation_struct(language_code: str):
    rel = relation("HAS", entity("carro"), entity("roda"))
    return struct(language=entity(language_code), relations=list_node([rel]))


def test_render_struct_sentence_defaults_to_portuguese_placeholder():
    node = struct()
    rendered = render_struct_sentence(node)
    assert rendered.startswith("Resposta não determinada")


def test_render_struct_sentence_respects_english_plan_language():
    node = _ian_answer_stub("en")
    rendered = render_struct_sentence(node, language="en")
    assert rendered.startswith("Answer not determined")


def test_render_struct_sentence_respects_spanish_plan_language():
    node = _ian_answer_stub("es")
    rendered = render_struct_sentence(node, language="es")
    assert rendered.startswith("Respuesta no determinada")


def test_render_struct_sentence_respects_french_plan_language():
    node = _ian_answer_stub("fr")
    rendered = render_struct_sentence(node, language="fr")
    assert rendered.startswith("Réponse non déterminée")


def test_render_struct_sentence_localizes_relations_intro():
    node = _relation_struct("es")
    rendered = render_struct_sentence(node, language="es")
    assert "Relaciones: carro has roda" in rendered
