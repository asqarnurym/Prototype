# Context Snapshot

- Task statement: Structure the user's broad repository/article review request into a sequential, logically connected prompt and run a deep-interview to expose weak points before planning.
- Desired outcome: an execution-ready brief for auditing the prototype, article assets, metrics, references, and evidence quality for a master's conference paper.
- Stated solution: inspect repository and nearby article/research assets, then ask focused questions.
- Probable intent hypothesis: reduce the risk of submitting an academically weak or factually unsupported paper, especially around metrics validity, citation completeness, TTS behavior, and human-authored final writing.

## Known facts / evidence
- Repository is brownfield and contains `academic_paper/`, `evaluation/`, `selected_articles_conference/`, `template/`, code, tests, logs, and cached outputs.
- Current paper source appears to be `academic_paper/main.tex` -> `paper_ieee.tex`.
- `paper_ieee.tex` already contains sections for methodology, technical evaluation, results, discussion, threats to validity, and TTS latency.
- `academic_paper/references.bib` currently has a small set of entries (13 article refs + PySceneDetect + WCAG21), while `selected_articles_conference/` and `Desktop/Thesis/Conference Articles/` each contain 13 PDFs and `Desktop/Thesis/Article base/` contains 50+ PDFs.
- Desktop contains `Overleaf backup.zip`, which may be the older article snapshot mentioned by the user.
- Evaluation artifacts exist under `evaluation/run_001`, `run_002`, `run_003`; run_001 overall metrics include mean B0 RTF 0.193, mean B1 RTF 0.433, ASR confidence 0.942, coverage 91.696.
- `paper_ieee.tex` reports matching aggregate values for 24 videos and states TTS micro-benchmark medians of 765.3 ms cold and 0.05 ms cached.
- `.env` contains `GOOGLE_APPLICATION_CREDENTIALS=...json`; code in `pipeline/visual/tts.py` prefers Google TTS when credentials exist, otherwise falls back to edge-tts.
- Recent logs on 2026-04-15 show both `Generating on-demand TTS` and `Google TTS`, and output folders contain `tts_cache/*.mp3` files updated on 2026-04-15.
- Some output folders have scene index / summary files updated on 2026-04-15, while many evaluation outputs are from 2026-03-31, so article metrics may reflect an earlier corpus run than the latest interactive checks.

## Constraints
- User says the final article text must be finalized manually by them because plagiarism/AI detectors previously flagged it as highly AI-generated.
- No direct implementation should happen in deep-interview mode.
- Need an academically honest and evidence-backed brief; cannot assume metrics or citations are valid without verification.

## Unknowns / open questions
- Primary outcome priority: prompt for later work, audit checklist, article rescue plan, or all of them.
- Which article version is the authoritative baseline: repo `paper_ieee.tex`, Desktop `Overleaf backup.zip`, or another archive.
- Whether the goal is to repair the current conference paper only, or also align it with the broader master's thesis research base.
- Which metrics are acceptable as scientifically meaningful for the target conference and advisor.
- Whether current paper tables/claims must be restricted to reproducible offline corpus metrics, excluding interactive TTS observations.
- Whether selected references must include tool papers for Whisper, WhisperX, CrisperWhisper, PySceneDetect, Google TTS, WCAG, etc.
- What level of repo/article modification authority OMX may take later versus what must remain manual.

## Decision-boundary unknowns
- Can OMX later modify LaTeX and bibliography, or should it only prepare findings/prompts/checklists?
- Can OMX run fresh evaluation/benchmark passes later, or should this stay analysis-only?
- Should older article assets outside the repo be treated as authoritative sources or merely fallback references?

## Likely touchpoints
- `academic_paper/paper_ieee.tex`
- `academic_paper/references.bib`
- `selected_articles_conference/`
- `evaluation/run_*/`
- `tests/evaluation/benchmark_tts_latency.py`
- `logs/prototype.log`
- `output/*/tts_cache/`
- `Desktop/Thesis/*`
- `Desktop/Overleaf backup.zip`
