"""Measure API endpoint latency against a running Prototype server.

Requirements:
    Start the API separately before running this script:
        uvicorn api.server:app --port 8000

Usage:
    python tests/evaluation/analyze_api.py
    python tests/evaluation/analyze_api.py --base http://localhost:8000
    python tests/evaluation/analyze_api.py --job test_1770867214 --save
"""

import argparse
import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from _bootstrap import PROJECT_ROOT


def api_call(method: str, url: str, body: dict = None) -> dict:
    """Execute an HTTP request and return the response plus timing data.

    Returns:
        {
            "status": 200,
            "latency_ms": 45.2,
            "body": {...},
            "error": None,
        }
    """
    headers = {"Content-Type": "application/json"}
    data = json.dumps(body).encode("utf-8") if body else None

    req = Request(url, data=data, headers=headers, method=method)

    t0 = time.time()
    try:
        with urlopen(req, timeout=60) as resp:
            latency = (time.time() - t0) * 1000
            response_body = json.loads(resp.read().decode("utf-8"))
            return {
                "status": resp.status,
                "latency_ms": round(latency, 1),
                "body": response_body,
                "error": None,
            }
    except HTTPError as e:
        latency = (time.time() - t0) * 1000
        try:
            error_body = json.loads(e.read().decode("utf-8"))
        except Exception:
            error_body = {"detail": str(e)}
        return {
            "status": e.code,
            "latency_ms": round(latency, 1),
            "body": error_body,
            "error": error_body.get("detail", str(e)),
        }
    except URLError as e:
        return {
            "status": 0,
            "latency_ms": 0,
            "body": None,
            "error": f"Connection failed: {e.reason}",
        }


