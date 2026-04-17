# Master Prompt — Technical Fix

Use this prompt if you want a follow-up agent to tighten the technical evidence chain without changing the scientific claims beyond what the audit already allows.

```text
Task: strengthen the reproducibility and evidence trail for the thesis prototype article without inventing any data.

Rules:
- Do not fabricate metrics.
- Prefer archived artifacts and reproducible scripts over prose assertions.
- Keep changes reversible and documented.
- If a metric cannot be reproduced, mark it stale or remove it from claim-bearing prose.

Work items:
1. Inspect `evaluation/run_001/*`, `tests/evaluation/run_corpus_eval.py`, and `tests/evaluation/benchmark_tts_latency.py`.
2. Produce or refresh machine-readable/Markdown traceability tables for every manuscript metric.
3. Archive any fresh benchmark transcript used for the paper under `.omx/reports/`.
4. If code comments or docs contradict the manuscript, either align them or document the mismatch.
5. Do not widen scope to new experiments unless they are directly needed to verify an existing manuscript claim.

Deliver:
- a metric traceability table,
- a short stale/unverified list,
- and a compact changelog of any evidence artifacts you refreshed.
```
