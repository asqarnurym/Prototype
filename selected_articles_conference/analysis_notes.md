# Analysis of Selected References

Topic: *Design of a multimodal pipeline for accessibility in e-learning content*

## 1) How the selected set is balanced

- **Accessibility impact of captions and controls**
  - R01 (Gernsbacher 2015): broad evidence that captions improve comprehension/attention/memory.
  - R02 (Malakul & Park 2023): auto-subtitles are viable in educational use (comprehension, load, satisfaction).
  - R03 (Mirzaei et al. 2018): timing and ASR-error-aware captioning matter, not only transcript content.

- **Instructional design and cognitive load rationale**
  - R04 (Mayer et al. 2020): practical principles for effective instructional video.
  - R05 (Castro-Alonso et al. 2021): CLT/CTML strategies (segmenting, signaling, split-attention reduction).
  - R06 (Lange & Costley 2020): real online-video media delivery issues (pace/intelligibility/congruence).
  - R07 (Kruger & Doherty 2016): multimodal methodology for cognitive load around educational video.
  - R08 (Le Cunff et al. 2024), R09 (Horlin et al. 2024): neurodiversity and practical need for controls (pause/speed/recordings).

- **ASR and timestamping technical foundation**
  - R10 (Malik et al. 2020): ASR methods landscape and deployment context.
  - R11 (Radford et al. 2022): robust ASR foundation (Whisper-scale weak supervision).
  - R12 (Bain et al. 2023), R13 (Wagner et al. 2024): adjacent timestamp precision approaches (WhisperX/CrisperWhisper), useful for future improvements and scope separation.

## 2) What this set supports in your paper

- **Problem motivation:** R01/R02/R06/R08/R09
- **Design principles for UI + pipeline outputs:** R04/R05/R07
- **Why ASR + word-level timing is central:** R03/R10/R11
- **Future timestamp improvements without claiming same scope:** R12/R13

## 3) Gaps still missing in the current 4-page draft

1. **Architecture figure is missing**
   - Add one compact block diagram (Input -> ASR -> Scene Index -> Summary/Chapters -> On-demand AD/TTS -> Player).

2. **No baseline comparison table**
   - Add one small table: your system vs "ASR-only captions" baseline on at least 3 measurable axes (scene coverage, AD availability, interaction latency/cached response).

3. **Metrics definitions are not formalized**
   - Add short formulas/definitions for coverage proxy, low-confidence ratio, and RTF to improve scientific rigor.

4. **Evaluation section needs clearer stage-level runtime split**
   - Include per-stage latency (ASR / scene extraction / multimodal descriptions / TTS cold/cached) to justify bottleneck claims.

5. **Threats to validity are too brief**
   - Add explicit external validity limits: two-video corpus, language/domain bias, API-rate-limit dependency.

6. **No explicit reproducibility checklist**
   - Add mini checklist: hardware, software versions, key params (scene threshold, scene cap, model settings).

## 4) Priority additions to reach strong 5.5-6 pages

- Add Figure 1 (architecture) + Figure 2 (UI with ARIA + word-by-word subtitles).
- Add one compact baseline-comparison table.
- Add 5-8 lines with metric definitions and failure cases.
- Add 1 paragraph "Practical deployment implications" (cost/latency trade-offs).
