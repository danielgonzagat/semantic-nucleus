from types import SimpleNamespace

from liu import entity, relation, struct

from nsr.meta_learning import MetaLearningEngine
from nsr.runtime import _maybe_run_meta_learning
from nsr.state import SessionCtx


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


def test_meta_learning_integration_updates_session_rules() -> None:
    session = SessionCtx()
    context = (
        relation("CONNECTED", entity("a"), entity("b")),
        relation("CONNECTED", entity("b"), entity("c")),
        relation("CONNECTED", entity("d"), entity("e")),
        relation("CONNECTED", entity("e"), entity("f")),
    )
    outcome = SimpleNamespace(
        quality=0.95,
        isr=SimpleNamespace(context=context),
        meta_summary=None,
    )

    _maybe_run_meta_learning(session, outcome)

    assert session.kb_rules, "meta-learning deveria adicionar regras na sessão"
    summary = session.meta_history[-1][0]
    fields = dict(summary.fields)
    assert fields["tag"].label == "meta_learning"
