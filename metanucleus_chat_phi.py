#!/usr/bin/env python3
"""Simple REPL wired to the upgraded PhiEngine."""

from __future__ import annotations

from metanucleus.phi_core import PhiEngine


def main() -> int:
    engine = PhiEngine()
    print("Metanúcleo – PhiEngine REPL")
    print("Digite 'sair' ou 'exit' para encerrar.\n")

    while True:
        try:
            text = input("você> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[metanúcleo] Sessão encerrada.")
            break
        if not text:
            continue
        if text.lower() in {"sair", "exit", "quit"}:
            print("[metanúcleo] Até logo.")
            break
        turn = engine.process(text)
        print(f"\n[META] intent={turn.intent.label} (conf={turn.intent.confidence:.2f})")
        if turn.frame:
            print(f"[META] frame={turn.frame.id} score={turn.frame.score}")
        print(turn.response + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
