#!/usr/bin/env python3
"""
build_claim_table.py — Build constraint model from claim ledger.

Generates a constraint table markdown file and updates hypothesis board
with current constraint information.

Usage:
    python build_claim_table.py
    python build_claim_table.py --output constraints.md
"""
from __future__ import annotations

import argparse
from pathlib import Path

from core import (
    RB_DIR, claim_ledger_path, hypothesis_board_path,
    source_registry_path, contradiction_log_path,
    section, subsection, bullet, info, ok, warn, load_json, save_json,
    utc_now, load_prompt,
)


HARD_TYPES = {"hard_constraint"}
SOFT_TYPES = {"soft_constraint"}
NEGATIVE_TYPES = {"negative_constraint"}
DEPRECATED_TYPES = {"deprecated_path"}


def build_constraint_table() -> dict:
    """Build a constraint model from the claim ledger."""
    ledger = load_json(claim_ledger_path())
    registry = load_json(source_registry_path())
    sources = {s["source_id"]: s["title"] for s in registry.get("sources", [])}

    claims = ledger.get("claims", [])
    hard_constraints = []
    soft_constraints = []
    negative_constraints = []
    deprecated_paths = []

    for c in claims:
        if c.get("status") in ("deprecated", "contradicted"):
            continue
        entry = {
            "claim_id": c["claim_id"],
            "claim": c["claim"],
            "type": c["type"],
            "confidence": c["confidence"],
            "source_id": c["source_id"],
            "source_title": sources.get(c["source_id"], c["source_id"]),
            "contradicts": c.get("contradicts", []),
            "tags": c.get("tags", []),
        }
        if c["type"] == "hard_constraint":
            hard_constraints.append(entry)
        elif c["type"] == "soft_constraint":
            soft_constraints.append(entry)
        elif c["type"] == "deprecated_path":
            deprecated_paths.append(entry)
        elif c["polarity"] == "negative":
            negative_constraints.append(entry)

    return {
        "hard_constraints": hard_constraints,
        "soft_constraints": soft_constraints,
        "negative_constraints": negative_constraints,
        "deprecated_paths": deprecated_paths,
    }


def generate_constraint_markdown(constraints: dict, model: dict) -> str:
    """Generate a markdown constraint table."""
    lines = [
        "# Constraint Model",
        "",
        f"Generated: {utc_now()}",
        "",
        "## Hard Constraints (Must be obeyed — blocking)",
        "",
        "| # | Claim ID | Constraint | Confidence | Source | Tags |",
        "|---|----------|------------|------------|--------|------|",
    ]
    for i, c in enumerate(constraints["hard_constraints"], 1):
        tags = ", ".join(c["tags"][:3])
        lines.append(
            f"| {i} | {c['claim_id']} | {c['claim'][:60]} | "
            f"{c['confidence']:.2f} | {c['source_title'][:25]} | {tags} |"
        )

    lines.extend(["", "## Soft Constraints (Likely true but unproven)", ""])
    lines.append("| # | Claim ID | Constraint | Confidence | Source | Tags |")
    lines.append("|---|----------|------------|------------|--------|------|")
    for i, c in enumerate(constraints["soft_constraints"], 1):
        tags = ", ".join(c["tags"][:3])
        lines.append(
            f"| {i} | {c['claim_id']} | {c['claim'][:60]} | "
            f"{c['confidence']:.2f} | {c['source_title'][:25]} | {tags} |"
        )

    lines.extend(["", "## Negative Constraints (Must NOT happen)", ""])
    lines.append("| # | Claim ID | Constraint | Confidence | Source |")
    lines.append("|---|----------|------------|------------|--------|")
    for i, c in enumerate(constraints["negative_constraints"], 1):
        lines.append(
            f"| {i} | {c['claim_id']} | {c['claim'][:60]} | "
            f"{c['confidence']:.2f} | {c['source_title'][:25]} |"
        )

    lines.extend(["", "## Deprecated Paths (Known broken routes)", ""])
    lines.append("| # | Claim ID | Deprecated Route | Confidence | Source |")
    lines.append("|---|----------|-----------------|------------|--------|")
    for i, c in enumerate(constraints["deprecated_paths"], 1):
        lines.append(
            f"| {i} | {c['claim_id']} | {c['claim'][:60]} | "
            f"{c['confidence']:.2f} | {c['source_title'][:25]} |"
        )

    # Contradiction summary
    ledger = load_json(claim_ledger_path())
    claims = ledger.get("claims", [])
    contradictions = [(c["claim_id"], c.get("contradicts", [])) for c in claims if c.get("contradicts")]
    lines.extend(["", "## Contradictions", ""])
    if contradictions:
        lines.append("| Claim A | Contradicts |")
        lines.append("|---------|------------|")
        for cid, contrs in contradictions:
            for c2 in contrs:
                lines.append(f"| {cid} | {c2} |")
    else:
        lines.append("*No contradictions currently active.*")

    # Coverage
    lines.extend(["", "## Coverage by Tag", ""])
    tag_counts = {}
    for c in claims:
        if c.get("status") in ("deprecated", "contradicted"):
            continue
        for tag in c.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    lines.append("| Tag | Claims |")
    lines.append("|-----|--------|")
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {tag} | {count} |")

    return "\n".join(lines)


