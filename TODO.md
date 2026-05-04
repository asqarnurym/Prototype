# TODO

## Completed on 2026-04-18

- IEEE style cleanup applied to the manuscript source:
  - removed `\IEEEPARstart`
  - removed `\IEEEoverridecommandlockouts`
  - removed the extra `\\` from `\title`
- Chart provenance unified:
  - `evaluation/paper_charts_run.txt` now points to `run_001`
  - `evaluation/run_001/per_video_metrics.csv` and `evaluation/run_002/per_video_metrics.csv` were confirmed identical
- Current metric charts were confirmed fresh:
  - `figures/fig_rtf_comparison.png`
  - `figures/fig_coverage.png`
- Explicit repo-path leakage was re-scanned in the manuscript source and no reader-visible internal project paths were found
- `academic_paper/Paper-output` was identified as an old LaTeX/Overleaf-style compile-output folder, not the source of truth for the article

## Completed on 2026-04-30

- Manuscript pre-submission toolchain added:
  - `scripts/paper_sanity_check.py`
  - `scripts/build_paper.ps1`
  - `scripts/pre_submission_check.ps1`
- Pre-submission tooling documented in:
  - `README.md`
  - `USAGE.md`
  - `TESTING.md`
  - `Prototype.md`
  - `PrototypeVision.md`
- Current paper build was validated from canonical sources:
  - `academic_paper/main_full.tex`
  - `academic_paper/paper_ieee_full.tex`
  - output confirms 6 pages
- Python environment reproducibility restored:
  - `.venv` works
  - `scripts/verify_environment.py --profile runtime` passes
- Lint issue fixed:
  - `tests/unit/test_generate_charts_script.py`
  - `ruff check .` is green
- Backups created:
  - article snapshot zip in `backups/`
  - repo bundle backup in `backups/`
- Git hygiene improved for publication workflow:
  - `backups/` ignored
  - local LaTeX build artifacts in `academic_paper/` ignored
- Runtime model baseline confirmed:
  - `description_model = gemini-2.5-flash`
  - no active `gemini-*-preview` override in `.env`
- Paper methodology extension added:
  - `scripts/analyze_scene_selection_ablation.py`
  - `scripts/extract_scene_case_notes.py`
  - generated artifacts in `evaluation/paper_extensions/`
  - generated data in `evaluation/paper_extensions/`
- Manuscript variants were consolidated:
  - current source: `academic_paper/main_full.tex`
  - earlier short version removed after the full version fit the 6-page layout
- On-demand TTS is included only as a separate exploratory interaction-level
  micro-benchmark, not as part of B0/B1 corpus throughput.

## Active — Critical

1. Perform a manual anti-AI / human rewrite pass:
   - abstract
   - introduction
   - contributions
   - discussion
   - conclusion

2. Final bibliography/content claim audit:
   - ensure every retained claim is supported by:
     - local verified metrics, or
     - cited literature
   - keep wording publication-facing (no internal engineering jargon in reader-facing text)

## Active — Important / Desirable

3. Replace ad-hoc upload persistence with a real database-backed implementation:
    - start with SQLite + SQLAlchemy
    - persist upload jobs, file metadata, statuses, and artifact references
    - keep the current filesystem layout only as blob/artifact storage, not the source of truth

4. Benchmark Gemini model variants on Vertex AI:
    - keep `gemini-2.5-flash` as the baseline default for summary and scene-description generation
    - compare future preview or newer Gemini models against `gemini-2.5-flash` on cost, runtime, and output quality
    - capture regression thresholds for summary/scene-description latency and artifact usefulness before changing the default again

## Candidate Ideas — Needs Triage

- Add a latency breakdown for on-demand audio description:
  - nearest-scene lookup time
  - cache hit/miss status
  - TTS generation time
  - total request time
- Add a focused benchmark script for on-demand AD:
  - cold cache vs warm cache
  - Google TTS vs edge fallback
  - median and worst-case request latency
- Define a simple quality rubric for scene descriptions and summaries:
  - usefulness
  - specificity
  - absence of fallback text
  - suitability for spoken playback
- Persist model/runtime metadata inside evaluation runs:
  - model name
  - region
  - auth mode
  - SDK/provider snapshot
- Add a regression guard that fails when summary or scene outputs fall back to placeholder artifacts.
- For the future upload database, design the initial schema for:
  - `jobs`
  - `uploads`
  - `artifacts`
  - `tts_cache_entries`

## Recommended Execution Order

1. Do the manual human-voice rewrite pass
2. Run `scripts/pre_submission_check.ps1`
3. Perform final bibliography/content claim audit
4. Then continue non-paper backlog items (DB persistence, model benchmarks)

## Key Files

- Current article: `academic_paper/paper_ieee_full.tex`
- Entrypoint: `academic_paper/main_full.tex`
