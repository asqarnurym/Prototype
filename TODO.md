# TODO

## Completed on 2026-04-18

- IEEE style cleanup applied to `academic_paper/paper_ieee.tex`:
  - removed `\IEEEPARstart`
  - removed `\IEEEoverridecommandlockouts`
  - removed the extra `\\` from `\title`
- Chart provenance unified:
  - `evaluation/paper_charts_run.txt` now points to `run_001`
  - `evaluation/run_001/per_video_metrics.csv` and `evaluation/run_002/per_video_metrics.csv` were confirmed identical
- Current metric charts were confirmed fresh:
  - `figures/fig_rtf_comparison.png`
  - `figures/fig_coverage.png`
- Explicit repo-path leakage was re-scanned in `academic_paper/paper_ieee.tex` and no reader-visible internal project paths were found
- `academic_paper/Paper-output` was identified as an old LaTeX/Overleaf-style compile-output folder, not the source of truth for the article

## Active — Critical

1. Compile the current paper PDF from:
   - `academic_paper/main.tex`
   - canonical article body: `academic_paper/paper_ieee.tex`
   Goal: verify the current manuscript builds, not the stale `academic_paper/Paper-output` build.

2. Validate the 6-page limit after the latest edits:
   - tables/figures still fit
   - references did not shift badly
   - no harmful underfull/overfull layout issues

3. Verify bibliography/citations:
   - every `\cite{...}` resolves
   - no retained claim lacks support from either:
     - local verified metrics, or
     - literature

4. Perform a manual anti-AI / human rewrite pass:
   - abstract
   - introduction
   - contributions
   - discussion
   - conclusion

## Active — Important / Desirable

5. Decide what to do with `academic_paper/Paper-output`:
   - delete it, or
   - rename/archive it as an old compile artifact (for example `Paper-output-old-overleaf-build`)

6. Repair the Python environment for reproducibility:
   - current `.venv` is broken and points to a missing Python path

7. Fix the remaining lint issue:
   - `tests/unit/test_generate_charts_script.py`
   - current `ruff check .` is not green

8. Create a separate manual backup of the near-final article:
    - for example a zip or a copy of `academic_paper/`
    - keep this even though git exists

9. Replace ad-hoc upload persistence with a real database-backed implementation:
    - start with SQLite + SQLAlchemy
    - persist upload jobs, file metadata, statuses, and artifact references
    - keep the current filesystem layout only as blob/artifact storage, not the source of truth

10. Decide whether to add an audio-description latency subsection for the paper:
    - compare on-demand audio-description latency against a pre-generated TTS baseline and against no-TTS preprocessing
    - only keep it if it materially strengthens the paper without breaking the page budget
    - separate server-side generation latency from end-to-end client-observed latency
    - if client-side latency cannot be measured robustly, report a conservative worst-case observed value with explicit methodology

11. Benchmark Gemini model variants on Vertex AI:
    - compare `gemini-3-flash-preview` vs `gemini-2.5-flash` on cost, runtime, and output quality
    - capture regression thresholds for summary/scene-description latency and artifact usefulness
    - revert the default model to `gemini-2.5-flash` if the newer model is slower, materially more expensive, or degrades output quality

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

1. Build the current PDF
2. Check 6 pages + citation resolution
3. Do the manual human-voice rewrite pass
4. Decide the fate of `Paper-output`
5. Then fix environment/lint issues

## Key Files

- Current article: `academic_paper/paper_ieee.tex`
- Entrypoint: `academic_paper/main.tex`
