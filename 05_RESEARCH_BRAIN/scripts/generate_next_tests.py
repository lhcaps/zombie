#!/usr/bin/env python3
"""
generate_next_tests.py — Generate test protocols for top hypotheses.

Usage:
    python generate_next_tests.py
    python generate_next_tests.py --top-n 3
    python generate_next_tests.py --hypothesis-id HYP-CHAR_MIRROR-001
"""
from __future__ import annotations

import argparse
import json

from core import (
    RB_DIR, hypothesis_board_path, claim_ledger_path, source_registry_path,
    test_protocols_dir, next_protocol_id, utc_now, section, subsection, bullet, info, ok, warn,
    load_json, save_json, load_prompt,
)


DEFAULT_HARD_RULES = [
    "exactly_one_gender_reroll",
    "same_gender_targets_after_reroll",
    "passive_blood_bar_method",
    "manual_grip_zombification",
    "no_return_die_invade_commands",
    "no_volt_mode_required",
    "any_race_non_unique_targets",
    "zombies_do_not_need_to_act",
]


def _load_hard_constraints(ledger: dict) -> list[str]:
    """Extract hard constraint texts from claims."""
    hard_texts = []
    for c in ledger.get("claims", []):
        if c.get("type") == "hard_constraint" and c.get("status") != "deprecated":
            hard_texts.append(c["claim"])
    return hard_texts


def _load_evidence_for_hypothesis(hyp_id: str, ledger: dict, registry: dict) -> str:
    """Build evidence context for a hypothesis."""
    board = load_json(hypothesis_board_path())
    hypotheses = board.get("hypotheses", [])
    hyp = next((h for h in hypotheses if h["hypothesis_id"] == hyp_id), None)
    if not hyp:
        return ""

    lines = [f"## Hypothesis: {hyp['title']}"]
    lines.append(f"ID: {hyp['hypothesis_id']}")
    lines.append(f"Status: {hyp['status']}")
    lines.append(f"Summary: {hyp['summary']}")
    lines.append("")

    # Supporting claims
    lines.append("### Supporting Claims")
    supporting = hyp.get("supporting_claims", [])
    for claim_id in supporting:
        for c in ledger.get("claims", []):
            if c["claim_id"] == claim_id:
                src = next(
                    (s["title"] for s in registry.get("sources", []) if s["source_id"] == c["source_id"]),
                    c["source_id"]
                )
                lines.append(f"- [{claim_id}] {c['claim']} (source: {src}, confidence: {c['confidence']:.2f})")
    lines.append("")

    # Contradicting claims
    contradicting = hyp.get("contradicting_claims", [])
    if contradicting:
        lines.append("### Contradicting Claims")
        for claim_id in contradicting:
            for c in ledger.get("claims", []):
                if c["claim_id"] == claim_id:
                    lines.append(f"- [{claim_id}] {c['claim']}")
        lines.append("")

    # Unknowns
    lines.append("### Open Questions")
    for uq in hyp.get("unknowns", []):
        lines.append(f"- ? {uq}")
    lines.append("")

    return "\n".join(lines)


