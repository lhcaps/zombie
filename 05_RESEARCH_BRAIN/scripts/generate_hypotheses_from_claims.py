#!/usr/bin/env python3
"""
generate_hypotheses_from_claims.py — Generate candidate hypotheses from an evidence pack + claims.

This is the critical bridge: evidence pack → candidate hypotheses → ranked board.

Usage:
    python generate_hypotheses_from_claims.py --evidence-pack ../evidence_packs/EPACK-2ISH-001.json --out ../data/hypothesis_candidates.json
    python generate_hypotheses_from_claims.py --evidence-pack ../evidence_packs/EPACK-001.json --generate-protocol --out ../data/hyp_candidates.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from core import RB_DIR, next_hypothesis_id, utc_now, load_json, save_json


_MECHANICS_ONTOLOGY = {
    "actions": ["grip", "grab", "execute", "zombify", "check_npc", "reroll", "mirror", "copy"],
    "states": ["gender", "mirror_active", "blood_bar", "mode", "volt", "appearance_copy"],
    "inputs": ["T", "G", "Z", "X", "C", "M2", "critical", "passive", "mode"],
    "relations": ["same_gender", "opposite_gender", "copy", "mirror", "target", "partner"],
    "counts": [40, 45, 49, 50],
}


def _call_llm(prompt: str, system: str = "") -> str | None:
    try:
        import os
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None
    except Exception:
        return None

    try:
        import openai
        client = openai.OpenAI()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(model="gpt-4o", messages=messages, temperature=0.1)
        return resp.choices[0].message.content
    except Exception:
        pass

    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-7-latest",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text
    except Exception as e:
        sys.stderr.write(f"[WARN] LLM call failed: {e}\n")
        return None


def _parse_hypotheses_from_response(response: str, existing_hyps: list[dict]) -> list[dict]:
    hypotheses = []

    json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(1))
            if isinstance(parsed, list):
                for item in parsed:
                    hypotheses.append(item)
        except json.JSONDecodeError:
            pass

    block_pattern = re.compile(
        r"TITLE:\s*(.*?)\nSUMMARY:\s*(.*?)\n(?:CONDITIONS:\s*(.*?)\n)?"
        r"(?:SUPPORTING:\s*(.*?)\n)?(?:UNKNOWN:\s*(.*?)\n)?",
        re.DOTALL | re.IGNORECASE,
    )
    for m in block_pattern.finditer(response):
        hypotheses.append({
            "title": m.group(1).strip(),
            "summary": m.group(2).strip(),
            "required_conditions": [c.strip() for c in m.group(3).split(",") if c.strip()] if m.group(3) else [],
            "supporting_claims": [c.strip() for c in m.group(4).split(",") if c.strip()] if m.group(4) else [],
            "unknowns": [u.strip() for u in m.group(5).split(",") if u.strip()] if m.group(5) else [],
        })

    return hypotheses


def _build_hypothesis(
    item: dict,
    hyp_id: str,
    evidence_pack_id: str,
    existing_hyps: list[dict],
    ontology: dict,
) -> dict:
    conditions = item.get("required_conditions", [])
    supporting = item.get("supporting_claims", [])
    unknowns = item.get("unknowns", [])

    test_cost = 3
    if len(conditions) > 5:
        test_cost += 1
    if "bankai" in " ".join(conditions).lower() or "volt" in " ".join(conditions).lower():
        test_cost += 1

    risk = 2
    if "unverified" in " ".join(unknowns).lower():
        risk += 1

    # Multi-axis scoring (game mechanic research specific)
    evidence_support = 0.1
    if supporting:
        evidence_support = min(0.8, 0.1 + len(supporting) * 0.15)
    if item.get("evidence"):
        evidence_support = min(0.9, evidence_support + 0.2)

    contradiction_risk = 0.5
    if any(h.get("status") in ("rejected", "deprecated") for h in existing_hyps):
        contradiction_risk = 0.6
    if "unverified" in " ".join(unknowns).lower():
        contradiction_risk = min(0.9, contradiction_risk + 0.2)

    novelty = 0.5
    if len(conditions) >= 4:
        novelty = 0.7
    if unknowns:
        novelty = min(0.9, novelty + 0.1)

    testability = 0.6
    if len(conditions) <= 3:
        testability = 0.8
    if len(conditions) > 7:
        testability = 0.3

    mechanic_plausibility = 0.5
    cond_text = " ".join(conditions).lower()
    if any(t in cond_text for t in ontology["actions"]):
        mechanic_plausibility = 0.7
    if any(s in cond_text for s in ontology["states"]):
        mechanic_plausibility = min(0.85, mechanic_plausibility + 0.1)

    likelihood = 0.1
    if supporting:
        likelihood = min(0.7, 0.1 + len(supporting) * 0.1)

    return {
        "hypothesis_id": hyp_id,
        "title": item.get("title", "Unnamed Hypothesis"),
        "summary": item.get("summary", ""),
        "required_conditions": conditions,
        "supporting_claims": supporting,
        "contradicting_claims": [],
        "unknowns": unknowns,
        "test_cost": test_cost,
        "risk": risk,
        "likelihood": likelihood,
        "expected_info_gain": 2.0,
        "evidence_fit": 0.5,
        "constraint_fit": 1.0,
        # Multi-axis scoring
        "evidence_support": round(evidence_support, 3),
        "contradiction_risk": round(contradiction_risk, 3),
        "novelty": round(novelty, 3),
        "testability": round(testability, 3),
        "mechanic_plausibility": round(mechanic_plausibility, 3),
        # Final score (weighted combination of multi-axis)
        "priority_score": 0.0,
        "status": "active",
        "test_protocol_id": None,
        "last_tested_at": None,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "notes": f"Generated from evidence pack: {evidence_pack_id}",
        "evidence_pack_id": evidence_pack_id,
    }


def _critique_hypothesis(hyp: dict, existing_hyps: list[dict]) -> dict:
    critiques: list[str] = []

    summary_lower = hyp.get("summary", "").lower()
    title_lower = hyp.get("title", "").lower()

    if not hyp.get("supporting_claims"):
        critiques.append("No supporting claims — generates only from inference")
        hyp["evidence_fit"] = max(0.0, hyp.get("evidence_fit", 0.5) - 0.2)
        hyp["evidence_support"] = max(0.0, hyp.get("evidence_support", 0.1) - 0.2)

    if any(
        vague in summary_lower
        for vague in [
            "maybe", "possibly", "might be", "could be", "perhaps",
            "some kind of", "somehow", "some mechanism",
        ]
    ):
        critiques.append("Contains vague language — hypothesis too speculative")
        hyp["evidence_fit"] = max(0.0, hyp.get("evidence_fit", 0.5) - 0.15)
        hyp["mechanic_plausibility"] = max(0.0, hyp.get("mechanic_plausibility", 0.5) - 0.15)

    for existing in existing_hyps:
        if existing.get("status") in ("rejected", "deprecated"):
            existing_conds = set(existing.get("required_conditions", []))
            new_conds = set(hyp.get("required_conditions", []))
            overlap = existing_conds & new_conds
            if len(overlap) >= 3:
                for cond in overlap:
                    if any(
                        hard in cond.lower()
                        for hard in [
                            "no_volt", "no_mode", "no_command",
                            "exactly_one_gender", "same_gender",
                        ]
                    ):
                        critiques.append(
                            f"Contradicts rejected hypothesis {existing['hypothesis_id']}: "
                            f"shares {overlap}"
                        )
                        hyp["constraint_fit"] = max(0.0, hyp.get("constraint_fit", 1.0) - 0.3)
                        hyp["contradiction_risk"] = min(1.0, hyp.get("contradiction_risk", 0.5) + 0.3)

    conditions = hyp.get("required_conditions", [])
    if not conditions or len(conditions) < 2:
        critiques.append("Too few required conditions — hypothesis lacks specificity")
        hyp["evidence_fit"] = max(0.0, hyp.get("evidence_fit", 0.5) - 0.1)
        hyp["testability"] = max(0.0, hyp.get("testability", 0.6) - 0.2)

    # Multi-axis priority score
    # = (evidence_support * constraint_fit * mechanic_plausibility * novelty)
    #   / (test_cost * (1 + contradiction_risk))
    ev = hyp.get("evidence_support", 0.1)
    cf = hyp.get("constraint_fit", 1.0)
    pl = hyp.get("mechanic_plausibility", 0.5)
    nv = hyp.get("novelty", 0.5)
    cr = hyp.get("contradiction_risk", 0.5)
    tc = max(hyp.get("test_cost", 3), 1)

    priority = (ev * cf * pl * nv) / (tc * (1.0 + cr))
    hyp["priority_score"] = round(priority, 4)

    if critiques:
        hyp["notes"] = hyp.get("notes", "") + " | Critic flags: " + "; ".join(critiques)

    return hyp


def _generate_with_llm(
    question: str,
    chunks: list[dict],
    existing_hyps: list[dict],
    ontology: dict,
) -> list[dict]:
    system_prompt = (
        "You are a game mechanics research analyst. "
        "Generate candidate solution hypotheses for the Zombie Almighty quest. "
        "Each hypothesis must include: title, summary, required_conditions (array), "
        "supporting_claims (array, can be empty), unknowns (array). "
        "Hypotheses must be specific and testable. "
        "Avoid vague language like 'maybe', 'possibly'. "
        "Each hypothesis should describe an exact mechanism or sequence. "
        "Output as JSON array of hypothesis objects."
    )

    chunks_text = "\n\n".join(
        f"[{c.get('card_name', 'unknown')}] ({c.get('list_name', '')}): {c.get('text', '')[:400]}"
        for c in chunks[:15]
    )

    existing_hyps_text = ""
    if existing_hyps:
        existing_hyps_text = "\n\n## Existing Hypotheses (do not duplicate)\n"
        for h in existing_hyps[:5]:
            existing_hyps_text += f"- {h['hypothesis_id']}: {h['title']} ({h['status']})\n"

    prompt = f"""Generate candidate hypotheses for this research question:

