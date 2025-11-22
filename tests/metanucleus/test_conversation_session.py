from __future__ import annotations

from metanucleus.core.state import MetaState
from metanucleus.runtime.meta_runtime import MetaRuntime
from metanucleus.runtime.conversation import (
    ConversationSession,
    ConversationState,
    MemoryConfig,
)


def _mk_session(cfg: MemoryConfig | None = None) -> ConversationSession:
    state = MetaState()
    runtime = MetaRuntime(state=state)
    return ConversationSession(runtime=runtime, state=ConversationState(), cfg=cfg or MemoryConfig())


def test_conversation_tracks_topics_and_memory():
    session = _mk_session()
    reply1 = session.handle_user_message("oi, tudo bem?")
    reply2 = session.handle_user_message("quero saber mais sobre o núcleo simbólico")

    assert isinstance(reply1, str)
    assert isinstance(reply2, str)

    # dois turns de usuário + dois turns meta
    assert len(session.state.turns) == 4
    user_turns = [t for t in session.state.turns if t.role == "user"]
    assert session.state.active_topic_id is not None
    assert len(session.state.short_mem[session.state.active_topic_id]) >= 1
    # pelo menos um tópico ativo registrado
    assert session.state.topics


def test_conversation_promotes_to_long_memory_when_needed():
    cfg = MemoryConfig(max_short=2, max_long=2, min_tokens_for_long=3)
    session = _mk_session(cfg)

    session.handle_user_message("preciso de detalhes técnicos sobre o metanúcleo simbólico")
    session.handle_user_message("ok, e sobre a auto evolução supervisionada?")
    session.handle_user_message("agora fale de inteligência determinística")

    # long memory deve ter recebido itens
    assert session.state.long_mem  # não vazio
    # short memory mantém apenas os últimos 2 ids
    active = session.state.active_topic_id
    assert active is not None
    assert len(session.state.short_mem[active]) <= cfg.max_short


def test_conversation_context_injects_previous_turns():
    session = _mk_session()
    session.handle_user_message("lembrar: preciso testar o núcleo")
    session.handle_user_message("lembrar: preciso evoluir o núcleo")
    answer = session.handle_user_message("quais foram os lembretes anteriores?")

    assert "lembrar" in answer.lower()
