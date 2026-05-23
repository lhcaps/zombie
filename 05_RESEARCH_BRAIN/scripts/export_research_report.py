#!/usr/bin/env python3
"""
export_research_report.py — Export a full research report.

Usage:
    python export_research_report.py
    python export_research_report.py --output research_report.md
    python export_research_report.py --format html
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from core import (
    RB_DIR, source_registry_path, claim_ledger_path, hypothesis_board_path,
    contradiction_log_path, decision_log_path, open_questions_path,
    run_results_dir, test_protocols_dir,
    section, subsection, bullet, info, ok, warn, load_json,
)


def _format_timestamp(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return ts


def generate_report(output_format: str = "markdown", output_path: Path | None = None) -> str:
    """Generate a comprehensive research report."""
    registry = load_json(source_registry_path())
    ledger = load_json(claim_ledger_path())
    board = load_json(hypothesis_board_path())

    sources = registry.get("sources", [])
    claims = ledger.get("claims", [])
    hypotheses = board.get("hypotheses", [])
    stats = ledger.get("stats", {})

    lines = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Header
    lines.extend([
        "# Zombie Research Brain — Full Report",
        "",
        f"Generated: {now}",
        "",
        "---",
        "",
    ])

    # Executive Summary
    lines.extend([
        "## Executive Summary",
        "",
    ])
    active_hyps = [h for h in hypotheses if h.get("status") == "active"]
    untested = [h for h in active_hyps if not h.get("last_tested_at")]
    tested = [h for h in active_hyps if h.get("last_tested_at")]
    active_claims = [c for c in claims if c.get("status") == "active"]
    hard_constraints = [c for c in claims if c.get("type") == "hard_constraint" and c.get("status") == "active"]

    lines.extend([
        f"- **Total sources**: {len(sources)}",
        f"- **Total claims**: {len(claims)} ({stats.get('total_claims', 0)} tracked)",
        f"- **Active claims**: {len(active_claims)}",
        f"- **Hard constraints**: {len(hard_constraints)}",
        f"- **Total hypotheses**: {len(hypotheses)}",
        f"- **Active hypotheses**: {len(active_hyps)}",
        f"- **Untested**: {len(untested)}",
        f"- **Tested**: {len(tested)}",
        "",
    ])

    # Top Hypothesis
    if active_hyps:
        top = max(active_hyps, key=lambda h: h.get("priority_score", 0))
        lines.extend([
            f"### Top Priority Hypothesis",
            "",
            f"**{top['hypothesis_id']}**: {top['title']}",
            "",
            f"- Priority score: {top.get('priority_score', 0):.4f}",
            f"- Likelihood: {top.get('likelihood', 0):.3f}",
            f"- Evidence fit: {top.get('evidence_fit', 0):.2f}",
            f"- Constraint fit: {top.get('constraint_fit', 0):.2f}",
            f"- Test cost: {top.get('test_cost', 0)}/10",
            f"- Info gain: {top.get('expected_info_gain', 0):.1f}",
            "",
            f"{top.get('summary', '')}",
            "",
            f"**Required conditions**: {', '.join(top.get('required_conditions', []))}",
            "",
        ])

    # Sources
    lines.extend(["---", "", "## Sources", ""])
    lines.append("| ID | Title | Type | Tags | Findings |")
    lines.append("|---|-------|------|------|---------|")
    for src in sorted(sources, key=lambda s: s.get("source_id", "")):
        findings = len(src.get("key_findings", []))
        tags = ", ".join(src.get("tags", [])[:3])
        lines.append(
            f"| {src['source_id']} | {src['title'][:40]} | "
            f"{src['source_type']} | {tags} | {findings} |"
        )
    lines.append("")

    # Claims by Type
    lines.extend(["---", "", "## Claims", ""])
    by_type = stats.get("by_type", {})
    lines.append("### By Type")
    for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
        lines.append(f"- **{t}**: {count}")
    lines.append("")

    lines.append("### By Status")
    by_status = stats.get("by_status", {})
    for s, count in sorted(by_status.items(), key=lambda x: -x[1]):
        lines.append(f"- **{s}**: {count}")
    lines.append("")

    # Hard Constraints
    lines.extend(["### Hard Constraints", ""])
    for c in hard_constraints:
        lines.append(f"- [{c['claim_id']}] {c['claim']} (confidence: {c['confidence']:.2f})")
    lines.append("")

    # Soft Constraints
    soft = [c for c in claims if c.get("type") == "soft_constraint" and c.get("status") == "active"]
    if soft:
        lines.extend(["### Soft Constraints", ""])
        for c in soft:
            lines.append(f"- [{c['claim_id']}] {c['claim']} (confidence: {c['confidence']:.2f})")
        lines.append("")

    # Hypotheses
    lines.extend(["---", "", "## Hypotheses", ""])
    lines.append(f"**Total**: {len(hypotheses)} | **Active**: {len(active_hyps)} | **Rejected**: {len([h for h in hypotheses if h.get('status') == 'rejected'])}")
    lines.append("")

    # Sort: active first, then by priority
    sorted_hyps = sorted(hypotheses, key=lambda h: (
        0 if h.get("status") == "active" else 1,
        -(h.get("priority_score", 0)),
    ))

    lines.append("| # | Hypothesis ID | Title | Priority | Likelihood | Status | Tested |")
    lines.append("|---|---------------|-------|----------|------------|--------|--------|")
    for i, h in enumerate(sorted_hyps, 1):
        status = h.get("status", "?")
        tested_at = "Yes" if h.get("last_tested_at") else "No"
        title_short = h["title"][:35]
        lines.append(
            f"| {i} | {h['hypothesis_id']} | {title_short} | "
            f"{h.get('priority_score', 0):.4f} | {h.get('likelihood', 0):.3f} | "
            f"{status} | {tested_at} |"
        )
    lines.append("")

    # Test Results
    results_dir = run_results_dir()
    if results_dir.exists():
        result_files = list(results_dir.glob("*.json"))
        if result_files:
            lines.extend(["---", "", "## Test Results", ""])
            lines.append(f"**Total runs**: {len(result_files)}")
            lines.append("")

            results = []
            for f in result_files:
                try:
                    data = load_json(f)
                    results.append(data)
                except Exception:
                    pass

            results.sort(key=lambda r: r.get("created_at", ""), reverse=True)

            pass_count = sum(1 for r in results if r.get("outcome") == "PASS")
            fail_count = sum(1 for r in results if r.get("outcome") == "FAIL")
            inc_count = sum(1 for r in results if r.get("outcome") == "INCONCLUSIVE")

            lines.extend([
                f"- **PASS**: {pass_count}",
                f"- **FAIL**: {fail_count}",
                f"- **INCONCLUSIVE**: {inc_count}",
                "",
            ])

            lines.append("| Run ID | Hypothesis | Outcome | Confidence | Date |")
            lines.append("|--------|------------|---------|------------|------|")
            for r in results[:20]:
                run_id = r.get("run_id", r.get("case_id", "?"))
                hyp_id = r.get("hypothesis_id", "?")
                outcome = r.get("outcome", "?")
                conf = r.get("confidence", "?")
                date = _format_timestamp(r.get("created_at", ""))[:10]
                lines.append(f"| {run_id} | {hyp_id} | {outcome} | {conf} | {date} |")
            lines.append("")

    # Open Questions
    if Path(open_questions_path()).exists():
        oq_content = Path(open_questions_path()).read_text(encoding="utf-8")
        lines.extend(["---", "", "## Open Questions", ""])
        lines.append(oq_content)

    # Recent Decisions
    if Path(decision_log_path()).exists():
        dl_content = Path(decision_log_path()).read_text(encoding="utf-8")
        lines.extend(["---", "", "## Recent Decisions", ""])
        # Only show last 3000 chars
        lines.append(dl_content[-3000:])

    # Contradictions
    if Path(contradiction_log_path()).exists():
        cl_content = Path(contradiction_log_path()).read_text(encoding="utf-8")
        lines.extend(["---", "", "## Contradictions", ""])
        lines.append(cl_content[:2000])

    # Test Protocols
    protocols_dir = test_protocols_dir()
    if protocols_dir.exists():
        proto_files = list(protocols_dir.glob("*.json"))
        if proto_files:
            lines.extend(["---", "", "## Test Protocols", ""])
            for pf in sorted(proto_files)[:10]:
                try:
                    proto = load_json(pf)
                    lines.extend([
                        f"### {proto['protocol_id']} — {proto['hypothesis_id']}",
                        "",
                        f"**Goal**: {proto['goal']}",
                        f"**Steps**: {len(proto.get('steps', []))}",
                        f"**PASS**: {proto.get('pass_condition', '')[:100]}",
                        f"**FAIL**: {proto.get('fail_condition', '')[:100]}",
                        "",
                    ])
                except Exception:
                    pass

    # Footer
    lines.extend([
        "---",
        "",
        f"*Report generated by Zombie Research Brain at {now}*",
        f"*Project: https://github.com/lhcaps/zombie*",
    ])

    content = "\n".join(lines)

    if output_path:
        output_path.write_text(content, encoding="utf-8")
        ok(f"Report saved to {output_path}")

    return content


def main() -> None:
    parser = argparse.ArgumentParser(description="Export full research report")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument("--format", type=str, default="markdown", choices=["markdown", "html"],
                        help="Output format")
    args = parser.parse_args()

    section("Export Research Report")
    output_path = Path(args.output) if args.output else RB_DIR / "research_report.md"
    content = generate_report(args.format, output_path)
    ok(f"Report generated ({len(content)} characters)")
    print(f"\n{'='*60}")
    print(f"  Preview (first 2000 chars):")
    print(f"{'='*60}")
    print(content[:2000])


if __name__ == "__main__":
    main()
