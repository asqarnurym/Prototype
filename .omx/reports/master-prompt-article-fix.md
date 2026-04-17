# Master Prompt — Article Fix

Use this prompt for future manuscript editing passes.

```text
Task: revise `academic_paper/paper_ieee.tex` into a cautious, scientifically honest conference-paper draft grounded in local evidence.

Hard rules:
- Keep only claims that are project-verified, literature-backed, or explicitly scoped as illustrative.
- Do not invent results, user outcomes, or semantic-quality judgments.
- Remove repo-internal implementation noise unless it is necessary for reproducibility.
- Preserve the paper as a standalone research artifact rather than repository documentation.
- Respect the existing page-budget pressure; avoid bibliography expansion unless essential.

Use these anchors:
- `.omx/reports/article-audit-report.md`
- `.omx/reports/metric-status-table.md`
- `.omx/reports/claim-status-table.md`
- `.omx/reports/citation-gap-list.md`
- `.omx/reports/benchmark-tts-latency-2026-04-17.txt`

Editing priorities:
1. Keep corpus-level numeric results that are already verified.
2. Scope performance interpretations to the evaluated corpus / tested hardware.
3. Convert any user-benefit or deployability overclaim into limitation-aware phrasing.
4. Keep qualitative examples illustrative only.
5. If a new claim needs a new citation, either add the citation carefully or weaken the claim.

Output:
- revised manuscript text,
- concise edit log,
- remaining risk list.
```
