#!/usr/bin/env python3
"""Determinism test: run the same query 3 times with same seed."""
import sys
import random
sys.path.insert(0, "05_RESEARCH_BRAIN/scripts")
from trello_search import search
from pathlib import Path

db = Path("05_RESEARCH_BRAIN/indexes/trello.db")
query = "zombie zombify blood grip charred"
top_k = 10
seed = 42

results_hashes = []
for run in range(1, 4):
    random.seed(seed)
    results, _ = search(db, query, top_k)
    combined_score = [round(r["combined_score"], 4) for r in results]
    results_hashes.append(combined_score)
    print(f"Run {run}: top-5 combined_scores: {combined_score[:5]}")

all_same = all(h == results_hashes[0] for h in results_hashes[1:])
if all_same:
    print("\n[DETERMINISM] All 3 runs returned identical results")
    sys.exit(0)
else:
    print("\n[NON-DETERMINISM] Results differ between runs!")
    for i, scores in enumerate(results_hashes):
        print(f"  Run {i+1}: {scores[:5]}")
    sys.exit(1)
