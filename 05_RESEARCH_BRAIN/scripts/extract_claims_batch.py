#!/usr/bin/env python3
"""
extract_claims_batch.py — Extract atomic claims from an evidence pack.

Reads chunks from an evidence pack and generates structured claims
for the claim ledger.

Usage:
    python extract_claims_batch.py --pack ../evidence_packs/EPACK-2ISH-001.json --out ../indexes/trello_claim_candidates.jsonl
    python extract_claims_batch.py --pack ../evidence_packs/EPACK-001.json --out ../indexes/claims.jsonl --interactive
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import RB_DIR, next_claim_id, utc_now, load_json, save_json


_CLAIM_TYPES = [
    "hard_constraint",
    "soft_constraint",
    "observation",
    "passed_test",
    "failed_test",
    "rumor",
    "inference",
    "deprecated_path",
]


_MECHANICS_TAGS = [
    "zombie_mechanic",
    "blood_mechanic",
    "grip_mechanic",
    "gender_mechanic",
    "appearance_mechanic",
    "mirror_mechanic",
    "count_mechanic",
    "quest_mechanic",
    "tail_mechanic",
    "reroll_mechanic",
    "ability_keys",
    "bankai_mechanic",
    "schrift_mechanic",
    "element_mechanic",
]


def _parse_claims_from_llm_response(
    response: str,
    source_prefix: str,
    existing_claims: list[dict],
) -> list[dict]:
    claims = []

    json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(1))
            if isinstance(parsed, list):
                for item in parsed:
                    claim_text = item.get("claim", item.get("text", ""))
                    if claim_text:
                        claims.append({
                            "claim": claim_text.strip(),
                            "type": item.get("type", "observation"),
                            "confidence": float(item.get("confidence", 0.5)),
                            "evidence": item.get("evidence", ""),
                            "tags": item.get("tags", []),
                            "polarity": item.get("polarity", "neutral"),
                        })
        except json.JSONDecodeError:
            pass

    block_pattern = re.compile(
        r"CLAIM:\s*(.*?)\nTYPE:\s*(\w+)\s*\nCONFIDENCE:\s*([\d.]+)\s*\n(?TAGS:.*?)?(?=\n\n|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    for m in block_pattern.finditer(response):
        claim_text = m.group(1).strip()
        if claim_text:
            claims.append({
                "claim": claim_text,
                "type": m.group(2).strip().lower(),
                "confidence": float(m.group(3)),
                "evidence": "",
                "tags": [],
                "polarity": "neutral",
            })

    return claims


def _infer_tags(text: str) -> list[str]:
    tags = []
    text_lower = text.lower()

    tag_map = {
        "zombie_mechanic": ["zombie", "zombify", "charred", "undead", "ghoul"],
        "blood_mechanic": ["blood", "blood bar", "blood meter"],
        "grip_mechanic": ["grip", "grab", "execute", "gripping"],
        "gender_mechanic": ["gender", "male", "female", "reroll"],
        "appearance_mechanic": ["appearance", "copy", "mirror", "vanity", "transform"],
        "mirror_mechanic": ["mirror", "character mirror", "bc", "xy"],
        "count_mechanic": ["count", "40", "45", "49", "50", "amount"],
        "quest_mechanic": ["quest", "npc", "check", "obtainment", "complete"],
        "tail_mechanic": ["tail", "two ish", "final"],
        "reroll_mechanic": ["reroll"],
        "ability_keys": ["critical", "passive", "bankai", "res", "volt", "shikai"],
        "bankai_mechanic": ["bankai"],
        "schrift_mechanic": ["schrift", "vollstandig", "resurreccion"],
        "element_mechanic": ["fire", "ice", "blood shikai"],
    }

    for tag, keywords in tag_map.items():
        if any(kw in text_lower for kw in keywords):
            tags.append(tag)

    return list(set(tags))


def _build_claims(
    raw_claims: list[dict],
    source_prefix: str,
    existing_claims: list[dict],
    chunks: list[dict],
) -> list[dict]:
    # Build lookup: text snippet -> entity_id for quote tracing
    text_to_entity: dict[str, str] = {}
    entity_by_card: dict[str, list[str]] = {}
    for chunk in chunks:
        eid = chunk.get("entity_id", "")
        card = chunk.get("card_name", "")
        text = chunk.get("text", "")
        if eid:
            text_to_entity[text[:100]] = eid
            if card not in entity_by_card:
                entity_by_card[card] = []
            entity_by_card[card].append(eid)

    new_claims = []
    for item in raw_claims:
        claim_text = item.get("claim", "")
        if not claim_text or len(claim_text) < 10:
            continue

        tags = item.get("tags", [])
        if not tags:
            tags = _infer_tags(claim_text)

        claim_type = item.get("type", "observation")
        if claim_type not in _CLAIM_TYPES:
            claim_type = "observation"

        # Trace entity IDs from chunks that contain claim-relevant text
        source_entity_ids: list[str] = []
        quote_spans: list[str] = []
        claim_lower = claim_text.lower()
        for chunk in chunks:
            chunk_text = chunk.get("text", "").lower()
            eid = chunk.get("entity_id", "")
            # Simple overlap: if claim keywords appear in chunk text
            keywords = [w for w in claim_lower.split() if len(w) > 4]
            overlap = sum(1 for kw in keywords if kw in chunk_text)
            if overlap >= 2 and eid and eid not in source_entity_ids:
                source_entity_ids.append(eid)
                # Extract a quote span: find the matching text snippet
                for kw in keywords[:3]:
                    idx = chunk.get("text", "").lower().find(kw)
                    if idx >= 0:
                        start = max(0, idx - 30)
                        end = min(len(chunk.get("text", "")), idx + len(kw) + 30)
                        span = chunk.get("text", "")[start:end].strip()
                        if span not in quote_spans:
                            quote_spans.append(span)
                        break

        claim_id = next_claim_id(existing_claims + new_claims)
        new_claims.append({
            "claim_id": claim_id,
            "source_id": source_prefix,
            "claim": claim_text.strip(),
            "type": claim_type,
            "polarity": item.get("polarity", "neutral"),
            "confidence": min(1.0, max(0.0, float(item.get("confidence", 0.5)))),
            "evidence": item.get("evidence", ""),
            "source_entity_ids": source_entity_ids,
            "quote_spans": quote_spans,
            "status": "pending_review",
            "contradicts": [],
            "supported_by": [],
            "tags": tags,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "notes": "",
        })

    return new_claims


def _call_llm(prompt: str, system: str = "", model: str = "gpt-4o") -> str | None:
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
        resp = client.chat.completions.create(model=model, messages=messages, temperature=0.05)
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


def _extract_from_chunks(pack: dict, existing_claims: list[dict]) -> list[dict]:
    system_prompt = (
        "You are a meticulous game mechanics researcher. "
        "Extract ONLY atomic, verifiable claims from the evidence chunks below. "
        "For each claim, infer its type (hard_constraint/soft_constraint/observation/inference/rumor). "
        "Assign a confidence score 0.0-1.0 based on how directly the text supports the claim. "
        "Tag claims with relevant mechanic tags from this list: "
        + ", ".join(_MECHANICS_TAGS) + ". "
        "Do NOT invent claims not supported by the text. "
        "Format output as a JSON array of claim objects with keys: "
        "claim, type, confidence, evidence, tags, polarity."
    )

    chunks_text = "\n\n---\n\n".join(
        f"CHUNK {c['chunk_id']} ({c['card_name']} / {c['list_name']}):\n{c['text']}"
        for c in pack.get("chunks", [])
    )

    prompt = f"""Extract atomic claims from the following Trello evidence chunks.

