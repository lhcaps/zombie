#!/usr/bin/env python3
"""Migrate hypothesis_board.json to include multi-axis scoring fields."""
import json
from pathlib import Path

board_path = Path("05_RESEARCH_BRAIN/hypothesis_board.json")
board = json.loads(board_path.read_text(encoding="utf-8"))

# Add lists structure
if "lists" not in board:
    board["lists"] = {
        "Research Output": {
            "description": "Hypotheses generated from evidence packs",
            "created_at": "2026-05-23T00:00:00Z"
        }
    }

# Multi-axis defaults for legacy hypotheses (derived from existing scores)
axis_defaults = {
    "HYP-COMMANDS-001": {
        "evidence_support": 0.05,
        "contradiction_risk": 0.95,
        "novelty": 0.3,
        "testability": 0.3,
        "mechanic_plausibility": 0.05,
    },
    "HYP-CHAR_MIRROR-001": {
        "evidence_support": 0.75,
        "contradiction_risk": 0.15,
        "novelty": 0.7,
        "testability": 0.6,
        "mechanic_plausibility": 0.8,
    },
    "HYP-BC_GENDER-001": {
        "evidence_support": 0.6,
        "contradiction_risk": 0.2,
        "novelty": 0.5,
        "testability": 0.5,
        "mechanic_plausibility": 0.7,
    },
    "HYP-APP_COPY-001": {
        "evidence_support": 0.3,
        "contradiction_risk": 0.4,
        "novelty": 0.6,
        "testability": 0.5,
        "mechanic_plausibility": 0.5,
    },
    "HYP-COUNT_ONLY-001": {
        "evidence_support": 0.15,
        "contradiction_risk": 0.6,
        "novelty": 0.4,
        "testability": 0.8,
        "mechanic_plausibility": 0.3,
    },
    "HYP-PASSIVE-001": {
        "evidence_support": 0.3,
        "contradiction_risk": 0.5,
        "novelty": 0.4,
        "testability": 0.6,
        "mechanic_plausibility": 0.4,
    },
}

backfilled = 0
for hyp in board.get("hypotheses", []):
    hid = hyp.get("hypothesis_id", "")
    if hid in axis_defaults and "evidence_support" not in hyp:
        hyp.update(axis_defaults[hid])
        backfilled += 1

board_path.write_text(json.dumps(board, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Backfilled {backfilled} hypotheses with multi-axis scoring and added 'lists' structure")