QUESTION: {question}

{existing_hyps_text}

EVIDENCE (top {min(len(chunks), 15)} chunks):
{chunks_text}

ONTOLOGY (game terms):
- Actions: {', '.join(ontology['actions'])}
- States: {', '.join(ontology['states'])}
- Inputs: {', '.join(ontology['inputs'])}
- Relations: {', '.join(ontology['relations'])}
- Known counts: {ontology['counts']}

Generate 3-8 hypotheses. Each must be:
1. Specific: describe exact steps/mechanics
2. Testable: can be verified with game actions
3. Distinct: different from each other and existing hypotheses
4. Evidence-backed: cite the card/entity that suggests it

Output as JSON array:
```json
[
  {{
    "title": "...",
    "summary": "...",
    "required_conditions": ["cond1", "cond2"],
    "supporting_claims": ["claim_id_if_available"],
    "unknowns": ["what_is_unknown"]
  }}
]
```
"""

    response = _call_llm(prompt, system_prompt)
    if not response:
        sys.stderr.write("[WARN] No LLM response — using template hypotheses\n")
        return _generate_template_hypotheses(question, chunks, existing_hyps, ontology)

    raw_hyps = _parse_hypotheses_from_response(response, existing_hyps)
    return raw_hyps


def _generate_template_hypotheses(
    question: str,
    chunks: list[dict],
    existing_hyps: list[dict],
    ontology: dict,
) -> list[dict]:
    templates = [
        {
            "title": "Character Mirror + Same-Gender Count",
            "summary": (
                "Activate character copy/mirror relation, then perform exact count "
                "of same-gender zombifications. Mirror must be active before NPC check."
            ),
            "required_conditions": [
                "exactly_one_gender_reroll",
                "same_gender_targets",
                "manual_grip",
                "passive_blood_bar",
                "character_mirror_activated_before_count",
                "final_check_while_mirror_active",
            ],
            "supporting_claims": [],
            "unknowns": [
                "What exact count? (40/45/49/50)",
                "Does mirror need to persist through count?",
                "NPC check timing?",
            ],
        },
        {
            "title": "Passive Blood Bar Threshold + Count",
            "summary": (
                "Build passive Blood Bar to threshold while performing manual grip count. "
                "Both Blood Bar level and grip count must reach threshold simultaneously."
            ),
            "required_conditions": [
                "exactly_one_gender_reroll",
                "passive_blood_bar_threshold",
                "grip_count_at_threshold",
                "same_gender_targets",
            ],
            "supporting_claims": [],
            "unknowns": [
                "Blood Bar threshold level?",
                "Grip count threshold? (40/45/49/50)",
                "Can they be independent?",
            ],
        },
        {
            "title": "Appearance Copy + Gender Pair",
            "summary": (
                "Copy character appearance (bc rule), then zombify same-gender targets "
                "matching the copied appearance. Gender pair relationship is key."
            ),
            "required_conditions": [
                "exactly_one_gender_reroll",
                "appearance_copy_before_zombify",
                "bc_entity_matches_copied_appearance",
                "same_gender_pair_targets",
                "final_npc_check_with_appearance_copy_active",
            ],
            "supporting_claims": [],
            "unknowns": [
                "How is appearance copy triggered?",
                "Is gender determined by copy or reroll?",
                "NPC check timing?",
            ],
        },
    ]
    return templates


def generate_hypotheses(
    question: str,
    evidence_pack_path: Path,
    out_path: Path,
    add_to_board: bool = False,
    board_list: str | None = None,
    idempotency_key: str | None = None,
) -> list[dict]:
    pack = json.loads(evidence_pack_path.read_text(encoding="utf-8"))
    chunks = pack.get("chunks", [])

    existing_hyps = []
    board_path = RB_DIR / "hypothesis_board.json"
    if board_path.exists():
        board = json.loads(board_path.read_text(encoding="utf-8"))
        existing_hyps = board.get("hypotheses", [])

    print(f"Generating hypotheses for question: {question[:80]}...")
    print(f"  Existing hypotheses: {len(existing_hyps)}")

    raw_hyps = _generate_with_llm(question, chunks, existing_hyps, _MECHANICS_ONTOLOGY)

    hypotheses = []
    for item in raw_hyps:
        hyp_id = next_hypothesis_id(existing_hyps + hypotheses)
        hyp = _build_hypothesis(
            item, hyp_id, pack.get("pack_id", "UNKNOWN"), existing_hyps, _MECHANICS_ONTOLOGY
        )
        hyp = _critique_hypothesis(hyp, existing_hyps)
        hypotheses.append(hyp)

    hypotheses.sort(key=lambda h: h["priority_score"], reverse=True)

    print(f"  Generated {len(hypotheses)} hypotheses")
    for h in hypotheses:
        print(f"  [{h['hypothesis_id']}] {h['title'][:60]} (score: {h['priority_score']:.4f}, status: {h['status']})")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "question": question,
        "evidence_pack_id": pack.get("pack_id"),
        "generated_at": utc_now(),
        "hypotheses": hypotheses,
    }
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    if add_to_board and hypotheses:
        board_path = RB_DIR / "hypothesis_board.json"
        if board_path.exists():
            board = json.loads(board_path.read_text(encoding="utf-8"))
        else:
            board = {"version": "1.0", "created_at": utc_now(), "hypotheses": [], "lists": {}}

        # Ensure lists structure exists
        if "lists" not in board:
            board["lists"] = {}
        if "hypotheses" not in board:
            board["hypotheses"] = []

        # Idempotency: check if this idempotency_key already exists
        if idempotency_key:
            existing = [h for h in board["hypotheses"]
                        if h.get("evidence_pack_id") == idempotency_key]
            if existing:
                print(f"  [SKIP] Idempotency key '{idempotency_key}' already on board "
                      f"({len(existing)} hypotheses). Use new --idempotency-key to update.")
                return hypotheses

        # Assign to list
        list_name = board_list or "Research Output"
        if list_name not in board["lists"]:
            board["lists"][list_name] = {"description": "", "created_at": utc_now()}

        existing_ids = {h["hypothesis_id"] for h in board["hypotheses"]}
        added = 0
        for h in hypotheses:
            if h["hypothesis_id"] not in existing_ids:
                h["board_list"] = list_name
                if idempotency_key:
                    h["evidence_pack_id"] = idempotency_key
                board["hypotheses"].append(h)
                added += 1

        save_json(board_path, board)
        print(f"[OK] Added {added} hypotheses to hypothesis_board.json "
              f"(list: '{list_name}')")
    else:
        print(f"  [DRY RUN] Not writing to hypothesis_board.json "
              f"(use --add-to-board --idempotency-key to commit)")

    return hypotheses


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate candidate hypotheses from an evidence pack"
    )
    parser.add_argument(
        "--evidence-pack", "-e", required=True,
        help="Path to evidence pack JSON"
    )
    parser.add_argument(
        "--question", "-q",
        help="Research question (overrides pack question if provided)"
    )
    parser.add_argument(
        "--out", "-o", required=True,
        help="Output path for hypothesis candidates JSON"
    )
    parser.add_argument(
        "--add-to-board", action="store_true",
        help="Also append hypotheses to hypothesis_board.json"
    )
    parser.add_argument(
        "--board-list",
        default="Research Output",
        help="Trello list name for board mutation (default: 'Research Output')"
    )
    parser.add_argument(
        "--idempotency-key",
        help="Unique key for idempotent board writing (e.g. EPACK-2ISH-001)"
    )
    args = parser.parse_args()

    pack_path = Path(args.evidence_pack)
    if not pack_path.exists():
        sys.stderr.write(f"[ERROR] Evidence pack not found: {pack_path}\n")
        sys.exit(1)

    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    question = args.question or pack.get("question", "Unknown question")

    generate_hypotheses(
        question, pack_path, Path(args.out),
        add_to_board=args.add_to_board,
        board_list=args.board_list,
        idempotency_key=args.idempotency_key,
    )
    print(f"[OK] Wrote hypotheses to {args.out}")


if __name__ == "__main__":
    main()
