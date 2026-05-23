#!/usr/bin/env python3
"""
update_after_result.py — Update beliefs after a test result is recorded.

Usage:
    python update_after_result.py --run-id RUN-20260523-001
    python update_after_result.py --run-id RUN-20260523-001 --interactive
"""
from __future__ import annotations

import argparse
from pathlib import Path

from core import (
    RB_DIR, hypothesis_board_path, claim_ledger_path, run_results_dir,
    source_registry_path, decision_log_path, open_questions_path,
    next_run_id, utc_now, section, subsection, bullet, info, warn, ok,
    load_json, save_json,
)


def _load_result(run_id: str) -> dict | None:
    result_path = run_results_dir() / f"{run_id}.json"
    if result_path.exists():
        return load_json(result_path)
    return None


def _apply_bayesian_update(hypothesis: dict, outcome: str) -> tuple[float, float, str]:
    """Apply Bayesian-like update to hypothesis likelihood."""
    old = hypothesis.get("likelihood", 0.0)

    if outcome == "PASS":
        new = min(0.99, old * 1.5 + 0.2)
        reasoning = f"PASS: boost by 20pp + 50% of remaining. {old:.3f} -> {new:.3f}"
    elif outcome == "FAIL":
        new = max(0.001, old * 0.3)
        reasoning = f"FAIL: reduce to 30% of prior. {old:.3f} -> {new:.3f}"
    else:  # INCONCLUSIVE
        new = old
        reasoning = f"INCONCLUSIVE: no change. {old:.3f} -> {new:.3f}"

    return old, round(new, 4), reasoning


def _detect_new_contradictions(result: dict, ledger: dict) -> list[tuple]:
    """Check if result creates new contradictions."""
    contradictions = []
    outcome = result.get("outcome", "")

    # If a test fails, it might contradict a claim that said it should pass
    if outcome == "FAIL":
        setup = result.get("setup", {})
        hypothesis = result.get("hypothesis_id", "")

        # Check if this failure contradicts any active soft constraints
        for claim in ledger.get("claims", []):
            if claim.get("status") in ("deprecated", "contradicted"):
                continue
            if claim.get("type") in ("soft_constraint", "inference"):
                claim_text = claim["claim"].lower()
                hyp_text = hypothesis.lower()
                # Simple heuristic: if claim mentions the tested mechanic
                if "char_mirror" in hyp_text and "char_mirror" not in claim_text:
                    pass  # Not a direct contradiction
    return contradictions


