# Claim Status Table — thesis-prototype-article-audit

| Claim family | Status | Basis | Disposition |
|---|---|---|---|
| Captions / playback control / navigational structure are relevant accessibility supports in video learning | LITERATURE-BACKED | `Gernsbacher2015`, `Mayer2020`, `Horlin2024`, `WCAG21` already cited in manuscript | kept |
| Unified pipeline emits subtitles, scene descriptions, summaries, and chapters | PROJECT-VERIFIED | manuscript structure + local pipeline artifacts / outputs | kept |
| Adaptive scene-density maintains useful coverage in the evaluated corpus | PROJECT-VERIFIED | `evaluation/run_001/*` | kept with corpus scope |
| On-demand AD cache reduces repeated local playback latency after first request | PROJECT-VERIFIED | archived TTS benchmark + `logs/prototype.log:873-881` | kept with local-cache scope |
| Midpoint word grouping reduces boundary-drop cases | WEAKEN/REMOVE | `tests/unit/test_word_grouper.py`, `pipeline/word_grouper.py` provide implementation support but not a standalone corpus-level reduction metric | manuscript narrowed to the zero-overlap proxy and removed the stronger reduction claim |
| Corpus evaluation recorded zero temporal overlaps across adjacent words | PROJECT-VERIFIED | `evaluation/run_001/per_video_metrics.csv`, `tests/evaluation/run_corpus_eval.py:250-273` | kept |
| On-demand AD resolves the nearest indexed scene within a 30-second tolerance window | PROJECT-VERIFIED | `pipeline/visual/scene_indexer.py:117-132`, `api/server.py:671-678` | kept |
| Low-variance fallback sampling injects anchors every 30 seconds (≈ two descriptions per minute) | PROJECT-VERIFIED | `pipeline/visual/scene_detect.py:79-105` | kept |
| Qualitative spot checks are illustrative rather than outcome-proving | PROJECT-VERIFIED | revised manuscript wording at `academic_paper/paper_ieee.tex:220-227` | kept |
| Human accessibility benefits are proven by this prototype | WEAKEN/REMOVE | no user study / no human ratings | removed as a project-proven claim; only literature-backed motivation is retained |
| Qualitative slide/screencast examples prove user outcomes or semantic correctness | WEAKEN/REMOVE | spot checks only | weakened to illustrative observations |
| Prototype is deployable in general production settings | WEAKEN/REMOVE | only local workstation/corpus evidence | weakened to “prototype-stage feasibility on the tested hardware” |
