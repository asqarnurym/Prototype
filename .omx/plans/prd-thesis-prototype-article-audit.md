# PRD — thesis-prototype-article-audit

## Metadata
- Task slug: `thesis-prototype-article-audit`
- Source spec: `.omx/specs/deep-interview-thesis-prototype-article-audit.md`
- Source context: `.omx/context/thesis-prototype-article-audit-20260415T112024Z.md`
- Source transcript: `.omx/interviews/thesis-prototype-article-audit-20260415T114757Z.md`
- Planning mode: `ralplan`
- Date: `2026-04-17`

## Requirements Summary
Prepare an academically honest, reversible, evidence-backed repair workflow for the conference article tied to the master's prototype. The work must:

1. audit metrics, claims, citations, and artifact freshness;
2. produce master prompts/checklists for technical and article repair;
3. enable a cautious article-fix pass that removes unsupported claims instead of embellishing them;
4. leave the user with a complete manual finalization package.

The current canonical paper entrypoint is `academic_paper/main.tex:1`, which includes `academic_paper/paper_ieee.tex`.

## Evidence Anchors
- Canonical article entrypoint: `academic_paper/main.tex:1`
- Core paper claims and abstract metrics: `academic_paper/paper_ieee.tex:35-37`
- Contributions and non-user-study positioning: `academic_paper/paper_ieee.tex:51-57`
- Artifact/pipeline framing: `academic_paper/paper_ieee.tex:72-79`
- On-demand AD algorithm and Google/Edge branching: `academic_paper/paper_ieee.tex:95-120`
- Evaluation protocol and machine-readable artifact claim: `academic_paper/paper_ieee.tex:138-216`
- Aggregate metric claims in results: `academic_paper/paper_ieee.tex:232-331`
- Threats-to-validity section anchor: `academic_paper/paper_ieee.tex:345-348`
- Current bibliography scope: `academic_paper/references.bib:1-129`
- TTS provider preference/fallback in code: `pipeline/visual/tts.py:22-85`
- Runtime TTS cache behavior in API: `api/server.py:641-723`
- Manual latency micro-benchmark harness: `tests/evaluation/benchmark_tts_latency.py:1-97`
- Current corpus aggregate artifact: `evaluation/run_001/evaluation_report.json:20-50`
- Recent Google TTS / cache evidence: `logs/prototype.log:873-881`
- Repo fallback gap: repository is not yet git-initialized (`git rev-parse --is-inside-work-tree` returned `not-a-git-repo` on 2026-04-17)

## Scope
### In Scope
- Metric traceability from manuscript claims to local evaluation/log/cache artifacts
- Claim classification: `PROJECT-VERIFIED`, `LITERATURE-BACKED`, `WEAKEN/REMOVE`
- Citation completeness for methods/tools/accessibility claims that materially affect the paper
- Removal of repo-internal implementation noise from the manuscript
- Reversible article/bibliography edits after audit findings are grounded
- Final manual-finishing instructions for the user

### Out of Scope
- Fabricating, smoothing over, or overstating results
- Adding a user study
- Turning the paper into repository documentation
- Expanding bibliography far beyond what the 6-page limit can support

## RALPLAN-DR Summary
### Principles
1. Keep only claims that are traceable to verified data or literature.
2. Prefer weakening/removal over speculative justification.
3. Preserve reversibility and provenance for every article edit.
4. Optimize for scientific honesty, not cosmetic impressiveness.
5. Treat the article as a standalone research artifact, not a repo tour.

### Decision Drivers
1. Submission deadline limits how much new experimentation/literature expansion is realistic.
2. The paper already contains concrete numeric claims that must remain traceable.
3. Manual user finalization is mandatory, so automation must prepare a safe draft rather than a final authoritative submission.

### Viable Options
#### Option A — Audit only
- **Pros:** lowest risk of accidental manuscript drift; fast to deliver.
- **Cons:** leaves the user with heavy manual rewrite work; does not close the paper-repair loop.

#### Option B — Audit + reversible repair plan + cautious manuscript fix
- **Pros:** matches the spec deliverables; keeps risk bounded by evidence gates; produces usable near-final materials.
- **Cons:** requires strict discipline to avoid unsupported edits; depends on careful artifact tracing.

#### Option C — Full rewrite around the current paper
- **Pros:** could improve flow quickly.
- **Cons:** highest risk of losing traceability and injecting unsupported framing under deadline pressure.

### Decision
Choose **Option B**. It is the only option that satisfies the requested deliverable chain while preserving evidence gates and reversibility.

## Acceptance Criteria
1. Every numeric manuscript claim has a traceability row pointing to a local artifact, reproducible script, or a deliberate weaken/remove decision.
2. Every strong accessibility or learning-effect claim is mapped either to literature or to a weaken/remove action.
3. A concrete citation gap list exists for tools/methods/claims mentioned in `academic_paper/paper_ieee.tex`.
4. A repair pass removes repo-internal details that do not belong in the paper.
5. A reversible change log exists for all `.tex` / `.bib` edits.
6. The user receives:
   - an audit report,
   - a metric/claim status table,
   - master prompt(s),
   - and a manual finalization checklist.
7. `.omx/plans/prd-thesis-prototype-article-audit.md` and `.omx/plans/test-spec-thesis-prototype-article-audit.md` both exist and are internally consistent.

## Implementation Steps
### Step 1 — Baseline and reversibility
- Confirm canonical article inputs and adjacent assets:
  - `academic_paper/main.tex:1`
  - `academic_paper/paper_ieee.tex`
  - `academic_paper/references.bib`
  - `evaluation/run_001/*`
  - `logs/prototype.log`
  - `output/*/tts_cache/*.mp3`
