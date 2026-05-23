#!/usr/bin/env python3
"""
extract_claims.py — Extract atomic claims from ingested sources.

This script reads a source, applies the extract_claims prompt,
and adds new claims to the claim ledger.

Usage:
    python extract_claims.py --source-id SRC-0001
    python extract_claims.py --source-id SRC-0001 --interactive
    python extract_claims.py --source-id SRC-0001 --llm-openai
    python extract_claims.py --all
    python extract_claims.py --pending-only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from core import (
    RB_DIR, source_registry_path, claim_ledger_path, next_claim_id,
    utc_now, section, subsection, bullet, info, warn, ok, load_json, save_json,
    load_prompt,
)


def _get_source_content(source_entry: dict) -> str:
    """Read full file content from source_path. Falls back to _content_preview only if file is missing."""
    path = source_entry.get("source_path", "")
    if not path:
        return source_entry.get("_content_preview", "")
    p = Path(path)
    if p.exists():
        suffix = p.suffix.lower()
        if suffix == ".json":
            try:
                import orjson
                return orjson.dumps(
                    orjson.loads(p.read_bytes()),
                    option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS
                ).decode("utf-8")
            except Exception:
                return json.dumps(json.loads(p.read_text(encoding="utf-8")), indent=2, ensure_ascii=False)
        return p.read_text(encoding="utf-8", errors="replace")
    # File not found — last resort fallback to preview
    return source_entry.get("_content_preview", f"[File not found: {path}]")


def _call_llm(prompt: str, system: str = "", model: str = "gpt-4o") -> str | None:
    """Call LLM API. Returns None if API not available."""
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
        resp = client.chat.completions.create(model=model, messages=messages, temperature=0.1)
        return resp.choices[0].message.content
    except Exception as e:
        warn(f"LLM call failed: {e}")
        return None


def _call_anthropic(prompt: str, system: str = "") -> str | None:
    try:
        import os
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None
    except Exception:
        return None

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
        warn(f"Anthropic call failed: {e}")
        return None


def _parse_claims_from_response(response: str, source_id: str, existing_claims: list[dict]) -> list[dict]:
    """Parse extracted claims from LLM response."""
    new_claims = []

    # Try to extract JSON array first
    json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(1))
            if isinstance(parsed, list):
                for item in parsed:
                    new_claims.append(_build_claim(item, source_id, existing_claims, new_claims))
        except json.JSONDecodeError:
            pass

    # Also parse CLAIM_ID blocks
    claim_pattern = re.compile(
        r"CLAIM_ID:\s*(CLM-\d+)\s*\nSOURCE:\s*(\S+)\s*\nCLAIM:\s*(.*?)\nTYPE:\s*(\w+)\s*\nCONFIDENCE:\s*([\d.]+)\s*\nEVIDENCE:\s*(.*?)\nTAGS:\s*(.*?)(?=\n\n|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    for m in claim_pattern.finditer(response):
        claim_id = m.group(1).upper()
        src = m.group(2).strip()
        item = {
            "claim": m.group(3).strip(),
            "type": m.group(4).strip(),
            "confidence": float(m.group(5)),
            "evidence": m.group(6).strip(),
            "tags": [t.strip() for t in m.group(7).strip("[]").split(",") if t.strip()],
        }
        new_claims.append(_build_claim(item, source_id, existing_claims, new_claims))

    return new_claims


def _build_claim(item: dict, source_id: str, existing_claims: list[dict], new_claims: list[dict]) -> dict:
    """Build a complete claim dict from parsed data."""
    claim_id = next_claim_id(existing_claims + new_claims)
    claim_text = item.get("claim", item.get("text", ""))
    return {
        "claim_id": claim_id,
        "source_id": source_id,
        "claim": claim_text.strip(),
        "type": item.get("type", "observation"),
        "polarity": item.get("polarity", "neutral"),
        "confidence": float(item.get("confidence", 0.5)),
        "evidence": item.get("evidence", item.get("source", "")),
        "status": "pending_review",
        "contradicts": [],
        "supported_by": [],
        "tags": item.get("tags", []),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "notes": item.get("notes", ""),
    }


def _detect_contradictions(new_claims: list[dict], existing_claims: list[dict]) -> list[tuple]:
    """Detect contradictions between new and existing claims."""
    contradictions = []
    new_texts = [c["claim"].lower() for c in new_claims]

    for existing in existing_claims:
        if existing.get("status") in ("deprecated", "contradicted"):
            continue
        for new_c in new_claims:
            # Simple heuristic: check for negation patterns
            ex_lower = existing["claim"].lower()
            new_lower = new_c["claim"].lower()
            neg_patterns = [
                ("not needed", "required"),
                ("not required", "required"),
                ("no ", "required"),
                ("deprecated", "active"),
                ("fails", "passes"),
                ("wrong", "correct"),
                ("invalid", "valid"),
            ]
            for neg, pos in neg_patterns:
                if neg in ex_lower and pos in new_lower:
                    contradictions.append((existing, new_c))
                if neg in new_lower and pos in ex_lower:
                    contradictions.append((new_c, existing))

    return contradictions


def extract_from_source(source_id: str, interactive: bool = False, llm_backend: str = "auto") -> list[dict]:
    """Extract claims from a single source."""
    registry = load_json(source_registry_path())
    sources = registry.get("sources", [])
    source_entry = next((s for s in sources if s["source_id"] == source_id), None)
    if not source_entry:
        warn(f"Source not found: {source_id}")
        return []

    ledger = load_json(claim_ledger_path())
    claims = ledger.get("claims", [])

    content = _get_source_content(source_entry)
    prompt_template = load_prompt("extract_claims")
    prompt = prompt_template.replace("{{SOURCE_CONTENT}}", content)
    prompt = prompt.replace("{{SOURCE_ID}}", source_id)

    system_prompt = (
        "You are a meticulous research analyst. Extract only atomic, verifiable claims. "
        "Be precise and conservative — mark low confidence for rumors and inferences. "
        "Do not invent or assume facts not in the source."
    )

    subsection(f"Extracting claims from {source_id}: {source_entry['title']}")
    bullet(f"Source type: {source_entry['source_type']}")
    bullet(f"Tags: {', '.join(source_entry['tags'])}")

    # Try LLM
    response = None
    if llm_backend in ("auto", "openai"):
        response = _call_llm(prompt, system_prompt)
    if not response and llm_backend in ("auto", "anthropic"):
        response = _call_anthropic(prompt, system_prompt)

    if not response:
        warn("No LLM API available — showing extraction prompt for manual use")
        info(f"Source: {source_entry['source_path']}")
        info("Run with --llm-openai or --llm-anthropic when API is available")
        print("\n--- EXTRACTION PROMPT ---")
        print(prompt[:2000])
        print("...")
        return []

    new_claims = _parse_claims_from_response(response, source_id, claims)

    if not new_claims:
        warn("No claims extracted from response")
        info("Response preview:")
        print(response[:500])
        return []

    # Detect contradictions
    contradictions = _detect_contradictions(new_claims, claims)
    for a, b in contradictions:
        a["contradicts"].append(b["claim_id"])
        b["contradicts"].append(a["claim_id"])

    # Mark pending review
    for c in new_claims:
        c["status"] = "pending_review"

    section(f"Extracted {len(new_claims)} Claims")
    for c in new_claims:
        print(f"\n  [{c['claim_id']}] {c['claim'][:80]}")
        bullet(f"Type: {c['type']} | Confidence: {c['confidence']:.2f} | Status: {c['status']}")
        if c.get("contradicts"):
            bullet(f"Contrasts with: {', '.join(c['contradicts'])}")

    if contradictions:
        warn(f"Detected {len(contradictions)} potential contradictions")
        for a, b in contradictions:
            print(f"\n  {a['claim_id']} vs {b['claim_id']}:")
            print(f"    A: {a['claim'][:80]}")
            print(f"    B: {b['claim'][:80]}")

    # Add to ledger
    claims.extend(new_claims)
    ledger["claims"] = claims
    _recompute_stats(ledger)
    save_json(claim_ledger_path(), ledger)
    ok(f"Added {len(new_claims)} claims to ledger (total: {len(claims)})")

    if interactive:
        print("\n  [Interactive mode] Review each claim:")
        for c in new_claims:
            print(f"\n  [{c['claim_id']}] {c['claim'][:80]}")
            status = input("    Set status (active/pending_review/deprecated): ").strip().lower()
            if status in ("active", "pending_review", "deprecated"):
                c["status"] = status
        save_json(claim_ledger_path(), ledger)

    return new_claims


def _recompute_stats(ledger: dict) -> None:
    claims = ledger.get("claims", [])
    by_type = {}
    by_status = {}
    for c in claims:
        t = c.get("type", "unknown")
        s = c.get("status", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        by_status[s] = by_status.get(s, 0) + 1
    ledger["stats"] = {
        "total_claims": len(claims),
        "by_type": by_type,
        "by_status": by_status,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract atomic claims from sources")
    parser.add_argument("--source-id", type=str, help="Source ID to extract from (e.g. SRC-0001)")
    parser.add_argument("--interactive", action="store_true", help="Review each claim interactively")
    parser.add_argument("--llm-backend", type=str, default="auto", choices=["auto", "openai", "anthropic"],
                        help="LLM backend to use")
    parser.add_argument("--all", action="store_true", help="Extract from all sources with pending claims")
    args = parser.parse_args()

    if args.all:
        registry = load_json(source_registry_path())
        sources = registry.get("sources", [])
        section("Extracting from all sources")
        for src in sources:
            try:
                extract_from_source(src["source_id"], False, args.llm_backend)
            except Exception as e:
                warn(f"Failed on {src['source_id']}: {e}")
        return

    if not args.source_id:
        parser.print_help()
        return

    extract_from_source(args.source_id, args.interactive, args.llm_backend)


if __name__ == "__main__":
    main()
