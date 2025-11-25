"""Simple REPL that exposes the symbolic conversation session."""
from __future__ import annotations

from metanucleus.conversation_session import ConversationSession


def main() -> int:
    session = ConversationSession(memory_size=100)
    print("Metanúcleo – REPL simbólico")
    print("Digite /mem para ver memória, /exit para sair.\n")

    while True:
        try:
            text = input("você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando sessão.")
            break
        if not text:
            continue
        if text == "/exit":
            print("Sessão encerrada.")
            break
        if text == "/mem":
            snapshot = session.memory.as_debug_dict()
            print(f"\n[MEMÓRIA] tamanho: {snapshot['size']}")
            for entry in snapshot["last_entries"]:
                print(f"- [{entry['role']}] intent={entry['intent']} sem={entry['semantics']} liu={entry['liu']}")
                print(f"    texto: {entry['text']}")
            print()
            continue

        result = session.process_user_message(text)
        print("\nnúcleo:")
        print(f"  intent:   {result.intent.label} (conf={result.intent.confidence:.2f})")
        print(f"  semantics:{result.semantics.label} (conf={result.semantics.confidence:.2f})")
        print(f"  liu:      {result.liu.fields} (conf={result.liu.confidence:.2f})\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
