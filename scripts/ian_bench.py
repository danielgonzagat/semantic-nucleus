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


def benchmark(instinct: IANInstinct, iterations: int, warmup: int) -> Tuple[List[float], int]:
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


def benchmark_long_text(instinct: IANInstinct, length: int, runs: int) -> List[float]:
    if length <= 0 or runs <= 0:
        return []
    base = " ".join(text for _, text in _iter_utterances())
    builder = []
    while len(" ".join(builder)) < length:
        builder.append(base)
    long_text = " ".join(builder)[:length]
    samples: List[float] = []
    for _ in range(runs):
        t0 = time.perf_counter()
        instinct.tokenize(long_text)
        samples.append(time.perf_counter() - t0)
    return samples


def compute_stats(samples: List[float]) -> Tuple[float, float, float, float]:
    if not samples:
        return 0.0, 0.0, 0.0, 0.0
    mean_s = statistics.fmean(samples)
    median_s = statistics.median(samples)
    if len(samples) >= 20:
        p95_s = statistics.quantiles(samples, n=100)[94]
    else:
        p95_s = max(samples)
    throughput = len(samples) / sum(samples) if sum(samples) else 0.0
    return mean_s, median_s, p95_s, throughput


def render_report(samples: List[float], peak_bytes: int) -> str:
    if not samples:
        return "Nenhuma amostra registrada."
    mean_s, median_s, p95_s, throughput = compute_stats(samples)
    return (
        f"calls={len(samples)} "
        f"mean={mean_s*1000:.3f}ms "
        f"median={median_s*1000:.3f}ms "
        f"p95={p95_s*1000:.3f}ms "
        f"throughput={throughput:.1f} rps "
        f"peak_mem={peak_bytes / 1_048_576:.2f} MiB"
    )


def render_long_report(samples: List[float], length: int) -> str:
    if not samples:
        return ""
    mean_s, _, p95_s, _ = compute_stats(samples)
    return f"tokenize(len={length}) mean={mean_s*1000:.3f}ms p95={p95_s*1000:.3f}ms"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark determinístico do IAN-Ω.")
    parser.add_argument("--iterations", type=int, default=2000, help="Número de amostras coletadas após o aquecimento (default: 2000).")
    parser.add_argument("--warmup", type=int, default=200, help="Chamadas descartadas para aquecimento (default: 200).")
    parser.add_argument("--long-length", type=int, default=0, help="Quando >0, mede tokenização de um texto longo com o tamanho indicado.")
    parser.add_argument("--long-runs", type=int, default=20, help="Número de execuções ao medir textos longos (default: 20).")
    parser.add_argument("--max-p95-ms", type=float, help="Falha se o p95 do reply() exceder este valor (ms).")
    parser.add_argument("--max-peak-mib", type=float, help="Falha se o pico de memória exceder este valor (MiB).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    instinct = IANInstinct.default()
    samples, peak = benchmark(instinct, iterations=args.iterations, warmup=args.warmup)
    report = render_report(samples, peak)
    print(report)
    stats = compute_stats(samples)
    peak_mib = peak / 1_048_576
    exit_code = 0
    if args.max_p95_ms is not None and stats[2] * 1_000 > args.max_p95_ms:
        print(f"ERROR: p95 {stats[2]*1000:.3f}ms > {args.max_p95_ms}ms", flush=True)
        exit_code = 1
    if args.max_peak_mib is not None and peak_mib > args.max_peak_mib:
        print(f"ERROR: peak_mem {peak_mib:.2f}MiB > {args.max_peak_mib}MiB", flush=True)
        exit_code = 1
    long_samples = benchmark_long_text(instinct, args.long_length, args.long_runs)
    if long_samples:
        print(render_long_report(long_samples, args.long_length))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
