"""
benchmark_tts_latency.py — Manual TTS latency benchmark.

This script is intentionally not collected by pytest.
"""

import argparse
import asyncio
import os
import shutil
import statistics
import time

from _bootstrap import PROJECT_ROOT, ensure_project_root_on_path

ensure_project_root_on_path()


def _load_runtime_deps():
    from core.config import settings
    from pipeline.visual.tts import synthesize_speech_async

    return settings, synthesize_speech_async


settings, synthesize_speech_async = _load_runtime_deps()


async def benchmark_tts_latency(language: str = "en") -> None:
    print(f"Testing TTS latency using provider: {settings.tts_provider}")

    test_texts = [
        "The bar chart shows a steady increase in quarterly revenue over the fiscal year.",
        "A Python code editor displays a main script with an error highlighted on line 42.",
        "The professor points to a complex chemical equation on the blackboard.",
        "A clear glass beaker holds a vibrant blue liquid, intensely swirling.",
        "The screen displays an abstract background of vertical, blurred streaks.",
    ]

    cache_dir = PROJECT_ROOT / "temp" / "latency_test"
    cache_dir.mkdir(parents=True, exist_ok=True)

    results = []

    # 1. Cold start test (first time generation)
    print("\n--- Cold Start Test ---")
    for i, text in enumerate(test_texts):
        out_path = str(cache_dir / f"cold_{i}.mp3")
        if os.path.exists(out_path):
            os.remove(out_path)

        start = time.perf_counter()
        await synthesize_speech_async(text, out_path, language=language)
        latency = (time.perf_counter() - start) * 1000  # ms

        print(f"Cold #{i}: {latency:.1f} ms")
        results.append({"type": "cold", "latency_ms": latency})

    # 2. Warm / Cached simulation
    # Our API checks os.path.exists() and returns FileResponse immediately.
    # We simulate this file system check.
    print("\n--- Cached Playback Test ---")
    for i, _text in enumerate(test_texts):
        out_path = str(cache_dir / f"cold_{i}.mp3")

        start = time.perf_counter()
        if os.path.exists(out_path):
            # FileResponse simulation
            pass
        latency = (time.perf_counter() - start) * 1000  # ms

        print(f"Cached #{i}: {latency:.2f} ms")
        results.append({"type": "cached", "latency_ms": latency})

    shutil.rmtree(cache_dir)

    cold = [r["latency_ms"] for r in results if r["type"] == "cold"]
    warm = [r["latency_ms"] for r in results if r["type"] == "cached"]

    med_cold = statistics.median(cold)
    med_warm = statistics.median(warm)

    print("\n=== Latency Summary ===")
    print(f"Median Cold TTS: {med_cold:.1f} ms")
    print(f"Median Cached TTS: {med_warm:.2f} ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark on-demand TTS latency")
    parser.add_argument(
        "--language",
        default="en",
        choices=settings.supported_languages,
        help="TTS language to benchmark",
    )
    args = parser.parse_args()
    asyncio.run(benchmark_tts_latency(args.language))