def _generate_protocol_content(hyp: dict, evidence: str, hard_constraints: list[str]) -> dict:
    """Generate a structured test protocol for a hypothesis."""
    protocol_id = next_protocol_id()
    hyp_id = hyp["hypothesis_id"]
    count_candidates = [40, 45, 49, 50]
    gender = "F"  # Can be parameterized

    # Build required conditions string
    req_conditions = "\n".join(f"- {c}" for c in hyp.get("required_conditions", []))

    # Build steps based on hypothesis type
    if "CHAR_MIRROR" in hyp_id or "BC_GENDER" in hyp_id or "APP_COPY" in hyp_id:
        steps = _build_mirror_steps(count_candidates)
    elif "PASSIVE" in hyp_id:
        steps = _build_passive_steps(count_candidates)
    elif "COMMANDS" in hyp_id:
        steps = _build_command_steps(count_candidates)
    else:
        steps = _build_count_only_steps(count_candidates)

    protocol = {
        "protocol_id": protocol_id,
        "hypothesis_id": hyp_id,
        "goal": f"Test whether {hyp['title']} is the correct tail mechanic.",
        "hypothesis_summary": hyp["summary"][:200],
        "required_conditions": hyp.get("required_conditions", []),
        "controlled_variables": [
            "race = Soul Reaper (or any)",
            "server = private",
            "world = base",
            "no Volt mode",
            "no commands (return/die/invade)",
        ],
        "tested_variables": [
            "count threshold (40, 45, 49, 50)",
            "character mirror activation timing",
            "same-gender zombification",
        ],
        "steps": steps,
        "record_fields": {
            "npc_dialogue_before": True,
            "npc_dialogue_after": True,
            "gender_changes": True,
            "race_changes": True,
            "balance_before": True,
            "balance_after": True,
            "blood_bar_state": True,
            "count_progress": True,
            "screenshots": True,
            "video": False,
            "game_version": True,
            "server_type": True,
        },
        "pass_condition": "NPC dialogue indicates quest completion or significant progress. Balance/appearance changes match expected outcome for this mechanic.",
        "fail_condition": "NPC dialogue unchanged after completing all steps. No progress indicator. Route fails to advance.",
        "inconclusive_condition": "Test interrupted mid-execution. Wrong character state used. Checkpoint missed. Ambiguous NPC response.",
        "common_mistakes": [
            "Using auto-grip instead of manual grip",
            "Wrong gender target selected after reroll",
            "Missing NPC checkpoint at milestones",
            "Activating mirror before passive Blood Bar is built",
            "Server reset during test invalidates state",
        ],
        "follow_up_on_pass": "Test with opposite gender. Test with different count. Generate next tail mechanic test.",
        "follow_up_on_fail": "Reduce count and retest. Try simpler tail mechanic. Fall back to next hypothesis.",
        "created_at": utc_now(),
        "_evidence_context": evidence[:1000],
    }
    return protocol


def _build_mirror_steps(counts: list[int]) -> list[dict]:
    steps = [
        {
            "step_number": 1, "phase": "preparation", "action": "Create new character. Enter game. Locate quest NPC.",
            "what_to_record": "Character name, race, starting gender, server type, NPC dialogue before quest start.",
            "checkpoint": True, "optional": False,
        },
        {
            "step_number": 2, "phase": "gender_reroll", "action": "Perform exactly ONE gender reroll using in-game method.",
            "what_to_record": "Gender before and after reroll. Confirm only one reroll used.",
            "checkpoint": True, "optional": False,
        },
        {
            "step_number": 3, "phase": "passive_blood_bar", "action": "Build passive Blood Bar by waiting/playing naturally. Do NOT use commands.",
            "what_to_record": "Blood bar state before building. Time spent. Method used.",
            "checkpoint": False, "optional": False,
        },
        {
            "step_number": 4, "phase": "target_selection", "action": "Select same-gender targets. Targets can be any race, non-unique.",
            "what_to_record": "Target genders confirmed match post-reroll gender. Target races noted.",
            "checkpoint": False, "optional": False,
        },
        {
            "step_number": 5, "phase": "checkpoint_40", "action": f"Perform {counts[0]} same-gender manual-grip zombifications. Check NPC at count {counts[0]}.",
            "what_to_record": f"NPC dialogue at count {counts[0]}. Balance before and after. Any changes noted.",
            "checkpoint": True, "optional": True,
        },
        {
            "step_number": 6, "phase": "checkpoint_45", "action": f"Continue to {counts[1]} total. Check NPC at count {counts[1]}.",
            "what_to_record": f"NPC dialogue at count {counts[1]}. Balance before and after.",
            "checkpoint": True, "optional": True,
        },
        {
            "step_number": 7, "phase": "checkpoint_49", "action": f"Continue to {counts[2]} total. Check NPC at count {counts[2]}.",
            "what_to_record": f"NPC dialogue at count {counts[2]}. Balance before and after.",
            "checkpoint": True, "optional": True,
        },
        {
            "step_number": 8, "phase": "mirror_activation", "action": "Activate character mirror/copy mechanic. Use appropriate action to trigger appearance copy.",
            "what_to_record": "Character appearance before and after activation. Any NPC dialogue triggered.",
            "checkpoint": True, "optional": False,
        },
        {
            "step_number": 9, "phase": "final_zombify", "action": f"Perform final zombification to reach {counts[3]} total while mirror is active. Check NPC immediately after.",
            "what_to_record": f"NPC dialogue at count {counts[3]} with mirror active. Final balance. Character appearance state.",
            "checkpoint": True, "optional": False,
        },
        {
            "step_number": 10, "phase": "verification", "action": "Record final state. Document NPC response. Take screenshots of key moments.",
            "what_to_record": "Complete NPC dialogue log. All screenshots. Final character state.",
            "checkpoint": True, "optional": False,
        },
    ]
    return steps