def update_beliefs(run_id: str, interactive: bool = False) -> None:
    """Update claim ledger and hypothesis board after a test result."""
    result = _load_result(run_id)
    if not result:
        warn(f"Run result not found: {run_id}")
        info(f"Available results in: {run_results_dir()}")
        for f in run_results_dir().glob("*.json"):
            bullet(f"  {f.stem}")
        return

    section(f"Update Beliefs — {run_id}")
    outcome = result.get("outcome", "?")
    hyp_id = result.get("hypothesis_id", "?")
    confidence = result.get("confidence", "?")

    print(f"\n  Outcome:     {outcome}")
    print(f"  Hypothesis:  {hyp_id}")
    print(f"  Confidence:  {confidence}")
    print(f"  Tester:      {result.get('tester', 'unknown')}")
    print(f"  Created:     {result.get('created_at', '?')}")

    # Load boards
    board = load_json(hypothesis_board_path())
    ledger = load_json(claim_ledger_path())

    # Find hypothesis
    hyp = next((h for h in board.get("hypotheses", []) if h["hypothesis_id"] == hyp_id), None)
    if not hyp:
        warn(f"Hypothesis not found: {hyp_id}")
        return

    # Idempotency guard — skip if this run_id was already applied
    applied = hyp.get("applied_run_ids", [])
    if run_id in applied:
        warn(f"Run {run_id} already applied to {hyp_id} — skipping (idempotent)")
        ok("Belief update skipped (already applied)")
        return

    old_likelihood, new_likelihood, reasoning = _apply_bayesian_update(hyp, outcome)
    old_status = hyp.get("status", "?")
    old_priority = hyp.get("priority_score", 0)

    # Update hypothesis
    hyp["likelihood"] = new_likelihood
    hyp["last_tested_at"] = result.get("created_at", utc_now())

    # Update status based on outcome
    if outcome == "PASS":
        hyp["status"] = "active"
    elif outcome == "FAIL":
        hyp["status"] = "rejected"

    # Recompute priority
    test_cost = max(hyp.get("test_cost", 5), 1)
    info_gain = hyp.get("expected_info_gain", 1.0)
    constraint_fit = hyp.get("constraint_fit", 1.0)
    new_priority = new_likelihood * info_gain * constraint_fit / test_cost
    hyp["priority_score"] = round(new_priority, 4)
    hyp["updated_at"] = utc_now()
    hyp.setdefault("applied_run_ids", []).append(run_id)

    print(f"\n  Hypothesis:  {hyp_id}")
    print(f"  Status:      {old_status} -> {hyp['status']}")
    print(f"  Likelihood: {old_likelihood:.4f} -> {new_likelihood:.4f}")
    print(f"  Reasoning:  {reasoning}")
    print(f"  Priority:   {old_priority:.4f} -> {new_priority:.4f}")

    # Add belief_update to result
    result["belief_update"] = {
        "hypothesis_updated": hyp_id,
        "old_likelihood": old_likelihood,
        "new_likelihood": new_likelihood,
        "reasoning": reasoning,
    }
    result_path = run_results_dir() / f"{run_id}.json"
    save_json(result_path, result)
    ok(f"Result updated with belief_update")

    # Add interpretation claim if provided
    interpretation = result.get("interpretation", "")
    if interpretation:
        claim_id = next_claim_id_from_ledger(ledger)
        new_claim = {
            "claim_id": claim_id,
            "source_id": "SRC-RESULTS",
            "claim": f"Test result for {hyp_id}: {interpretation}",
            "type": "passed_test" if outcome == "PASS" else ("failed_test" if outcome == "FAIL" else "observation"),
            "polarity": "positive" if outcome == "PASS" else "negative" if outcome == "FAIL" else "neutral",
            "confidence": {"high": 0.95, "medium": 0.7, "low": 0.4}.get(confidence, 0.5),
            "evidence": f"Run {run_id}: {outcome} with {confidence} confidence. {interpretation}",
            "status": "active",
            "contradicts": [],
            "supported_by": [],
            "tags": ["test_result", hyp_id.lower(), outcome.lower()],
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "notes": "",
        }
        ledger["claims"].append(new_claim)
        _recompute_claim_stats(ledger)
        save_json(claim_ledger_path(), ledger)
        ok(f"Added claim {claim_id} for test interpretation")

    # Save updated hypothesis board
    save_json(hypothesis_board_path(), board)
    ok("Hypothesis board updated")

    # Log decision
    _append_decision_log(run_id, outcome, hyp_id, old_likelihood, new_likelihood, reasoning)
    ok("Decision logged")

    # Update open questions
    _check_open_questions(outcome, hyp_id, result)

    section("Recommended Next Actions")
    active = [h for h in board.get("hypotheses", []) if h.get("status") == "active"]
    active.sort(key=lambda h: h.get("priority_score", 0), reverse=True)

    if outcome == "PASS":
        print("\n  PASS result! Next steps:")
        bullet("Test with opposite gender (if not already done)")
        bullet("Test with different count candidate")
        bullet("Validate with another independent run")
        if active:
            next_hyp = max(active, key=lambda h: h.get("priority_score", 0))
            bullet(f"Also test: {next_hyp['hypothesis_id']} — {next_hyp['title']}")
    elif outcome == "FAIL":
        print("\n  FAIL result. Next steps:")
        bullet(f"Reduce {hyp_id} likelihood to near zero")
        bullet("Try lower count candidate (45, 40)")
        bullet("Fall back to next highest priority hypothesis")
        if active:
            for h in active[:2]:
                if h["hypothesis_id"] != hyp_id:
                    bullet(f"  Test: {h['hypothesis_id']} — {h['title']}")
    else:
        print("\n  INCONCLUSIVE result. Fix issues and retest.")
        bullet("Review common mistakes in the test protocol")
        bullet("Ensure all controlled variables are correct")
        bullet(f"Retry: {run_id}")


