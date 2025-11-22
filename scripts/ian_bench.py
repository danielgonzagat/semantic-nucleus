#!/usr/bin/env python3
"""
Benchmark determinístico para o instinto IAN-Ω.

Mede latência média/mediana/p95 e pico de memória durante chamadas `IANInstinct.reply`
para os idiomas suportados atualmente (pt, en, es, fr, it).
"""

from __future__ import annotations

import argparse
import statistics
import time
import tracemalloc
from typing import Dict, Iterable, List, Tuple

from nsr.ian import IANInstinct


SAMPLE_UTTERANCES: Dict[str, Tuple[str, ...]] = {
    "pt": ("oi", "tudo bem?", "como você está?"),
    "en": ("hi", "how are you?", "i am fine"),
    "es": ("hola", "todo bien?", "¿cómo estás?"),
    "fr": ("bonjour", "tout va bien?", "comment ça va?"),
    "it": ("ciao", "tutto bene?", "come stai?"),
}


def _iter_utterances() -> Iterable[Tuple[str, str]]:
    for lang, utterances in SAMPLE_UTTERANCES.items():
        for text in utterances:
            yield lang, text


def benchmark(iterations: int, warmup: int) -> Tuple[List[float], int]:
    instinct = IANInstinct.default()
    utterances = tuple(_iter_utterances())
    if not utterances:
        raise RuntimeError("Nenhuma frase de benchmark configurada.")

    tracemalloc.start()
    samples: List[float] = []
    total_calls = warmup + iterations
    for idx in range(total_calls):
        lang, text = utterances[idx % len(utterances)]
        t0 = time.perf_counter()
        instinct.reply(text)
        elapsed = time.perf_counter() - t0
        if idx >= warmup:
            samples.append(elapsed)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return samples, peak


def render_report(samples: List[float], peak_bytes: int) -> str:
    if not samples:
        return "Nenhuma amostra registrada."
    mean_ms = statistics.fmean(samples) * 1_000
    median_ms = statistics.median(samples) * 1_000
    p95_ms = statistics.quantiles(samples, n=100)[94] * 1_000 if len(samples) >= 20 else max(samples) * 1_000
    throughput = len(samples) / sum(samples)
    return (
        f"calls={len(samples)} "
        f"mean={mean_ms:.3f}ms "
        f"median={median_ms:.3f}ms "
        f"p95={p95_ms:.3f}ms "
        f"throughput={throughput:.1f} rps "
        f"peak_mem={peak_bytes / 1_048_576:.2f} MiB"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark determinístico do IAN-Ω.")
    parser.add_argument("--iterations", type=int, default=2000, help="Número de amostras coletadas após o aquecimento (default: 2000).")
    parser.add_argument("--warmup", type=int, default=200, help="Chamadas descartadas para aquecimento (default: 200).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    samples, peak = benchmark(iterations=args.iterations, warmup=args.warmup)
    print(render_report(samples, peak))


if __name__ == "__main__":
    main()