def _build_passive_steps(counts: list[int]) -> list[dict]:
    steps = [
        {
            "step_number": 1, "phase": "preparation", "action": "Create new character. Enter game. Locate quest NPC.",
            "what_to_record": "Character state, NPC dialogue before quest.",
            "checkpoint": True, "optional": False,
        },
        {
            "step_number": 2, "phase": "gender_reroll", "action": "Perform exactly ONE gender reroll.",
            "what_to_record": "Gender before/after.",
            "checkpoint": True, "optional": False,
        },
        {
            "step_number": 3, "phase": "passive_accumulation", "action": "Build passive Blood Bar threshold. Monitor blood bar fill carefully.",
            "what_to_record": "Blood bar level at each 10% increment. Time to reach threshold.",
            "checkpoint": True, "optional": False,
        },
        {
            "step_number": 4, "phase": "manual_grip_count", "action": f"Perform {counts[3]} manual-grip same-gender zombifications. Keep blood bar passive.",
            "what_to_record": f"NPC at count {counts[3]}. Blood bar state throughout.",
            "checkpoint": True, "optional": False,
        },
        {
            "step_number": 5, "phase": "verification", "action": "Record final state. Document NPC response.",
            "what_to_record": "NPC dialogue. Balance. All screenshots.",
            "checkpoint": True, "optional": False,
        },
    ]
    return steps


def _build_count_only_steps(counts: list[int]) -> list[dict]:
    steps = [
        {
            "step_number": 1, "phase": "preparation", "action": "Create new character. Enter game. Locate quest NPC.",
            "what_to_record": "Character state, NPC dialogue before quest.",
            "checkpoint": True, "optional": False,
        },
        {
            "step_number": 2, "phase": "gender_reroll", "action": "Perform exactly ONE gender reroll.",
            "what_to_record": "Gender before/after.",
            "checkpoint": True, "optional": False,
        },
        {
            "step_number": 3, "phase": "passive_blood_bar", "action": "Build passive Blood Bar. Use manual grip for zombification.",
            "what_to_record": "Blood bar state. Grip method confirmed manual.",
            "checkpoint": False, "optional": False,
        },
        {
            "step_number": 4, "phase": "checkpoint_40", "action": f"Zombify {counts[0]} same-gender targets. Check NPC.",
            "what_to_record": f"NPC at count {counts[0]}.",
            "checkpoint": True, "optional": True,
        },
        {
            "step_number": 5, "phase": "checkpoint_45", "action": f"Continue to {counts[1]}. Check NPC.",
            "what_to_record": f"NPC at count {counts[1]}.",
            "checkpoint": True, "optional": True,
        },
        {
            "step_number": 6, "phase": "checkpoint_49", "action": f"Continue to {counts[2]}. Check NPC.",
            "what_to_record": f"NPC at count {counts[2]}.",
            "checkpoint": True, "optional": True,
        },
        {
            "step_number": 7, "phase": "final_check", "action": f"Zombify to reach {counts[3]} total. Check NPC.",
            "what_to_record": f"NPC at count {counts[3]}. No tail mechanic.",
            "checkpoint": True, "optional": False,
        },
    ]
    return steps


