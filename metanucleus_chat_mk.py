"""REPL focused on the MetaKernel end-to-end pipeline."""
from __future__ import annotations

from metanucleus.metakernel import metakernel_process


def main() -> int:
    print("Metanúcleo – Chat simbólico (intent + semantics + frames + calculus)")
    print("Digite /exit para sair.\n")

    while True:
        try:
            text = input("você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando.")
            break
        if not text:
            continue
        if text == "/exit":
            print("Sessão encerrada.")
            break

        result = metakernel_process(text)
        print("\nnúcleo:")
        print(f"  intent:    {result.intent.label} (conf={result.intent.confidence:.2f})")
        print(f"  semantics: {result.semantics.label} (conf={result.semantics.confidence:.2f})")
        print(f"  liu:       {result.liu.fields} (conf={result.liu.confidence:.2f})")
        print(f"  frame:     {result.frames.frame_type} roles={result.frames.roles} (conf={result.frames.confidence:.2f})")
        if result.calculus.kind != "none":
            print(
                f"  calculus:  {result.calculus.expression_normalized} = {result.calculus.result} "
                f"(conf={result.calculus.confidence:.2f})"
            )
        print(f"  meta-conf: {result.confidence:.2f}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
