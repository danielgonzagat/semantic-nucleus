from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Dict, Optional
from uuid import uuid4

from metanucleus.kernel.meta_kernel import MetaKernel


@dataclass
class ChatConfig:
    show_debug_banner: bool = True
    prompt_user: str = "você"
    prompt_core: str = "núcleo"
    exit_commands: tuple[str, ...] = ("/exit", "/quit", "/sair")
    debug_commands: tuple[str, ...] = ("/state", "/debug")


@dataclass
class ChatSession:
    kernel: MetaKernel = field(default_factory=MetaKernel)
    session_id: str = field(default_factory=lambda: f"cli-{uuid4().hex[:8]}")
    last_debug: Dict[str, object] = field(default_factory=dict)

    def ask(self, text: str) -> str:
        result = self.kernel.handle_turn(user_text=text, session_id=self.session_id)
        self.last_debug = result.debug_info
        return result.answer_text

    def inspect_state(self) -> Dict[str, object]:
        return {
            "session_id": self.session_id,
            "debug": self.last_debug,
            "state_metrics": {
                "total_requests": self.kernel.state.metrics.total_requests,
                "semantic_events": self.kernel.state.metrics.semantic_events,
            },
        }


def _print_banner(cfg: ChatConfig) -> None:
    print()
    print("========================================")
    print("         Metanúcleo – REPL Chat         ")
    print("========================================")
    print("Idiomas suportados: PT/EN (multi-turno).")
    print("Comandos especiais:")
    print(f"  {', '.join(cfg.exit_commands)}  → sair")
    print(f"  {', '.join(cfg.debug_commands)} → inspeção do estado interno")
    print("========================================")
    print()


def _handle_debug(session: ChatSession) -> None:
    print()
    print("------ [DEBUG: estado interno do Metanúcleo] ------")
    print(session.inspect_state())
    print("---------------------------------------------------")
    print()


def chat_loop(cfg: Optional[ChatConfig] = None) -> int:
    cfg = cfg or ChatConfig()
    session = ChatSession()

    if cfg.show_debug_banner:
        _print_banner(cfg)

    while True:
        try:
            user_text = input(f"{cfg.prompt_user}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print("encerrando sessão...")
            break

        if not user_text:
            continue

        if user_text in cfg.exit_commands:
            print("encerrando sessão...")
            break

        if user_text in cfg.debug_commands:
            _handle_debug(session)
            continue

        try:
            reply = session.ask(user_text)
        except Exception as exc:  # pragma: no cover - manter REPL vivo
            print(f"{cfg.prompt_core}: [erro interno: {exc!r}]")
            continue

        print(f"{cfg.prompt_core}: {reply}")

    return 0


def main() -> None:
    try:
        code = chat_loop()
    except Exception as exc:  # pragma: no cover
        print(f"[metanucleus-chat] erro fatal: {exc!r}", file=sys.stderr)
        code = 1
    raise SystemExit(code)


if __name__ == "__main__":  # pragma: no cover
    main()
