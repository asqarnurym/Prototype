"""Paper pre-submission sanity checks for LaTeX manuscript sources."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PAPER_DIR = PROJECT_ROOT / "academic_paper"
IGNORE_MARKER = "sanity-ignore"


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: str
    rationale: str


@dataclass(frozen=True)
class Finding:
    rule: str
    rationale: str
    file: str
    line: int
    column: int
    match: str
    text: str


RULES: tuple[Rule, ...] = (
    Rule(
        name="absolute_windows_path",
        pattern=r"\b[A-Za-z]:\\[^\s\]}]+",
        rationale="Absolute Windows path leaked into manuscript text.",
    ),
    Rule(
        name="absolute_unix_path",
        pattern=r"/(?:Users|home|tmp|var|private|mnt)/[^\s\]}]+",
        rationale="Absolute Unix-like path leaked into manuscript text.",
    ),
    Rule(
        name="file_uri",
        pattern=r"file://[^\s\]}]+",
        rationale="file:// URI is usually a local path leak.",
    ),
    Rule(
        name="localhost_url",
        pattern=r"https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|::1)(?::\d+)?(?:/[^\s\]}]*)?",
        rationale="Localhost URL is not reader-reproducible for publication.",
    ),
    Rule(
        name="internal_run_id",
        pattern=r"\brun_\d{3,}\b",
        rationale="Internal run identifier leaked into paper narrative.",
    ),
    Rule(
        name="internal_job_id",
        pattern=r"\bjob_id\b|/jobs/\{?job_id\}?",
        rationale="Internal job identifier or API placeholder leaked into manuscript.",
    ),
    Rule(
        name="internal_artifact_path",
        pattern=r"\b(?:output|temp|logs)/[A-Za-z0-9_.\-/]+",
        rationale="Implementation artifact path leaked into manuscript text.",
    ),
    Rule(
        name="repo_path_leak",
        pattern=r"\b(?:academic_paper|evaluation|pipeline|scripts|core|api|tests)/[A-Za-z0-9_.\-/]+",
        rationale="Repository-internal path leaked into manuscript text.",
    ),
    Rule(
        name="draft_marker",
        pattern=r"\b(?:TODO|TBD|FIXME|XXX|WIP|TK)\b",
        rationale="Draft marker remained in manuscript source.",
    ),
    Rule(
        name="placeholder_citation",
        pattern=r"\[(?:ref|citation needed|todo)\]",
        rationale="Placeholder citation marker is not publication-ready.",
    ),
    Rule(
        name="log_style_reason_tag",
        pattern=r"fallback\s*\[reason=",
        rationale="Log-style fallback annotation leaked into manuscript text.",
    ),
    Rule(
        name="runtime_secret_or_env_key",
        pattern=r"\b(?:GOOGLE_APPLICATION_CREDENTIALS|API_KEY|SECRET_KEY|service_account|token)\b",
        rationale="Runtime credential/env marker leaked into manuscript text.",
    ),
    Rule(
        name="preview_model_name",
        pattern=r"\bgemini-[a-z0-9.\-]*preview\b",
        rationale="Preview model tag appears in manuscript text.",
    ),
    Rule(
        name="raw_http_endpoint_snippet",
        pattern=r"\b(?:GET|POST|PUT|DELETE)\s+/[A-Za-z0-9_/\-{}]+\b",
        rationale="Raw API endpoint snippet is likely implementation leakage.",
    ),
)


def _collect_targets(paper_dir: Path) -> list[Path]:
    if not paper_dir.exists():
        raise FileNotFoundError(f"Paper directory does not exist: {paper_dir}")
    targets = sorted(
        p
        for p in paper_dir.rglob("*.tex")
        if "Paper-output" not in p.parts and p.is_file()
    )
    return targets


def _scan_file(path: Path, compiled_rules: list[tuple[Rule, re.Pattern[str]]]) -> list[Finding]:
    findings: list[Finding] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    rel = str(path.relative_to(PROJECT_ROOT))

    for idx, raw_line in enumerate(lines, start=1):
        if IGNORE_MARKER in raw_line:
            continue
        for rule, regex in compiled_rules:
            for match in regex.finditer(raw_line):
                findings.append(
                    Finding(
                        rule=rule.name,
                        rationale=rule.rationale,
                        file=rel,
                        line=idx,
                        column=match.start() + 1,
                        match=match.group(0),
                        text=raw_line.strip(),
                    )
                )
    return findings


def _print_findings(findings: list[Finding]) -> None:
    print(f"[FAIL] Paper sanity check found {len(findings)} issue(s).")
    for item in findings:
        print(
            f" - {item.file}:{item.line}:{item.column} [{item.rule}] "
            f"{item.match} :: {item.rationale}"
        )


def _write_report(path: Path, findings: list[Finding], targets: list[Path]) -> None:
    payload = {
        "ok": not findings,
        "checked_files": [str(t.relative_to(PROJECT_ROOT)) for t in targets],
        "findings_count": len(findings),
        "findings": [asdict(f) for f in findings],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--paper-dir",
        default=str(DEFAULT_PAPER_DIR),
        help="Directory with LaTeX manuscript sources (default: academic_paper).",
    )
    parser.add_argument(
        "--report-json",
        default=None,
        help="Optional path for a JSON report with all findings.",
    )
    args = parser.parse_args()

    paper_dir = Path(args.paper_dir).resolve()
    targets = _collect_targets(paper_dir)
    if not targets:
        print(f"[FAIL] No .tex files found in {paper_dir}")
        return 1

    compiled_rules: list[tuple[Rule, re.Pattern[str]]] = [
        (rule, re.compile(rule.pattern, re.IGNORECASE)) for rule in RULES
    ]

    findings: list[Finding] = []
    for target in targets:
        findings.extend(_scan_file(target, compiled_rules))

    if args.report_json:
        _write_report(Path(args.report_json).resolve(), findings, targets)

    if findings:
        _print_findings(findings)
        return 1

    print(f"[PASS] Paper sanity check passed ({len(targets)} file(s) scanned).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
