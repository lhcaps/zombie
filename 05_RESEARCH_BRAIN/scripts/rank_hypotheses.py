#!/usr/bin/env python3
"""
rank_hypotheses.py — Rank hypotheses by evidence fit, constraint fit, and priority.

Usage:
    python rank_hypotheses.py
    python rank_hypotheses.py --top-n 10
    python rank_hypotheses.py --hypothesis-id HYP-CHAR_MIRROR-001
"""
from __future__ import annotations

import argparse

from core import (
    RB_DIR, hypothesis_board_path, claim_ledger_path, run_results_dir,
    source_registry_path, section, subsection, bullet, info, ok, warn,
    load_json, save_json, utc_now, load_prompt,
)


def _recompute_priority(hyp: dict) -> float:
    likelihood = hyp.get("likelihood", 0.0)
    info_gain = hyp.get("expected_info_gain", 1.0)
    test_cost = max(hyp.get("test_cost", 5), 1)
    constraint_fit = hyp.get("constraint_fit", 1.0)
    score = likelihood * info_gain * constraint_fit / test_cost
    hyp["priority_score"] = round(score, 4)
    return score


def _apply_test_results(board: dict, results_dir) -> None:
    """Apply test result evidence to hypothesis likelihoods."""
    if not results_dir.exists():
        return

    for result_file in results_dir.glob("*.json"):
        try:
            result = load_json(result_file)
            outcome = result.get("outcome", "").upper()
            hyp_id = result.get("hypothesis_id", "")

            if not hyp_id:
                continue

            for hyp in board.get("hypotheses", []):
                if hyp["hypothesis_id"] != hyp_id:
                    continue

                old_likelihood = hyp.get("likelihood", 0.0)
                old_score = _recompute_priority(hyp)

                if outcome == "PASS":
                    new_likelihood = min(0.99, old_likelihood * 1.5 + 0.2)
                    hyp["likelihood"] = round(new_likelihood, 4)
                    hyp["status"] = "active"
                    info(f"{hyp_id}: PASS -> likelihood {old_likelihood:.3f} -> {new_likelihood:.3f}")
                elif outcome == "FAIL":
                    new_likelihood = max(0.001, old_likelihood * 0.3)
                    hyp["likelihood"] = round(new_likelihood, 4)
                    hyp["status"] = "rejected"
                    info(f"{hyp_id}: FAIL -> likelihood {old_likelihood:.3f} -> {new_likelihood:.3f}")
                # INCONCLUSIVE: no change

                hyp["last_tested_at"] = result.get("created_at", utc_now())
                new_score = _recompute_priority(hyp)
                if new_score != old_score:
                    info(f"  Priority score: {old_score:.4f} -> {new_score:.4f}")

        except Exception as e:
            warn(f"Failed to apply {result_file.name}: {e}")


def rank_hypotheses(top_n: int = 10, focused_id: str | None = None) -> None:
    """Rank and display hypotheses."""
    board = load_json(hypothesis_board_path())
    hypotheses = board.get("hypotheses", [])

    # Apply test results
    results_dir = run_results_dir()
    _apply_test_results(board, results_dir)

    # Recompute all priorities
    for h in hypotheses:
        _recompute_priority(h)

    # Sort by priority
    hypotheses.sort(key=lambda h: (
        0 if h.get("status") in ("rejected", "deprecated", "blocked") else 1,
        -(h.get("priority_score", 0)),
    ))

    section("Hypothesis Ranking")

    if focused_id:
        focused = next((h for h in hypotheses if h["hypothesis_id"] == focused_id), None)
        if focused:
            subsection(focused["hypothesis_id"])
            print(f"\n  Title:   {focused['title']}")
            print(f"  Status:  {focused['status']}")
            print(f"  Priority: {focused.get('priority_score', 0):.4f}")
            print(f"  Likelihood: {focused.get('likelihood', 0):.4f}")
            print(f"  Evidence fit: {focused.get('evidence_fit', 0):.2f}")
            print(f"  Constraint fit: {focused.get('constraint_fit', 0):.2f}")
            print(f"  Test cost: {focused.get('test_cost', 0)}/10")
            print(f"  Info gain: {focused.get('expected_info_gain', 0):.1f}")
            print(f"\n  Summary: {focused['summary'][:200]}")
            print(f"\n  Required conditions:")
            for cond in focused.get("required_conditions", []):
                bullet(f"  - {cond}")
            print(f"\n  Supporting claims: {', '.join(focused.get('supporting_claims', []))}")
            print(f"  Contradicting claims: {', '.join(focused.get('contradicting_claims', []))}")
            print(f"\n  Unknowns:")
            for uq in focused.get("unknowns", []):
                bullet(f"  ? {uq}")
            return

    # Summary table
    print(f"\n  {'Rank':<5} {'ID':<25} {'Priority':<10} {'Likelihood':<12} {'Fit':<5} {'Cost':<5} {'Status':<12}")
    print(f"  {'-'*5} {'-'*25} {'-'*10} {'-'*12} {'-'*5} {'-'*5} {'-'*12}")

    displayed = 0
    for i, h in enumerate(hypotheses, 1):
        status = h.get("status", "?")
        if status in ("rejected", "deprecated") and displayed >= top_n:
            continue
        print(
            f"  {i:<5} {h['hypothesis_id']:<25} "
            f"{h.get('priority_score', 0):<10.4f} "
            f"{h.get('likelihood', 0):<12.3f} "
            f"{h.get('constraint_fit', 0):<5.1f} "
            f"{h.get('test_cost', 0):<5} "
            f"{status:<12}"
        )
        displayed += 1
        if displayed >= top_n:
            break

    # Status summary
    section("Status Summary")
    status_counts = {}
    for h in hypotheses:
        s = h.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
    for s, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        bullet(f"  {s}: {count}")

    # Top recommendation
    active = [h for h in hypotheses if h.get("status") == "active"]
    if active:
        top = max(active, key=lambda h: h.get("priority_score", 0))
        section("Top Recommendation")
        print(f"\n  Hypothesis: {top['hypothesis_id']} — {top['title']}")
        print(f"  Priority score: {top.get('priority_score', 0):.4f}")
        print(f"  Why: {top.get('notes', 'See hypothesis board for details')[:200]}")
        print(f"\n  Unknowns that need testing:")
        for uq in top.get("unknowns", [])[:3]:
            bullet(f"    ? {uq}")
        print(f"\n  Next: python generate_next_tests.py --hypothesis-id {top['hypothesis_id']}")

    # Save updated board
    board["hypotheses"] = hypotheses
    save_json(hypothesis_board_path(), board)
    ok("Hypothesis board updated with latest priorities")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank hypotheses by evidence and priority")
    parser.add_argument("--top-n", type=int, default=10, help="Number of hypotheses to display")
    parser.add_argument("--hypothesis-id", type=str, help="Show detailed info for a specific hypothesis")
    args = parser.parse_args()
    rank_hypotheses(args.top_n, args.hypothesis_id)


if __name__ == "__main__":
    main()