def update_hypothesis_constraint_fit(hypothesis_board: dict, constraints: dict) -> None:
    """Recompute constraint_fit for each hypothesis."""
    hard_claims = {c["claim_id"]: c["claim"].lower() for c in constraints["hard_constraints"]}
    negative_claims = {c["claim_id"]: c["claim"].lower() for c in constraints["negative_constraints"]}

    for hyp in hypothesis_board.get("hypotheses", []):
        if hyp.get("status") in ("rejected", "deprecated"):
            continue

        # Check if any supporting claim was contradicted
        supporting = hyp.get("supporting_claims", [])
        contradicted_supporting = [cid for cid in supporting if cid in hyp.get("contradicting_claims", [])]

        # Check constraint violations
        violates = False
        for req in hyp.get("required_conditions", []):
            req_lower = req.lower()
            for neg_c in negative_claims.values():
                if any(word in neg_c for word in req_lower.split("_")):
                    if any(negword in req_lower for negword in ["no_", "not_", "without_"]):
                        continue
                    violate_keywords = ["command", "volt", "mode", "two_reroll", "multi_reroll"]
                    if any(vk in req_lower for vk in violate_keywords):
                        if "no_" not in req_lower:
                            violates = True

        hyp["constraint_fit"] = 0.0 if violates else 1.0

        # Recompute priority
        likelihood = hyp.get("likelihood", 0)
        info_gain = hyp.get("expected_info_gain", 1.0)
        test_cost = hyp.get("test_cost", 5)
        constraint_fit = hyp.get("constraint_fit", 1.0)
        if test_cost > 0:
            hyp["priority_score"] = likelihood * info_gain * constraint_fit / test_cost
        else:
            hyp["priority_score"] = 0.0

        hyp["updated_at"] = utc_now()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build constraint model from claim ledger")
    parser.add_argument("--output", type=str, help="Output path for constraint markdown")
    args = parser.parse_args()

    section("Build Constraint Model")
    info("Reading claim ledger...")
    constraints = build_constraint_table()

    print(f"\n  Hard constraints:     {len(constraints['hard_constraints'])}")
    print(f"  Soft constraints:     {len(constraints['soft_constraints'])}")
    print(f"  Negative constraints: {len(constraints['negative_constraints'])}")
    print(f"  Deprecated paths:     {len(constraints['deprecated_paths'])}")

    # Generate markdown
    model = {}
    md = generate_constraint_markdown(constraints, model)

    output_path = Path(args.output) if args.output else RB_DIR / "constraint_model.md"
    output_path.write_text(md, encoding="utf-8")
    ok(f"Constraint model written to {output_path.relative_to(RB_DIR)}")

    # Update hypothesis board constraint_fit
    info("Updating hypothesis constraint fits...")
    board = load_json(hypothesis_board_path())
    update_hypothesis_constraint_fit(board, constraints)
    save_json(hypothesis_board_path(), board)
    ok("Hypothesis board updated")

    section("Active Hypotheses by Priority")
    board = load_json(hypothesis_board_path())
    active = [h for h in board.get("hypotheses", []) if h.get("status") == "active"]
    active.sort(key=lambda h: h.get("priority_score", 0), reverse=True)
    for i, h in enumerate(active, 1):
        print(f"\n  {i}. {h['hypothesis_id']}: {h['title']}")
        bullet(f"Priority: {h.get('priority_score', 0):.3f} | Constraint fit: {h.get('constraint_fit', 0):.1f}")
        bullet(f"Likelihood: {h.get('likelihood', 0):.3f} | Info gain: {h.get('expected_info_gain', 0):.1f}")


if __name__ == "__main__":
    main()
