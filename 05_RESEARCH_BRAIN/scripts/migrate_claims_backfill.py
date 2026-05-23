#!/usr/bin/env python3
"""Backfill legacy claims in claim_ledger.json with source_entity_ids and quote_spans."""
import json
from pathlib import Path

ledger_path = Path("05_RESEARCH_BRAIN/claim_ledger.json")
ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

backfilled = 0
for claim in ledger.get("claims", []):
    if "source_entity_ids" not in claim:
        claim["source_entity_ids"] = []
        backfilled += 1
    if "quote_spans" not in claim:
        ev = claim.get("evidence", "")
        if ev:
            claim["quote_spans"] = [ev[:300]]
        else:
            claim["quote_spans"] = []
        backfilled += 1

ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Backfilled {backfilled} fields across {len(ledger['claims'])} claims")
