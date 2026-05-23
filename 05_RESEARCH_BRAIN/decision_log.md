# Decision Log

Every significant research decision is logged here with full reasoning.

---

## 2026-05-23 — Migration to Research Brain

### Decision: CLAIM_ADDED — Initial claim ledger populated from working notes
- **What**: Migrated all established claims from 02_WORKING_NOTES and 03_TOOLS into the Research Brain claim ledger.
- **Evidence**: 17 claims extracted from SRC-0001 through SRC-0099.
- **Reasoning**: Before running new tests, the Research Brain needs a baseline claim set. All claims were reviewed against their source documents.
- **Alternatives**: Start with empty ledger. Rejected — would lose existing evidence.
- **Who**: Research Brain setup

### Decision: HYPOTHESIS_CREATED — Initial hypotheses migrated from 03_TOOLS
- **What**: Populated hypothesis_board.json with 6 hypotheses from zombie_csp_model.py and zombie_tail_simulator.py.
- **Evidence**: CHAR_MIRROR had highest simulation probability (55.8%), COUNT_ONLY lowest (0.1%).
- **Reasoning**: These hypotheses represent the current search space. Priority scores computed from simulation data.
- **Alternatives**: Start fresh. Rejected — would lose months of reasoning.
- **Who**: Research Brain setup

### Decision: CONSTRAINT_ADDED — 8 hard constraints established
- **What**: Established 8 hard constraints that cannot be violated.
- **Evidence**: CLM-0001 through CLM-0015 and CLM-0017.
- **Reasoning**: Hard constraints define the search boundary. Any hypothesis violating them is immediately BLOCKED.
- **Who**: Research Brain setup

---

## 2026-05-22 — SideCharacter Update

### Decision: HYPOTHESIS_DEPRECATED — OLD_MULTI_REROLL marked deprecated
- **What**: Marked multi-reroll hypothesis as ruled_out/deprecated.
- **Evidence**: CLM-0001 (one reroll hard constraint) and CLM-0099 (deprecated_path). Evidence weight for one_reroll: 3.0.
- **Reasoning**: Multiple sources now agree exactly one reroll is required. Multi-reroll route contradicts this.
- **Who**: Manual analysis

### Decision: HYPOTHESIS_CREATED — CHAR_MIRROR ranked #1
- **What**: Created CHAR_MIRROR hypothesis with highest priority.
- **Evidence**: bc_char(3.5), xy_mirror(3.2), bc_gender(3.2), appearance_copy_seen(3.0). Tail simulation: 55.8% probability, 100% top-1 stability.
- **Reasoning**: Image solution strongly suggests character mirroring mechanic. This is the most evidence-backed tail candidate.
- **Who**: Manual analysis

---

## 2026-05-21 — CSP Model and Probability Scoring

### Decision: CLAIM_ADDED — Count candidates scored via CSP model
- **What**: Established count candidates 50, 49, 45, 40 with probability scores.
- **Evidence**: amount_50ish(2.5), below_57(1.8) from evidence bank. Reason: "50-ish and 57 is too much."
- **Reasoning**: No single count proven; must test multiple candidates. Priority by probability.
- **Who**: zombie_csp_model.py automated scoring

### Decision: HYPOTHESIS_CREATED — 6 tail candidates generated
- **What**: Generated 6 unknown task pair candidates from evidence bank.
- **Evidence**: 18 evidence items scored across 6 candidates. CHAR_MIRROR had highest raw score.
- **Reasoning**: The "tail" (unknown portion after count) is the main research gap. Candidates generated from all available evidence.
- **Who**: zombie_tail_simulator.py Monte Carlo scoring
