"""
Zombie Quest - Updated CLI
==========================

Commands:
    python zombie_test_runner.py --mode=list
    python zombie_test_runner.py --mode=priorities
    python zombie_test_runner.py --mode=next
    python zombie_test_runner.py --mode=csp
    python zombie_test_runner.py --mode=coverage
    python zombie_test_runner.py --mode=dispatch --max=4
    python zombie_test_runner.py --mode=record --case-id=CORE_M_50 --outcome=fail
    python zombie_test_runner.py --mode=record --case-id=TAIL_F_50_CHAR_MIRROR --outcome=fail
        --hypothesis-id=HYP-CHAR_MIRROR-001 --run-id=RUN-20260523-001 --rich
        --npc-before="..." --npc-after="..." --count-target=50 --count-actual=50
        --gender=F --race="Soul Reaper" --notes="..."
    python zombie_test_runner.py --mode=report
    python zombie_test_runner.py --mode=generate
    python zombie_test_runner.py --mode=simulate

The --rich flag records in the full Research Brain run_result format,
saving to both 03_TOOLS/zombie_test_runner/results/ and 05_RESEARCH_BRAIN/run_results/.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


sys.path.insert(0, str(Path(__file__).parent))

from zombie_analysis import AnalysisEngine
from zombie_csp_model import ProbabilityEngine, make_engine, make_model
from zombie_dispatcher import MultiAgentDispatcher
from zombie_test_generator import CoverageTracker
from zombie_tail_simulator import print_summary, score_candidates, write_reports


OUT_DIR = Path(r"D:\Study\Project\zombie\03_TOOLS\zombie_test_runner")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def status_icon(status: str) -> str:
    return {
        "untested": "[ ]",
        "pass": "[PASS]",
        "fail": "[FAIL]",
        "blocked": "[WARN]",
        "tested": "[~]",
    }.get(status, status)


def cmd_list(tracker: CoverageTracker, args):
    cases = tracker.all_cases()
    print("\n" + "=" * 78)
    print(f"  ZOMBIE QUEST - UPDATED TEST CASES ({len(cases)} total)")
    print("=" * 78)
    print()
    print(f"{'#':<4} {'Type':<13} {'Spec':<24} {'P':>8} {'IG':>6} {'Status':<10} Label")
    print(f"{'-'*4} {'-'*13} {'-'*24} {'-'*8} {'-'*6} {'-'*10} {'-'*20}")
    for c in cases:
        print(
            f"{c.priority:<4} {c.test_type:<13} {c.spec:<24} "
            f"{c.probability:>8.4f} {c.info_gain:>6.2f} "
            f"{status_icon(c.status)} {c.status:<10} {c.label}"
        )
    print(f"\nUntested: {len(tracker.untested_cases())} / {len(cases)}")


def cmd_priorities(tracker: CoverageTracker, eng: ProbabilityEngine, args):
    tested = {f"{c.test_type}:{c.spec}" for c in tracker.all_cases() if c.status != "untested"}
    print("\n" + "=" * 78)
    print("  ZOMBIE QUEST - UPDATED RANKED PRIORITIES")
    print("=" * 78)
    print()
    print(f"{'#':<4} {'Type':<13} {'Spec':<24} {'P(success)':>10} {'IG':>8} {'Score':>8} Label")
    print(f"{'-'*4} {'-'*13} {'-'*24} {'-'*10} {'-'*8} {'-'*8} {'-'*20}")
    for i, t in enumerate(eng.ranked_tests(30), 1):
        mark = "[x]" if f"{t['type']}:{t['spec']}" in tested else "[ ]"
        print(
            f"{mark}{i:<2} {t['type']:<13} {t['spec']:<24} "
            f"{t['p']:>10.4f} {t['info_gain']:>8.2f} {t['score']:>8.4f} {t['label']}"
        )


def cmd_next(tracker: CoverageTracker, args):
    nxt = tracker.next_case()
    if not nxt:
        print("\nAll updated cases have been tested.")
        return
    print("\n" + "=" * 78)
    print("  NEXT BEST UPDATED TEST")
    print("=" * 78)
    print(f"\n  Case:       {nxt.case_id}")
    print(f"  Type:       {nxt.test_type}")
    print(f"  Spec:       {nxt.spec}")
    print(f"  Label:      {nxt.label}")
    print(f"  P(success): {nxt.probability:.4f}")
    print(f"  Info Gain:  {nxt.info_gain:.2f} bits")
    print("\n  Description:")
    print(f"  {nxt.description}")
    print("\n  Steps:")
    for step in nxt.steps:
        print(f"    {step['step']}. [{step.get('phase', '?')}] {step['action']}")
        actor = step.get("actor")
        target = step.get("target")
        repeat = step.get("repeat")
        if actor is not None or target is not None or repeat:
            print(f"       actor={actor}, target={target}, repeat={repeat or '-'}")
    print("\n  Hard Rules:")
    for rule in nxt.constraints:
        print(f"    - {rule}")


def cmd_coverage(tracker: CoverageTracker, args):
    print(tracker.coverage_report())


def cmd_dispatch(tracker: CoverageTracker, eng: ProbabilityEngine, dispatcher: MultiAgentDispatcher, args):
    max_dispatch = args.max or 12
    tests = eng.ranked_tests(max_dispatch)
    dispatcher.enqueue_all(tests)
    print(f"\n[Dispatcher] Enqueued {len(tests)} updated tests")
    for i, t in enumerate(tests[:8], 1):
        print(f"  #{i} {t['label']} P={t['p']:.4f} IG={t['info_gain']:.2f}")
    print(f"\n  Task files: {dispatcher.tasks_dir}")
    print(f"  Pending:    {dispatcher.pending_count()}")


def cmd_report(args):
    results = load_results()
    engine = AnalysisEngine()
    report = engine.full_report(results)
    report_path = OUT_DIR / f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nReport saved to: {report_path}")


def cmd_csp(eng: ProbabilityEngine, args):
    csp = eng.csp
    print("\n" + "=" * 78)
    print("  ZOMBIE QUEST - UPDATED CSP MODEL")
    print("=" * 78)
    print("\n  Variables:")
    print("    final_gender in {M, F}")
    print("    same_gender_zombification_amount in {40, 45, 49, 50}")
    print("    tail_task_pair in candidate pairs")
    print("\n  Hard skeleton:")
    print("    gender reroll exactly once -> same-gender zombify N -> tail A -> tail B")
    print("\n  Count probabilities:")
    for count in csp.all_counts:
        print(f"    x{count.amount:<2} P={count.confidence:.2f}  {count.reason}")
    print("\n  Unknown pair probabilities:")
    for pair in csp.all_unknown_pairs:
        print(f"    {pair.id:<14} P={pair.confidence:.2f}  {pair.label}")
        print(f"      tasks: {pair.tasks[0]} / {pair.tasks[1]}")
    print("\n  Constraints:")
    for c in ProbabilityEngine.CONSTRAINTS.values():
        kind = "HARD" if c.weight >= 1.0 else "SOFT"
        print(f"    [{kind}] {c.name:<24} w={c.weight:.1f} - {c.description}")


def cmd_generate(tracker: CoverageTracker, args):
    cases_data = [
        {
            "case_id": c.case_id,
            "test_type": c.test_type,
            "spec": c.spec,
            "label": c.label,
            "description": c.description,
            "steps": c.steps,
            "constraints": c.constraints,
            "probability": c.probability,
            "info_gain": c.info_gain,
            "score": c.score,
            "priority": c.priority,
            "status": c.status,
        }
        for c in tracker.all_cases()
    ]
    path = OUT_DIR / "all_test_cases.json"
    path.write_text(json.dumps(cases_data, indent=2), encoding="utf-8")
    print(f"\nGenerated {len(cases_data)} updated test cases -> {path}")


def cmd_simulate(args):
    scored = score_candidates()
    print_summary(scored)
    json_path, md_path = write_reports(scored)
    print("\nReports:")
    print(f"  {json_path}")
    print(f"  {md_path}")


def _next_run_id_for_tools(out_dir: Path) -> str:
    today = datetime.now().strftime("%Y%m%d")
    existing = []
    results_dir = out_dir / "results"
    if results_dir.exists():
        for f in results_dir.glob("*.json"):
            import re
            m = re.match(r"RUN-(\d{8})-(\d{3})", f.stem)
            if m and m.group(1) == today:
                existing.append(f"RUN-{m.group(1)}-{m.group(2)}")
    base = f"RUN-{today}-"
    if not existing:
        return f"{base}001"
    nums = sorted(int(e.replace(base, "")) for e in existing)
    return f"{base}{nums[-1] + 1:03d}"


def _build_rich_result(
    case, parsed: dict, outcome: str, args,
    notes: str, tester: str,
) -> dict:
    """Build a full Research Brain run_result dict."""
    outcome_upper = outcome.upper()  # already INCONCLUSIVE/PASS/FAIL from caller
    confidence = getattr(args, "confidence", "medium")
    gender = getattr(args, "gender", parsed.get("gender", "?"))
    race = getattr(args, "race", "?")
    count_target = getattr(args, "count_target", parsed.get("amount", 50))
    count_actual = getattr(args, "count_actual", count_target)
    npc_before = getattr(args, "npc_before", "")
    npc_after = getattr(args, "npc_after", "")
    balance_before = getattr(args, "balance_before", "")
    balance_after = getattr(args, "balance_after", "")
    screenshots_raw = getattr(args, "screenshots", [])
    if isinstance(screenshots_raw, str):
        screenshots = [s.strip() for s in screenshots_raw.split(",") if s.strip()]
    else:
        screenshots = list(screenshots_raw)
    video = getattr(args, "video", "")
    server_type = getattr(args, "server_type", "private")
    world = getattr(args, "world", "base")
    mode_used = getattr(args, "mode_used", False)
    commands_used = getattr(args, "commands_used", [])
    grip_method = getattr(args, "grip_method", "manual")
    blood_bar_method = getattr(args, "blood_bar_method", "passive")
    mirror_active = getattr(args, "mirror_active", False)
    npc_checked_str = getattr(args, "npc_checked_at", [])
    if isinstance(npc_checked_str, str):
        npc_checked_at = [int(x) for x in npc_checked_str.split(",") if x.strip()] if npc_checked_str else []
    else:
        npc_checked_at = list(npc_checked_str)
    run_id = getattr(args, "run_id", _next_run_id_for_tools(OUT_DIR))
    hyp_id = getattr(args, "hypothesis_id", "")
    if not hyp_id:
        if case.test_type == "unknown_pair":
            hyp_id_map = {
                "CHAR_MIRROR": "HYP-CHAR_MIRROR-001",
                "PASSIVE_GRIP": "HYP-PASSIVE-001",
                "COUNT_ONLY": "HYP-COUNT_ONLY-001",
                "T_G_BASE": "HYP-T_G_BASE-001",
                "X_C_BASE": "HYP-X_C_BASE-001",
                "COMMANDS": "HYP-COMMANDS-001",
            }
            hyp_id = hyp_id_map.get(parsed.get("pair_id", ""), "")
        else:
            hyp_id = "HYP-COUNT_ONLY-001"

    # Determine protocol_id if available
    rb_dir = Path(r"D:\Study\Project\zombie\05_RESEARCH_BRAIN")
    protocol_id = ""
    if rb_dir.exists():
        import re
        for pf in (rb_dir / "test_protocols").glob("*.json"):
            data = json.loads(pf.read_text(encoding="utf-8"))
            if data.get("hypothesis_id") == hyp_id:
                protocol_id = data.get("protocol_id", "")
                break

    return {
        "run_id": run_id,
        "case_id": case.case_id,
        "hypothesis_id": hyp_id,
        "protocol_id": protocol_id,
        "outcome": outcome_upper,
        "confidence": confidence,
        "setup": {
            "game": "Type Soul",
            "server_type": server_type,
            "world": world,
            "starting_gender": gender,
            "post_reroll_gender": gender,
            "race": race,
            "mode_used": mode_used,
            "commands_used": commands_used,
        },
        "execution": {
            "count_target": int(count_target),
            "actual_count": int(count_actual),
            "target_gender": gender,
            "target_race": getattr(args, "target_race", "any"),
            "blood_bar_method": blood_bar_method,
            "grip_method": grip_method,
            "character_mirror_active": mirror_active,
            "npc_checked_at": npc_checked_at,
            "npc_checked_values": [],
            "rerolls_performed": 1,
            "duration_min": float(getattr(args, "duration_min", 0)),
        },
        "evidence": {
            "npc_before": npc_before,
            "npc_after": npc_after,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "screenshots": screenshots,
            "video": video,
            "raw_notes": notes,
        },
        "interpretation": getattr(args, "interpretation", ""),
        "notes": notes,
        "created_at": datetime.now().isoformat(),
        "tester": tester,
    }


def cmd_record(tracker: CoverageTracker, args):
    if not args.case_id or not args.outcome:
        print("Error: --case-id and --outcome are required")
        return
    case = next((c for c in tracker.all_cases() if c.case_id == args.case_id), None)
    if not case:
        print(f"Error: unknown case id {args.case_id}")
        return

    outcome = args.outcome.lower()
    # Map 'blocked' to 'inconclusive' for Research Brain compatibility
    rich_outcome = "INCONCLUSIVE" if outcome == "blocked" else outcome.upper()
    tracker.mark_tested(args.case_id, outcome, args.notes or "")
    parsed = tracker.eng.parse_spec(case.spec)
    tester = "manual"

    # --- Legacy format (always written to 03_TOOLS) ---
    legacy_result = {
        "run_id": args.case_id,
        "case_id": args.case_id,
        "test_type": case.test_type,
        "spec": case.spec,
        "amount": parsed["amount"],
        "final_gender": parsed["gender"],
        "pair_id": parsed.get("pair_id", ""),
        "hypothesis": parsed.get("pair_id", "") if case.test_type == "unknown_pair" else "COUNT_ONLY",
        "outcome": outcome.upper(),
        "notes": args.notes or "",
        "timestamp": datetime.now().isoformat(),
        "ai_agent": tester,
        "duration_min": 0.0,
    }
    legacy_file = OUT_DIR / "results" / f"{args.case_id}.json"
    legacy_file.parent.mkdir(parents=True, exist_ok=True)
    legacy_file.write_text(json.dumps(legacy_result, indent=2), encoding="utf-8")
    print(f"\nRecorded: {args.case_id} -> {outcome.upper()}")
    print(f"Legacy result: {legacy_file}")

    # --- Rich format (Research Brain format) ---
    rich_result = _build_rich_result(case, parsed, rich_outcome, args, args.notes or "", args.tester)
    run_id = rich_result["run_id"]

    # Save to 05_RESEARCH_BRAIN/run_results/ if available
    rb_dir = Path(r"D:\Study\Project\zombie\05_RESEARCH_BRAIN")
    rb_results_dir = rb_dir / "run_results"
    if rb_results_dir.exists():
        rich_path = rb_results_dir / f"{run_id}.json"
        rich_path.write_text(json.dumps(rich_result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Rich result:  {rich_path}")
    else:
        # Save alongside legacy result
        rich_path = OUT_DIR / "results" / f"{run_id}_rich.json"
        rich_path.write_text(json.dumps(rich_result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Rich result:  {rich_path} (05_RESEARCH_BRAIN not found, saved locally)")

    print(f"\n  Run ID:      {run_id}")
    print(f"  Hypothesis:  {rich_result['hypothesis_id']}")
    print(f"  Outcome:     {rich_result['outcome']}")
    print(f"  Confidence:  {rich_result['confidence']}")

    nxt = tracker.next_case()
    if nxt:
        print(f"\nNext case: {nxt.case_id} - {nxt.label}")
        print(f"  Run: python zombie_test_runner.py --mode=record --case-id={nxt.case_id} --outcome=<pass|fail|inconclusive> --rich --hypothesis-id=HYP-...")
        print(f"  Then: python 05_RESEARCH_BRAIN/scripts/update_after_result.py --run-id={run_id}")
    else:
        print("\nAll test cases have been recorded.")


def cmd_run_interactive(tracker: CoverageTracker, args):
    print("\nInteractive mode. Press q to quit.")
    while True:
        nxt = tracker.next_case()
        if not nxt:
            print("All updated cases have been tested.")
            break
        print(f"\n{nxt.case_id}: {nxt.label}")
        print(nxt.description)
        outcome = input("Outcome (pass/fail/blocked/q): ").strip().lower()
        if outcome == "q":
            break
        if outcome not in {"pass", "fail", "blocked"}:
            print("Invalid outcome.")
            continue
        notes = input("Notes: ").strip()
        class Args:
            pass
        a = Args()
        a.case_id = nxt.case_id
        a.outcome = outcome
        a.notes = notes
        cmd_record(tracker, a)


def load_results() -> list[dict]:
    results = []
    results_dir = OUT_DIR / "results"
    if not results_dir.exists():
        return results
    for path in results_dir.glob("*.json"):
        try:
            results.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return results


def main():
    parser = argparse.ArgumentParser(description="Zombie Quest updated test runner")
    parser.add_argument(
        "--mode",
        default="list",
        choices=[
            "list",
            "priorities",
            "next",
            "coverage",
            "dispatch",
            "report",
            "csp",
            "generate",
            "simulate",
            "record",
            "run",
        ],
    )
    parser.add_argument("--max", type=int, default=None)
    parser.add_argument("--case-id", type=str)
    parser.add_argument("--outcome", type=str, choices=["pass", "fail", "blocked"])
    parser.add_argument("--notes", type=str, default="")
    # --- Rich record arguments ---
    parser.add_argument("--rich", action="store_true",
                        help="Also save result in Research Brain format")
    parser.add_argument("--run-id", type=str,
                        help="Explicit run ID (e.g. RUN-20260523-001)")
    parser.add_argument("--hypothesis-id", type=str,
                        help="Hypothesis ID (e.g. HYP-CHAR_MIRROR-001)")
    parser.add_argument("--protocol-id", type=str,
                        help="Protocol ID (e.g. PROT-0001)")
    parser.add_argument("--confidence", type=str, default="medium",
                        choices=["low", "medium", "high"])
    parser.add_argument("--gender", type=str, choices=["M", "F"])
    parser.add_argument("--race", type=str, default="Soul Reaper")
    parser.add_argument("--server-type", type=str, default="private")
    parser.add_argument("--world", type=str, default="base")
    parser.add_argument("--count-target", type=int)
    parser.add_argument("--count-actual", type=int)
    parser.add_argument("--npc-before", type=str, default="")
    parser.add_argument("--npc-after", type=str, default="")
    parser.add_argument("--balance-before", type=str, default="")
    parser.add_argument("--balance-after", type=str, default="")
    parser.add_argument("--grip-method", type=str, default="manual",
                        choices=["manual", "auto"])
    parser.add_argument("--blood-bar-method", type=str, default="passive",
                        choices=["passive", "active"])
    parser.add_argument("--mirror-active", action="store_true")
    parser.add_argument("--mode-used", action="store_true")
    parser.add_argument("--commands-used", type=str, default="")
    parser.add_argument("--screenshots", type=str, default="",
                        help="Comma-separated screenshot paths")
    parser.add_argument("--npc-checked-at", type=str, default="",
                        help="Comma-separated checkpoint counts (e.g. 40,45,49,50)")
    parser.add_argument("--duration-min", type=float, default=0.0)
    parser.add_argument("--interpretation", type=str, default="",
                        help="Analyst interpretation of the result")
    parser.add_argument("--tester", type=str, default="manual")
    args = parser.parse_args()

    csp = make_model()
    eng = make_engine(csp)
    tracker = CoverageTracker(OUT_DIR)
    dispatcher = MultiAgentDispatcher(OUT_DIR, max_agents=4)

    if args.mode == "list":
        cmd_list(tracker, args)
    elif args.mode == "priorities":
        cmd_priorities(tracker, eng, args)
    elif args.mode == "next":
        cmd_next(tracker, args)
    elif args.mode == "coverage":
        cmd_coverage(tracker, args)
    elif args.mode == "dispatch":
        cmd_dispatch(tracker, eng, dispatcher, args)
    elif args.mode == "report":
        cmd_report(args)
    elif args.mode == "csp":
        cmd_csp(eng, args)
    elif args.mode == "generate":
        cmd_generate(tracker, args)
    elif args.mode == "simulate":
        cmd_simulate(args)
    elif args.mode == "record":
        cmd_record(tracker, args)
    elif args.mode == "run":
        cmd_run_interactive(tracker, args)


if __name__ == "__main__":
    main()
