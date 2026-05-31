"""
tests/evaluation/location_probe.py — Benchmark Vertex AI locations for latency.

For each candidate region, sends 3 warm-up + 5 measured text-only requests
to gemini-2.5-flash. Reports median latency, error rate, and availability.

Usage:
    .venv\Scripts\python tests/evaluation/location_probe.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from statistics import median

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import settings  # noqa: E402

# ── Regions to probe (sorted by relevance for Kazakhstan/Astana) ──
CANDIDATES = [
    "europe-west4",       # Netherlands — ~5000 km, best latency for KZ
    "europe-west1",       # Belgium
    "asia-northeast1",    # Tokyo
    "asia-southeast1",    # Singapore
    "us-central1",        # Iowa — baseline (largest quota pool)
    "us-east4",           # Virginia
]

WARMUP_REQUESTS = 3
MEASURED_REQUESTS = 5
TEST_PROMPT = "Reply with exactly one word: ready."


def probe_location(location: str) -> dict:
    """Probe a single Vertex AI location.

    Returns a dict with availability, latency stats, and any errors.
    """
    from google import genai
    from google.genai import types

    result: dict = {
        "location": location,
        "available": False,
        "error": None,
        "latency_median_ms": None,
        "latency_min_ms": None,
        "latency_max_ms": None,
        "successes": 0,
        "failures": 0,
    }

    try:
        client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=location,
            http_options=types.HttpOptions(api_version="v1"),
        )
    except Exception as exc:
        result["error"] = f"client_init: {exc}"
        return result

    # Warmup
    for i in range(WARMUP_REQUESTS):
        try:
            resp = client.models.generate_content(
                model=settings.description_model,
                contents=TEST_PROMPT,
            )
            if resp.text is None:
                result["failures"] += 1
            else:
                result["successes"] += 1
        except Exception:
            pass  # warmup failures are silent

    # Measured
    latencies: list[float] = []
    for i in range(MEASURED_REQUESTS):
        try:
            start = time.perf_counter()
            resp = client.models.generate_content(
                model=settings.description_model,
                contents=TEST_PROMPT,
            )
            elapsed = time.perf_counter() - start
            if resp.text is not None:
                latencies.append(elapsed)
                result["successes"] += 1
            else:
                result["failures"] += 1
        except Exception as exc:
            result["failures"] += 1
            if result["error"] is None:
                msg = str(exc)[:200]
                result["error"] = f"{type(exc).__name__}: {msg}"

    if latencies:
        result["available"] = True
        result["latency_median_ms"] = round(median(latencies) * 1000)
        result["latency_min_ms"] = round(min(latencies) * 1000)
        result["latency_max_ms"] = round(max(latencies) * 1000)

    return result


def main() -> int:
    print("=" * 70)
    print("  Vertex AI Location Probe — gemini-2.5-flash from Kazakhstan")
    print("=" * 70)
    print()
    print(f"  Model:     {settings.description_model}")
    print(f"  Project:   {settings.google_cloud_project}")
    print(f"  Warmup:    {WARMUP_REQUESTS} requests")
    print(f"  Measured:  {MEASURED_REQUESTS} requests per location")
    print()

    results: list[dict] = []
    for i, location in enumerate(CANDIDATES):
        print(f"  [{i + 1}/{len(CANDIDATES)}] Probing {location} ...", end=" ", flush=True)
        result = probe_location(location)
        results.append(result)
        if result["available"]:
            print(
                f"OK — median={result['latency_median_ms']}ms "
                f"(min={result['latency_min_ms']}ms, max={result['latency_max_ms']}ms)"
            )
        else:
            print(f"FAIL — {result['error'] or 'no successful responses'}")

    # ── Summary ──
    print()
    print("=" * 70)
    print("  Results (sorted by median latency)")
    print("=" * 70)
    available = [r for r in results if r["available"]]
    unavailable = [r for r in results if not r["available"]]

    if available:
        available.sort(key=lambda r: r["latency_median_ms"] or float("inf"))
        print()
        print(f"  {'Location':<22s} {'Median':>8s} {'Min':>8s} {'Max':>8s} {'OK/Fail':>8s}")
        print(f"  {'─' * 22} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 8}")
        for r in available:
            print(
                f"  {r['location']:<22s} {r['latency_median_ms']:>5d}ms "
                f"{r['latency_min_ms']:>5d}ms {r['latency_max_ms']:>5d}ms "
                f"{r['successes']:>3d}/{r['successes'] + r['failures']:>3d}"
            )

    if unavailable:
        print()
        print(f"  Unavailable locations ({len(unavailable)}):")
        for r in unavailable:
            print(f"    - {r['location']}: {r['error']}")

    if available:
        best = available[0]
        print()
        print(f"  Recommended location: {best['location']}")
        print(f"  Reason: lowest median latency ({best['latency_median_ms']}ms), model available.")
        print()
        print(f"  To apply: set GOOGLE_CLOUD_LOCATION={best['location']} in .env")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
