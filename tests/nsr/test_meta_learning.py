from liu import entity, relation, struct

from nsr.meta_learning import MetaLearningEngine


def test_meta_learning_transitivity_rule() -> None:
    engine = MetaLearningEngine()
    context = (
        relation("FRIEND_OF", entity("a"), entity("b")),
        relation("FRIEND_OF", entity("b"), entity("c")),
        relation("FRIEND_OF", entity("d"), entity("e")),
        relation("FRIEND_OF", entity("e"), entity("f")),
    )

    rules = engine.learn_from_trace(struct(), context)

    assert rules, "esperava pelo menos uma regra transitiva"
    rule = rules[0]
    assert len(rule.if_all) == 2
    assert rule.then.label == "FRIEND_OF"


def test_meta_learning_symmetric_rule() -> None:
    engine = MetaLearningEngine()
    context = (
        relation("LIKES", entity("anna"), entity("bob")),
        relation("LIKES", entity("bob"), entity("anna")),
        relation("LIKES", entity("cara"), entity("dave")),
        relation("LIKES", entity("dave"), entity("cara")),
    )

    rules = engine.learn_from_trace(struct(), context)

    assert rules, "esperava pelo menos uma regra simétrica"
    rule = rules[0]
    assert len(rule.if_all) == 1
    assert rule.if_all[0].label == "LIKES"
    # consequent deve inverter os placeholders
    assert rule.then.args[0].label == "?y"
    assert rule.then.args[1].label == "?x"
