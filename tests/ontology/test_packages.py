from ontology import core, code
from liu import check


def test_core_ontology_is_wf():
    for fact in core.facts():
        check(fact)
    assert any(rel.label == "IS_A" for rel in core.facts())


def test_code_ontology_annotations_exist():
    annotations = [rel for rel in code.facts() if rel.label == "code/ANNOTATION"]
    assert annotations
    for rel in annotations:
        check(rel)