QUESTION BEING RESEARCHED: {pack.get('question', 'General')}

EVIDENCE CHUNKS:
{chunks_text}

Extract all specific, verifiable claims. For each, output a JSON object:
{{"claim": "...", "type": "...", "confidence": 0.0-1.0, "evidence": "...", "tags": [], "polarity": "positive"}}

Claim types:
- hard_constraint: proven game rule, cannot be violated
- soft_constraint: likely rule but could change
- observation: directly stated fact from source
- inference: reasonable deduction from evidence
- rumor: unverified player claim

Only output the JSON array. No explanation needed.
"""

    response = _call_llm(prompt, system_prompt)
    if not response:
        sys.stderr.write("[WARN] No LLM response — using heuristic extraction\n")
        return _heuristic_extract(pack, existing_claims)

    raw_claims = _parse_claims_from_llm_response(response, pack.get("pack_id", "EPACK-UNKNOWN"), existing_claims)
    return _build_claims(raw_claims, pack.get("pack_id", "EPACK-UNKNOWN"), existing_claims, pack.get("chunks", []))


def _heuristic_extract(pack: dict, existing_claims: list[dict]) -> list[dict]:
    claims = []
    new_claims = []

    for chunk in pack.get("chunks", []):
        text = chunk.get("text", "")
        card_name = chunk.get("card_name", "")
        list_name = chunk.get("list_name", "")
        source = f"{card_name} ({list_name})"

        patterns = [
            (r"(?:when|if).*?at (\d+)[%]? blood.*?zombif", "soft_constraint", 0.8, "blood_100_zombify"),
            (r"charred zombie", "observation", 0.7, "charred_zombie"),
            (r"(?:zombif|undead|convert).*?(?:knocked|opponent)", "soft_constraint", 0.6, "zombie_convert"),
            (r"(?:same|opposite).*?gender", "soft_constraint", 0.7, "gender_relation"),
            (r"(?:gender|appearance).*?(?:reroll|copy|mirror)", "soft_constraint", 0.6, "gender_appearance"),
            (r"bc.*?(?:character|rule|match)", "hard_constraint", 0.85, "bc_character_rule"),
            (r"xy.*?(?:mirror|rule)", "hard_constraint", 0.85, "xy_mirror_rule"),
            (r"(?:character|mirror|copy).*?(?:appearance|bc|xy)", "soft_constraint", 0.6, "mirror_appearance"),
            (r"(?:passive|manual).*?grip", "observation", 0.7, "grip_type"),
            (r"blood bar", "observation", 0.9, "blood_bar"),
        ]

        for pattern, ctype, confidence, tag in patterns:
            if pattern.lower() in text.lower():
                claim_text = f"{source}: pattern '{tag}' found in card description"
                # Minimal entity tracing for heuristic claims
                entity_ids = [chunk.get("entity_id", "")] if chunk.get("entity_id") else []
                claim_id = next_claim_id(existing_claims + new_claims)
                new_claims.append({
                    "claim_id": claim_id,
                    "source_id": pack.get("pack_id", "EPACK-UNKNOWN"),
                    "claim": claim_text,
                    "type": ctype,
                    "polarity": "neutral",
                    "confidence": confidence,
                    "evidence": f"Pattern match in {card_name}: {text[:200]}",
                    "source_entity_ids": entity_ids,
                    "quote_spans": [text[:200]] if text else [],
                    "status": "pending_review",
                    "contradicts": [],
                    "supported_by": [],
                    "tags": [tag],
                    "created_at": utc_now(),
                    "updated_at": utc_now(),
                    "notes": "Heuristically extracted",
                })

    return new_claims


def extract_from_evidence_pack(
    pack_path: Path,
    out_path: Path,
    add_to_ledger: bool = False,
) -> list[dict]:
    pack = json.loads(pack_path.read_text(encoding="utf-8"))

    existing_claims = []
    ledger_path = RB_DIR / "claim_ledger.json"
    if ledger_path.exists():
        existing_claims = json.loads(ledger_path.read_text(encoding="utf-8")).get("claims", [])

    print(f"Extracting claims from {len(pack.get('chunks', []))} chunks...")

    new_claims = _extract_from_chunks(pack, existing_claims)

    print(f"  Extracted {len(new_claims)} claims")
    for c in new_claims[:5]:
        print(f"  [{c['claim_id']}] {c['claim'][:80]}")
    if len(new_claims) > 5:
        print(f"  ... and {len(new_claims) - 5} more")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for c in new_claims:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    if add_to_ledger and new_claims:
        ledger_path = RB_DIR / "claim_ledger.json"
        if ledger_path.exists():
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        else:
            ledger = {"version": "1.0", "created_at": utc_now(), "claims": []}

        existing_ids = {c["claim_id"] for c in ledger.get("claims", [])}
        for c in new_claims:
            if c["claim_id"] not in existing_ids:
                ledger["claims"].append(c)

        from core import _recompute_stats
        _recompute_stats(ledger)
        save_json(ledger_path, ledger)
        print(f"[OK] Added {len(new_claims)} claims to claim_ledger.json")

    return new_claims


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract atomic claims from an evidence pack"
    )
    parser.add_argument(
        "--pack", "-p", required=True,
        help="Path to evidence pack JSON"
    )
    parser.add_argument(
        "--out", "-o", required=True,
        help="Output path for claims (.jsonl)"
    )
    parser.add_argument(
        "--add-to-ledger", action="store_true",
        help="Also append claims to the claim_ledger.json"
    )
    args = parser.parse_args()

    pack_path = Path(args.pack)
    out_path = Path(args.out)

    if not pack_path.exists():
        sys.stderr.write(f"[ERROR] Pack not found: {pack_path}\n")
        sys.exit(1)

    claims = extract_from_evidence_pack(pack_path, out_path, args.add_to_ledger)
    print(f"[OK] Wrote {len(claims)} claims to {out_path}")


if __name__ == "__main__":
    main()