def next_claim_id_from_ledger(ledger: dict) -> str:
    existing = [c["claim_id"] for c in ledger.get("claims", []) if c.get("claim_id", "").startswith("CLM-")]
    nums = sorted([int(e.replace("CLM-", "")) for e in existing])
    return f"CLM-{nums[-1] + 1:04d}"


def _recompute_claim_stats(ledger: dict) -> None:
    claims = ledger.get("claims", [])
    by_type = {}
    by_status = {}
    for c in claims:
        t = c.get("type", "unknown")
        s = c.get("status", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        by_status[s] = by_status.get(s, 0) + 1
    ledger["stats"] = {"total_claims": len(claims), "by_type": by_type, "by_status": by_status}


def _append_decision_log(run_id: str, outcome: str, hyp_id: str,
                          old_lik: float, new_lik: float, reasoning: str) -> None:
    path = decision_log_path()
    now = utc_now()

    entry = f"""
### {now} — TEST_EXECUTED + BELIEF_UPDATED

- **Run**: {run_id}
- **Hypothesis**: {hyp_id}
- **Outcome**: {outcome}
- **Old likelihood**: {old_lik:.4f}
- **New likelihood**: {new_lik:.4f}
- **Reasoning**: {reasoning}
- **Decision type**: TEST_EXECUTED, BELIEF_UPDATED
- **Who**: automated belief update

"""
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Decision Log\n"
    path.write_text(existing + entry, encoding="utf-8")


def _check_open_questions(outcome: str, hyp_id: str, result: dict) -> None:
    """Check if any open questions were answered by this result."""
    setup = result.get("setup", {})
    execution = result.get("execution", {})
    count_target = execution.get("count_target", "?")
    count_actual = execution.get("actual_count", "?")
    gender = setup.get("post_reroll_gender", "?")

    questions_resolved = []
    questions_raised = []

    if outcome == "PASS" and count_actual == count_target:
        questions_resolved.append(
            f"Count {count_target} with gender {gender} appears to work (PASS)"
        )
    elif outcome == "FAIL":
        questions_resolved.append(
            f"Count {count_target} with gender {gender} does NOT work (FAIL)"
        )
        questions_raised.append(
            f"What count is correct after {hyp_id} failed at {count_target}?"
        )

    if questions_resolved:
        info("Questions resolved by this test:")
        for q in questions_resolved:
            bullet(f"  + {q}")

    if questions_raised:
        warn("New questions raised by this test:")
        for q in questions_raised:
            bullet(f"  ? {q}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update beliefs after test result")
    parser.add_argument("--run-id", type=str, help="Run ID to update (e.g. RUN-20260523-001)")
    parser.add_argument("--interactive", action="store_true", help="Review updates interactively")
    args = parser.parse_args()

    if not args.run_id:
        # List available results
        section("Available Test Results")
        results = sorted(run_results_dir().glob("*.json"))
        if not results:
            info("No results yet. Run 03_TOOLS/zombie_test_runner.py --mode=record first.")
            return
        for r in results:
            data = load_json(r)
            outcome = data.get("outcome", "?")
            hyp_id = data.get("hypothesis_id", "?")
            created = data.get("created_at", "?")
            print(f"  {r.stem} | {outcome} | {hyp_id} | {created}")
        info("Run with --run-id RUN-XXXXX to update beliefs")
        return

    update_beliefs(args.run_id, args.interactive)


if __name__ == "__main__":
    main()