def _build_command_steps(counts: list[int]) -> list[dict]:
    steps = [
        {
            "step_number": 1, "phase": "preparation", "action": "Create new character. Enter game. Locate quest NPC.",
            "what_to_record": "Character state, NPC dialogue before quest.",
            "checkpoint": True, "optional": False,
        },
        {
            "step_number": 2, "phase": "gender_reroll", "action": "Perform exactly ONE gender reroll.",
            "what_to_record": "Gender before/after.",
            "checkpoint": True, "optional": False,
        },
        {
            "step_number": 3, "phase": "zombify_count", "action": f"Zombify {counts[3]} same-gender targets with manual grip.",
            "what_to_record": f"NPC at count {counts[3]} before commands.",
            "checkpoint": True, "optional": False,
        },
        {
            "step_number": 4, "phase": "command_sequence", "action": "Execute return command, then die command in sequence.",
            "what_to_record": "NPC response after each command. Any dialogue triggered.",
            "checkpoint": True, "optional": False,
        },
        {
            "step_number": 5, "phase": "verification", "action": "Record final state. Document NPC response.",
            "what_to_record": "NPC dialogue. Balance. Screenshots.",
            "checkpoint": True, "optional": False,
        },
    ]
    return steps


def generate_protocols(top_n: int = 3, focused_id: str | None = None) -> list[dict]:
    """Generate test protocols for top hypotheses."""
    board = load_json(hypothesis_board_path())
    hypotheses = board.get("hypotheses", [])
    ledger = load_json(claim_ledger_path())
    registry = load_json(source_registry_path())
    hard_constraints = _load_hard_constraints(ledger)

    if focused_id:
        target = next((h for h in hypotheses if h["hypothesis_id"] == focused_id), None)
        if not target:
            warn(f"Hypothesis not found: {focused_id}")
            return []
        hypotheses = [target]
    else:
        # Sort active hypotheses by priority
        active = [h for h in hypotheses if h.get("status") == "active"]
        active.sort(key=lambda h: h.get("priority_score", 0), reverse=True)
        hypotheses = active[:top_n]

    section("Generate Test Protocols")
    protocols = []

    for hyp in hypotheses:
        if hyp.get("constraint_fit", 1.0) < 1.0:
            info(f"Skipping {hyp['hypothesis_id']} — constraint_fit = 0 (blocked)")
            continue

        subsection(f"{hyp['hypothesis_id']}: {hyp['title']}")
        evidence = _load_evidence_for_hypothesis(hyp["hypothesis_id"], ledger, registry)
        protocol = _generate_protocol_content(hyp, evidence, hard_constraints)

        # Save protocol
        proto_path = test_protocols_dir() / f"{protocol['protocol_id']}.json"
        save_json(proto_path, protocol)
        ok(f"Saved {protocol['protocol_id']} -> {proto_path.relative_to(RB_DIR)}")

        # Update hypothesis with protocol ID
        for h in board.get("hypotheses", []):
            if h["hypothesis_id"] == hyp["hypothesis_id"]:
                h["test_protocol_id"] = protocol["protocol_id"]
        protocols.append(protocol)

        # Print summary
        print(f"\n  Protocol: {protocol['protocol_id']}")
        print(f"  Goal: {protocol['goal']}")
        print(f"  Steps: {len(protocol['steps'])}")
        print(f"  Checkpoints: {sum(1 for s in protocol['steps'] if s.get('checkpoint'))}")
        print(f"  PASS: {protocol['pass_condition'][:80]}")
        print(f"  FAIL: {protocol['fail_condition'][:80]}")

    save_json(hypothesis_board_path(), board)
    ok(f"Generated {len(protocols)} protocol(s)")

    return protocols


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate test protocols for top hypotheses")
    parser.add_argument("--top-n", type=int, default=3, help="Generate protocols for top N hypotheses")
    parser.add_argument("--hypothesis-id", type=str, help="Generate protocol for specific hypothesis")
    args = parser.parse_args()
    generate_protocols(args.top_n, args.hypothesis_id)


if __name__ == "__main__":
    main()
