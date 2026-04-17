# Metric Status Table — thesis-prototype-article-audit

| Manuscript area | Claim / metric | Status | Evidence | Action |
|---|---|---|---|---|
| `paper_ieee.tex:36,353` | 24 videos (12 EN, 12 RU) | VERIFIED | `evaluation/run_001/evaluation_report.json`, `evaluation/corpus_manifest.csv` | kept |
| `paper_ieee.tex:36,232-247,353` | ASR confidence mean 0.942 | VERIFIED | `evaluation/run_001/evaluation_report.json`, `evaluation/run_001/aggregate_metrics.csv` | kept |
| `paper_ieee.tex:36,232-247,353` | B0 mean RTF 0.193 | VERIFIED | `evaluation/run_001/evaluation_report.json`, `evaluation/run_001/aggregate_metrics.csv` | kept |
| `paper_ieee.tex:36,232-247,353` | B1 mean/median RTF 0.433 / 0.424 | VERIFIED | `evaluation/run_001/evaluation_report.json`, `evaluation/run_001/aggregate_metrics.csv` | kept |
| `paper_ieee.tex:36,290,343,353` | All 24 videos processed faster than realtime | VERIFIED | `evaluation/run_001/evaluation_report.json` (`videos_b1_rtf_ge_1 = 0`) | kept |
| `paper_ieee.tex:36,247,300,353` | Mean 15 s coverage 91.7% | VERIFIED | `evaluation/run_001/evaluation_report.json`, `evaluation/run_001/aggregate_metrics.csv` | kept |
| `paper_ieee.tex:232` | Low-confidence ratio mean 0.026 | VERIFIED | `evaluation/run_001/per_video_metrics.csv`, `tests/evaluation/run_corpus_eval.py:246-278` | kept |
| `paper_ieee.tex:89` | Zero temporal overlaps across adjacent words | VERIFIED | `evaluation/run_001/per_video_metrics.csv` (`overlap_ratio = 0.0` for all rows), `tests/evaluation/run_corpus_eval.py:250-273` | kept |
| `paper_ieee.tex:93,102` | On-demand AD tolerance window = 30 seconds | VERIFIED | `pipeline/visual/scene_indexer.py:117-132`, `api/server.py:671-678` | kept |
| `paper_ieee.tex:132,224` | Fallback sampling interval = every 30 seconds | VERIFIED | `pipeline/visual/scene_detect.py:79-105` | kept |
| `paper_ieee.tex:132` | Minimum fallback density ≈ two descriptions per minute | VERIFIED | `pipeline/visual/scene_detect.py:96-105` (30-second interval implies two samples/minute) | kept |
| `paper_ieee.tex:255-285` | Stage latency and duration-bucket ratios | VERIFIED | recomputed from `evaluation/run_001/per_video_metrics.csv`; aggregate ratios from `evaluation/run_001/baseline_comparison.csv` | kept |
| `paper_ieee.tex:300-321,343` | Content-type coverage and mean scene counts | VERIFIED | `evaluation/run_001/per_video_metrics.csv` | kept |
| Previous `paper_ieee.tex:300` wording | “initial pass returned zero scenes (0% coverage)” | UNVERIFIED | no retained local artifact for the pre-fallback pass | removed/reframed |
| `paper_ieee.tex:331` | TTS cold/cached median latency | VERIFIED (fresh archived run) | `.omx/reports/benchmark-tts-latency-2026-04-17.txt` | updated to fresh values |
