# Analysis Notes for the Conference Paper

Topic: *Design of a multimodal pipeline for accessibility in e-learning content*

Status date: 2026-04-30

This file replaces earlier notes written for an older short draft. The current
paper is no longer a 4-page outline: it is a prototype-stage systems paper with
a 24-video EN/RU corpus, B0/B1 baseline comparison, formal metrics, charts,
post-hoc scene-selection ablation, and explicit threats to validity.

## Current Manuscript Variants

- Current full manuscript version:
  - `academic_paper/main_full.tex`
  - `academic_paper/paper_ieee_full.tex`
  - `academic_paper/main_full.pdf`
- Generated extension data:
  - `evaluation/paper_extensions/`

The full version is the current manuscript source after consolidation. The
compiled PDF remains within a 6-page layout while preserving the additional
methodology material needed for supervisor review.

## Reference Coverage

The selected references currently support five parts of the paper:

- Captions and accessibility benefit:
  - Gernsbacher 2015
  - Malakul and Park 2023
  - Mirzaei et al. 2018
- Instructional video and cognitive-load rationale:
  - Mayer et al. 2020
  - Castro-Alonso et al. 2021
  - Lange and Costley 2020
  - Kruger and Doherty 2016
- Neurodiversity and lecture-capture access:
  - Le Cunff et al. 2024
  - Horlin et al. 2024
- ASR and timestamping foundations:
  - Malik et al. 2020
  - Radford et al. 2022
  - Bain et al. 2023
  - Wagner et al. 2024
- Hosted multimodal model used in the prototype:
  - Gemini Team, Google 2025
- Implementation and accessibility baseline:
  - PySceneDetect
  - W3C WCAG 2.1

This reference set is sufficient for the current conference-paper framing:
architecture plus technical evaluation. Deeper UI/accessibility standards
references, such as W3C Media Accessibility User Requirements or WAI-ARIA, can
be added later for the dissertation or a UI-focused paper.

## Current Evidence and Claims

The paper now supports these claims with local evidence:

- B0/B1 technical comparison on a fixed 24-video corpus.
- Mean ASR confidence and low-confidence ratio.
- B0 and B1 real-time factor (RTF).
- Content-type coverage within 15 seconds of indexed scenes.
- Stage-level latency breakdown using B0/B1-derived timing.
- TTS latency as a separate exploratory interaction-level micro-benchmark.
- Post-hoc scene-selection ablation against static scene caps.

The paper does not claim:

- user-level accessibility validation;
- learning gains;
- clinical or medical validation;
- semantic quality superiority of generated audio descriptions;
- full reproducibility across hosted API model drift.

These limits are intentional and should remain explicit.

## Algorithm Description Checkpoints

The paper algorithm should match the implementation at a systems level:

- Offline processing:
  - ASR and scene detection run as parallel branches.
  - Scene descriptions are generated after detection and interval filtering.
  - Summary/chapter artifacts are generated from saved scene descriptions.
- Adaptive scene indexing:
  - PySceneDetect ContentDetector is the primary scene detector.
  - If the detector returns fewer than three scenes, uniform anchors are added
    every 30 seconds before interval filtering and description generation.
  - The paper should describe this as a coverage-oriented fallback, not as a
    guarantee of semantic description quality.
- On-demand audio description:
  - The player sends the current playback time and requested language.
  - The API selects the nearest indexed scene within a 30-second tolerance.
  - TTS cache entries are scoped by job, scene, and language.
  - The player pauses video during description audio and resumes if playback was
    active before the request.

## What Is Already Resolved

- Architecture figure is present.
- Baseline B0/B1 comparison is present.
- Formal metric definitions are present.
- Corpus size and balance are described.
- Scene coverage chart is present with bootstrap 95% confidence intervals.
- TTS is no longer mixed into B0/B1 corpus throughput.
- Post-hoc scene-selection ablation is present.
- Threats to validity now state prototype-stage limits.
- Manuscript leakage is guarded by `scripts/paper_sanity_check.py`.
- PDF build/page count is guarded by `scripts/build_paper.ps1`.

## Remaining Near-Term Work

Before sending to the supervisor:

1. Do a manual English style pass on the current PDF.
2. Check that the abstract and conclusion sound human and modest.
3. Verify that no venue-specific template requirements are missing.
4. Keep GitHub/artifact links out of the main text unless a clean public release
   or DOI is prepared.
5. Keep the expanded 8-page version as backup material, not the default
   submission target.

For dissertation-stage work:

1. Add deeper UI/accessibility standards discussion.
2. Add a real UI/accessibility evaluation or expert review if feasible.
3. Add a more formal scene-description quality rubric.
4. Persist model/runtime metadata in evaluation runs.
5. Consider a public artifact release once the repository is cleaned.