def run_tests(base_url: str, job_id: str = None, save: bool = False) -> dict:
    """Test the main API endpoints against a running server.

    Args:
        base_url: Base URL of the API server.
        job_id: Specific job id to test. If omitted, the first job is used.
        save: Whether to persist the report to disk.
    """
    results = []
    base = base_url.rstrip("/")

    # ── 1. Health check ───────────────────────────────────────────
    print("Testing /health...")
    r = api_call("GET", f"{base}/health")
    results.append({"endpoint": "GET /health", **r})
    print(f"  {r['status']}  {r['latency_ms']}ms")

    if r["status"] != 200:
        print()
        print("ERROR: Server is not responding. Make sure to start it first:")
        print("  uvicorn api.server:app --port 8000")
        sys.exit(1)

    server_info = r["body"]

    # ── 2. List jobs ──────────────────────────────────────────────
    print("Testing /jobs...")
    r = api_call("GET", f"{base}/jobs")
    results.append({"endpoint": "GET /jobs", **r})
    print(f"  {r['status']}  {r['latency_ms']}ms  ({len(r['body'].get('jobs', []))} jobs)")

    # Auto-detect job_id if not specified
    if not job_id:
        jobs = r["body"].get("jobs", [])
        if jobs:
            job_id = jobs[0]["job_id"]
            print(f"  Auto-selected job: {job_id}")
        else:
            print("  No jobs found. Process a video first.")
            sys.exit(1)

    # ── 3. Get scenes ─────────────────────────────────────────────
    print(f"Testing /jobs/{job_id}/scenes...")
    r = api_call("GET", f"{base}/jobs/{job_id}/scenes")
    results.append({"endpoint": "GET /jobs/{id}/scenes", **r})
    scene_count = len(r["body"].get("scenes", [])) if r["body"] else 0
    print(f"  {r['status']}  {r['latency_ms']}ms  ({scene_count} scenes)")

    scenes = r["body"].get("scenes", []) if r["body"] else []

    # ── 4. Describe scene (cold — first TTS generation) ───────────
    if scenes:
        # Find a scene without TTS cache
        test_scene = next((s for s in scenes if not s.get("tts_cached", False)), scenes[0])
        test_time = test_scene["time"]

        print(f"Testing /jobs/{job_id}/describe (time={test_time:.1f}, cold)...")
        r = api_call(
            "POST",
            f"{base}/jobs/{job_id}/describe",
            {"time": test_time, "language": "en"},
        )
        results.append(
            {
                "endpoint": "POST /jobs/{id}/describe (cold)",
                **r,
            }
        )
        if r["body"]:
            print(
                f"  {r['status']}  {r['latency_ms']}ms  "
                f"scene_id={r['body'].get('scene_id')}  "
                f"tts={r['body'].get('tts_duration_sec', 0):.1f}s"
            )
        else:
            print(f"  {r['status']}  {r['latency_ms']}ms  error={r['error']}")

        # ── 5. Describe same scene (warm — from cache) ────────────
        print(f"Testing /jobs/{job_id}/describe (time={test_time:.1f}, cached)...")
        r = api_call(
            "POST",
            f"{base}/jobs/{job_id}/describe",
            {"time": test_time, "language": "en"},
        )
        results.append(
            {
                "endpoint": "POST /jobs/{id}/describe (cached)",
                **r,
            }
        )
        if r["body"]:
            print(f"  {r['status']}  {r['latency_ms']}ms  (from cache)")
        else:
            print(f"  {r['status']}  {r['latency_ms']}ms")

        # ── 6. Get TTS audio ──────────────────────────────────────
        scene_id = test_scene["scene_id"]
        print(f"Testing /jobs/{job_id}/tts/{scene_id}...")
        # TTS returns binary MP3, not JSON — measure with raw request
        t0 = time.time()
        try:
            req = Request(f"{base}/jobs/{job_id}/tts/{scene_id}")
            with urlopen(req) as resp:
                audio_data = resp.read()
                latency = (time.time() - t0) * 1000
                results.append(
                    {
                        "endpoint": "GET /jobs/{id}/tts/{scene_id}",
                        "status": resp.status,
                        "latency_ms": round(latency, 1),
                        "body": {"size_bytes": len(audio_data)},
                        "error": None,
                    }
                )
                print(f"  {resp.status}  {latency:.1f}ms  ({len(audio_data)} bytes)")
        except Exception as e:
            results.append(
                {
                    "endpoint": "GET /jobs/{id}/tts/{scene_id}",
                    "status": 0,
                    "latency_ms": 0,
                    "body": None,
                    "error": str(e),
                }
            )
            print(f"  ERROR: {e}")

    # ── 7. Get subtitles ──────────────────────────────────────────
    print(f"Testing /jobs/{job_id}/subtitles...")
    t0 = time.time()
    try:
        req = Request(f"{base}/jobs/{job_id}/subtitles")
        with urlopen(req) as resp:
            vtt_data = resp.read()
            latency = (time.time() - t0) * 1000
            results.append(
                {
                    "endpoint": "GET /jobs/{id}/subtitles",
                    "status": resp.status,
                    "latency_ms": round(latency, 1),
                    "body": {"size_bytes": len(vtt_data)},
                    "error": None,
                }
            )
            print(f"  {resp.status}  {latency:.1f}ms  ({len(vtt_data)} bytes)")
    except Exception as e:
        results.append(
            {
                "endpoint": "GET /jobs/{id}/subtitles",
                "status": 0,
                "latency_ms": 0,
                "body": None,
                "error": str(e),
            }
        )

    # ── 8. Get video (check headers only — cancel after connect) ──
    print(f"Testing /jobs/{job_id}/video...")
    t0 = time.time()
    try:
        req = Request(f"{base}/jobs/{job_id}/video")
        with urlopen(req) as resp:
            latency = (time.time() - t0) * 1000
            content_type = resp.headers.get("content-type", "")
            content_length = resp.headers.get("content-length", "?")
            results.append(
                {
                    "endpoint": "GET /jobs/{id}/video",
                    "status": resp.status,
                    "latency_ms": round(latency, 1),
                    "body": {
                        "content_type": content_type,
                        "content_length": content_length,
                    },
                    "error": None,
                }
            )
            print(f"  {resp.status}  {latency:.1f}ms  ({content_type}, {content_length} bytes)")
    except Exception as e:
        results.append(
            {
                "endpoint": "GET /jobs/{id}/video",
                "status": 0,
                "latency_ms": 0,
                "body": None,
                "error": str(e),
            }
        )

    # ── 9. Web UI ─────────────────────────────────────────────────
    print("Testing / (web UI)...")
    t0 = time.time()
    try:
        req = Request(f"{base}/")
        with urlopen(req) as resp:
            latency = (time.time() - t0) * 1000
            results.append(
                {
                    "endpoint": "GET /",
                    "status": resp.status,
                    "latency_ms": round(latency, 1),
                    "body": {"content_type": resp.headers.get("content-type")},
                    "error": None,
                }
            )
            print(f"  {resp.status}  {latency:.1f}ms")
    except Exception as e:
        results.append(
            {
                "endpoint": "GET /",
                "status": 0,
                "latency_ms": 0,
                "body": None,
                "error": str(e),
            }
        )

    # ── Summary ───────────────────────────────────────────────────
    passed = sum(1 for r in results if r["status"] in (200, 405))
    failed = len(results) - passed
    latencies = [r["latency_ms"] for r in results if r["latency_ms"] > 0]

    report = {
        "server": base_url,
        "server_info": server_info,
        "job_id": job_id,
        "total_tests": len(results),
        "passed": passed,
        "failed": failed,
        "latency_summary": {
            "avg_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
            "min_ms": round(min(latencies), 1) if latencies else 0,
            "max_ms": round(max(latencies), 1) if latencies else 0,
        },
        "results": [
            {
                "endpoint": r["endpoint"],
                "status": r["status"],
                "latency_ms": r["latency_ms"],
                "error": r["error"],
            }
            for r in results
        ],
    }

    print()
    print("=" * 60)
    print("  API TEST SUMMARY")
    print("=" * 60)
    print(f"  Passed: {passed}/{len(results)}")
    print(f"  Failed: {failed}/{len(results)}")
    ls = report["latency_summary"]
    print(f"  Latency: avg={ls['avg_ms']}ms, min={ls['min_ms']}ms, max={ls['max_ms']}ms")

    if failed > 0:
        print()
        print("  Failed tests:")
        for r in results:
            if r["status"] not in (200, 405):
                print(f"    {r['endpoint']}: {r['status']} — {r['error']}")

    # ── Save ──────────────────────────────────────────────────────
    if save:
        # Save next to the job output if possible
        save_dir = PROJECT_ROOT / "output" / job_id if job_id else PROJECT_ROOT / "output"
        save_dir.mkdir(parents=True, exist_ok=True)
        report_path = save_dir / "api_report.json"
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print()
        print(f"Report saved to: {report_path}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test all API endpoints with latency measurement")
    parser.add_argument(
        "--base",
        default="http://localhost:8000",
        help="API server URL (default: http://localhost:8000)",
    )
    parser.add_argument("--job", default=None, help="Job ID to test (default: auto-detect first)")
    parser.add_argument("--save", action="store_true", help="Save report as api_report.json")
    args = parser.parse_args()
    run_tests(args.base, args.job, args.save)
