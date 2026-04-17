# Test Spec — thesis-prototype-article-audit

## Metadata
- Paired PRD: `.omx/plans/prd-thesis-prototype-article-audit.md`
- Source spec: `.omx/specs/deep-interview-thesis-prototype-article-audit.md`
- Date: `2026-04-17`

## Test Objectives
Verify that article-audit and repair work remains evidence-backed, reversible, and complete enough for manual finalization.

## Evidence Under Test
- Manuscript: `academic_paper/main.tex`, `academic_paper/paper_ieee.tex`
- Bibliography: `academic_paper/references.bib`
- Evaluation artifacts: `evaluation/run_001/aggregate_metrics.csv`, `evaluation/run_001/baseline_comparison.csv`, `evaluation/run_001/evaluation_report.json`
- Runtime evidence: `logs/prototype.log`, `output/*/tts_cache/*.mp3`
- TTS benchmark harness: `tests/evaluation/benchmark_tts_latency.py`

## Acceptance Test Matrix
| ID | Requirement | Verification method | Pass condition |
|---|---|---|---|
| TS-01 | Canonical article is identified correctly | Inspect `academic_paper/main.tex:1` | `main.tex` includes `paper_ieee.tex` and all plan outputs treat it as canonical entrypoint |
| TS-02 | Every retained numeric claim is traceable | Build a metric traceability table from manuscript to local artifacts | No retained metric row lacks a source, script, or explicit weaken/remove disposition |
| TS-03 | Run_001 aggregate claims match manuscript where intended | Compare manuscript metrics against `evaluation/run_001/evaluation_report.json:20-50` and CSV summaries | Any mismatch is either fixed in manuscript or documented as stale |
| TS-04 | TTS latency claims are scoped honestly | Compare `academic_paper/paper_ieee.tex:330-331`, `tests/evaluation/benchmark_tts_latency.py:45-85`, and `logs/prototype.log:873-881` | Benchmark and runtime/cache evidence are not conflated |
| TS-05 | Accessibility-effect claims are literature-backed | Build a claim matrix against `academic_paper/references.bib` and selected literature | Every strong user-impact claim has citation support or is weakened/removed |
| TS-06 | Repo-internal noise is removed | Search manuscript for implementation-only paths/function names | No irrelevant repo paths/internal identifiers remain in reader-facing prose |
| TS-07 | Reversibility is preserved | Confirm git/snapshot baseline and change log exist before edits | All `.tex` / `.bib` edits can be traced and rolled back |
| TS-08 | Final package is complete | Inspect final deliverables bundle | Audit report, metric/claim tables, prompts, and manual checklist all exist |

## Verification Procedure
### 1. Metric Traceability Pass
- Enumerate all quantitative claims from:
  - `academic_paper/paper_ieee.tex:35-37`
  - `academic_paper/paper_ieee.tex:232-331`
  - `academic_paper/paper_ieee.tex:343-353`
- For each metric, capture:
  - manuscript location,
  - source artifact,
  - source value,
  - verification status,
  - remediation action if stale/unverified.

### 2. Claim Classification Pass
- Extract all strong claims from introduction, methodology, results, and conclusion.
- Classify each as:
  - `PROJECT-VERIFIED`
  - `LITERATURE-BACKED`
  - `WEAKEN/REMOVE`
- Reject completion if any strong claim remains unclassified.

### 3. Citation Hygiene Pass
- Confirm that named methods/tools with claim-bearing roles are either cited or described conservatively.
- Reject completion if the manuscript retains unsupported method/tool claims that imply validation.

### 4. Structural Hygiene Pass
- Search for:
  - repo file paths,
  - internal function names,
  - implementation details that do not improve reproducibility.
- Reject completion if such details remain outside clearly justified methodological description.

### 5. Delivery Bundle Pass
- Confirm presence of:
  - audit report,
  - metric table,
  - claim table,
  - citation gap list,
  - technical master prompt,
  - article master prompt,
  - manual finalization checklist.

## Suggested Commands
```powershell
Select-String -Path academic_paper\paper_ieee.tex -Pattern 'RTF|coverage|confidence|TTS|Google|Edge|Whisper|scene'
Get-Content evaluation\run_001\evaluation_report.json
Get-Content evaluation\run_001\aggregate_metrics.csv
Select-String -Path logs\prototype.log -Pattern 'Generating on-demand TTS|Google TTS|Reused cached TTS'
Get-ChildItem output -Recurse -Filter *.mp3 | Where-Object { $_.FullName -match 'tts_cache' }
```

## Exit Criteria
- All acceptance tests TS-01 through TS-08 pass.
- No known unsupported strong claim remains in the retained manuscript.
- All planning artifacts under `.omx/plans/` are present and consistent with the deep-interview spec.

## Failure Conditions
- Numeric claims cannot be mapped to evidence.
- Benchmark numbers and runtime-behavior claims are mixed without explicit scope.
- Accessibility benefits are stated as project-proven without literature support.
- Final package omits prompts or manual-finalization instructions.

## Notes
- This test spec intentionally favors falsification: unsupported claims must fail the gate and be weakened or removed, not reworded into pseudo-support.