- Create a rollback baseline before article edits.
- Because the repo is not git-initialized, decide whether to initialize git or create an equivalent snapshot log before editing.

### Step 2 — Metric traceability audit
- Build a table covering every metric in the abstract/results/threats sections:
  - overall RTF/confidence/coverage claims from `academic_paper/paper_ieee.tex:35-37,232-353`
  - TTS latency claim from `academic_paper/paper_ieee.tex:330-331`
  - coverage/fallback claims from `academic_paper/paper_ieee.tex:300-321`
- Map each row to:
  - `evaluation/run_001/evaluation_report.json`
  - `evaluation/run_001/aggregate_metrics.csv`
  - `evaluation/run_001/baseline_comparison.csv`
  - `tests/evaluation/benchmark_tts_latency.py:29-85`
  - `logs/prototype.log:873-881`
- Mark each row `VERIFIED`, `PARTIALLY VERIFIED`, `UNVERIFIED`, or `STALE`.

### Step 3 — Claim and citation audit
- Enumerate strong claims from:
  - abstract/introduction/contributions: `academic_paper/paper_ieee.tex:35-70`
  - methodology/design statements: `academic_paper/paper_ieee.tex:72-137`
  - conclusions: `academic_paper/paper_ieee.tex:343-353`
- Cross-check against `academic_paper/references.bib:1-129` and selected local literature sets.
- Produce a claim matrix with required action:
  - keep as project-verified,
  - keep as literature-backed,
  - weaken/remove.

### Step 4 — Structural article repair plan
- Remove repo-internal noise (paths, function names, implementation-only details) that are not reader-facing research content.
- Keep technical specificity only where it supports reproducibility or methodological clarity.
- Ensure threats/limitations honestly bound what the project does **not** prove.

### Step 5 — Controlled manuscript/bibliography edits
- Apply only evidence-backed edits to `.tex` / `.bib`.
- Strengthen literature framing where needed, but keep the 6-page limit in mind.
- If a metric or claim cannot be defended before deadline, demote it to limitation/future work or remove it.

### Step 6 — Final delivery package
- Deliver:
  - audit findings,
  - metric status table,
  - claim status table,
  - citation gap list,
  - technical-fix master prompt,
  - article-fix master prompt,
  - manual finalization instructions.

## Risks and Mitigations
- **Risk:** Manuscript claims reflect stale evaluation snapshots.  
  **Mitigation:** Treat `evaluation/run_001` as the current anchored corpus source unless newer reproducible artifacts supersede it; label later interactive evidence separately.

- **Risk:** TTS evidence mixes benchmark and live API/cache behavior.  
  **Mitigation:** Keep micro-benchmark claims scoped to `tests/evaluation/benchmark_tts_latency.py` and runtime-behavior claims scoped to logs/cache artifacts.

- **Risk:** Citation expansion blows the page budget.  
  **Mitigation:** Add only citations that directly support current claims or named methods/tools.

- **Risk:** Manual finalization requirement gets lost after automated edits.  
  **Mitigation:** Produce a separate final human checklist and keep edits clearly documented as draftable/reversible.

## Verification Steps
1. Confirm all cited local artifacts still exist before any repair pass.
2. Recompute or restate every table/number from machine-readable sources where feasible.
3. Re-scan the manuscript for unsupported absolutes (`demonstrate`, `prove`, `ensure`, etc.) after edits.
4. Verify that repo-path and internal-function leakage is removed unless essential for reproducibility.
5. Verify that the final package includes audit tables, prompts, and manual checklist.

## ADR
### Decision
Audit first, then perform only evidence-gated and reversible article repair.

### Drivers
- The deep-interview spec explicitly forbids fabrication and requires literature-backed accessibility claims.
- The repo already contains enough evidence to ground a strong audit before editing.
- Deadline pressure makes speculative new experiments and wide literature growth a poor tradeoff.

### Alternatives Considered
- **Audit only:** too incomplete for the requested deliverables.
- **Direct rewrite first:** too risky without claim/metric traceability.

### Why Chosen
This path preserves scientific honesty while still producing usable near-final materials for the user.

### Consequences
- Some appealing claims may be weakened or removed.
- The workflow spends time on verification before cosmetic editing.
- Final polish remains a human-controlled step.

### Follow-ups
1. Build the metric/claim traceability tables.
2. Audit bibliography against named claims/tools.
3. Apply cautious manuscript edits.
4. Prepare the final manual-finishing package.

## Available-Agent-Types Roster
- `planner` — sequencing and scope control
- `architect` — methodology/structure review
- `critic` — plan/claim-quality gate
- `executor` — cautious `.tex` / `.bib` edits
- `verifier` — traceability and completion checks
- `writer` — final instructions / prompt packaging

## Follow-up Staffing Guidance
### Ralph path
- `executor` (high): article/bib edits
- `verifier` (high): traceability and regression checks
- `writer` (high): final checklist and prompts

### Team path
- Lane 1: `architect` or `executor` for manuscript structure and claims
- Lane 2: `verifier` for metrics/logs/evaluation traceability
- Lane 3: `writer` for final package and user checklist

## Launch Hints
```text
$ralph .omx/plans/prd-thesis-prototype-article-audit.md
$team .omx/plans/prd-thesis-prototype-article-audit.md
```

## Team Verification Path
1. Verifier confirms every retained numeric claim has an artifact anchor.
2. Verifier confirms every strong accessibility claim is literature-backed or weakened.
3. Writer confirms the final package includes prompts + manual checklist.
4. Ralph/team only stop after manuscript diffs and audit tables agree.

## Plan Changelog
- 2026-04-17: created missing PRD from completed deep-interview spec and observed repo evidence.
