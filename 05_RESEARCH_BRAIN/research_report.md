# Zombie Research Brain — Full Report

Generated: 2026-05-23 15:04 UTC

---

## Executive Summary

- **Total sources**: 9
- **Total claims**: 18 (17 tracked)
- **Active claims**: 17
- **Hard constraints**: 11
- **Total hypotheses**: 6
- **Active hypotheses**: 4
- **Untested**: 4
- **Tested**: 0

### Top Priority Hypothesis

**HYP-CHAR_MIRROR-001**: Character Mirror + Same-Gender Final

- Priority score: 0.2511
- Likelihood: 0.558
- Evidence fit: 0.88
- Constraint fit: 1.00
- Test cost: 4/10
- Info gain: 1.8

After one gender reroll and ~50 same-gender manual-grip zombifications through passive Blood Bar, activate character-copy/mirror relation, then perform final same-gender zombify/check while the mirror relation is active. The count must be discovered via milestone checks at 40, 45, 49, 50 during one clean run. The character mirror is a separate mechanic from the count — both are required.

**Required conditions**: exactly_one_gender_reroll, same_gender_targets, manual_grip, passive_blood_bar, no_commands, no_volt_mode, character_mirror_activated_before_final_check, final_zombify_while_mirror_active

---

## Sources

| ID | Title | Type | Tags | Findings |
|---|-------|------|------|---------|
| SRC-0001 | The Almighty Quests | txt | quest_text, core_requirements | 2 |
| SRC-0002 | Zombie Checklist Database | txt | checklist, hints, game_content | 2 |
| SRC-0003 | Almighty All Zombe Hints | txt | hints, game_content, gender | 3 |
| SRC-0004 | SideCharacter Update — 2026-05-22 | markdown | theory, gender_reroll, character_mirror | 4 |
| SRC-0005 | New Hint Reassessment — 2026-05-21 | markdown | csp_model, probability, count | 3 |
| SRC-0006 | Final Solution Working Notes | markdown | solution, steps, route | 3 |
| SRC-0007 | English Checklist | markdown | checklist, english, gender | 2 |
| SRC-0008 | Hint Image 2 Green Analysis | json | image_analysis, character_mirror, bc | 3 |
| SRC-0099 | Zombie Almighty — Final Build | pdf | final, consolidated, solution | 2 |

---

## Claims

### By Type
- **hard_constraint**: 10
- **soft_constraint**: 5
- **deprecated_path**: 1
- **observation**: 0
- **failed_test**: 0
- **passed_test**: 0
- **rumor**: 0
- **inference**: 0

### By Status
- **active**: 16
- **deprecated**: 1
- **superseded**: 0
- **contradicted**: 0

### Hard Constraints

- [CLM-0001] Exactly one gender reroll is required for the clean route. (confidence: 0.90)
- [CLM-0002] After gender reroll, zombify same-gender targets only. (confidence: 0.92)
- [CLM-0006] bc (uppercase) follows the character rule: matches race/class/appearance. (confidence: 0.85)
- [CLM-0007] xy (lowercase) follows the mirror rule: mirrors partner's appearance. (confidence: 0.85)
- [CLM-0008] Character copy relationship is confirmed in the image solution. (confidence: 0.88)
- [CLM-0009] Targets can be any race and do not need to be unique. (confidence: 0.88)
- [CLM-0011] Manual grip is the correct zombification method for clean tests. (confidence: 0.85)
- [CLM-0012] Return/die/invade commands are not needed for clean tests. (confidence: 0.88)
- [CLM-0013] Volt/mode lock is not required for clean tests. (confidence: 0.80)
- [CLM-0014] Zombies do not need to act or do anything after conversion. (confidence: 0.80)
- [CLM-0015] Items and accessories are explicitly not needed. (confidence: 0.85)

### Soft Constraints

- [CLM-0003] The zombification count is likely 50. (confidence: 0.42)
- [CLM-0004] The zombification count could be 49. (confidence: 0.23)
- [CLM-0005] Character mirror (copy/mirror appearance) is a mechanic involved in the tail. (confidence: 0.72)
- [CLM-0010] Passive Blood Bar buildup is required before zombification. (confidence: 0.75)
- [CLM-0016] The count must be discovered during one clean run via milestone checks. (confidence: 0.65)
- [CLM-0017] The tail involves copy/mirror character appearance + same-gender final zombify while mirror is active. (confidence: 0.68)

---

## Hypotheses

**Total**: 6 | **Active**: 4 | **Rejected**: 1

| # | Hypothesis ID | Title | Priority | Likelihood | Status | Tested |
|---|---------------|-------|----------|------------|--------|--------|
| 1 | HYP-CHAR_MIRROR-001 | Character Mirror + Same-Gender Fina | 0.2511 | 0.558 | active | No |
| 2 | HYP-BC_GENDER-001 | BC/xy Same-Gender Character Mirror  | 0.0897 | 0.299 | active | No |
| 3 | HYP-APP_COPY-001 | Appearance Copy Before Count, Keep  | 0.0375 | 0.125 | active | No |
| 4 | HYP-COUNT_ONLY-001 | Count Only — No Tail Required | 0.0010 | 0.001 | active | No |
| 5 | HYP-PASSIVE-001 | Passive Blood Bar + Manual Grip Cou | 0.0033 | 0.020 | weak | No |
| 6 | HYP-COMMANDS-001 | Return/Die Commands Required | 0.0000 | 0.001 | rejected | No |

---

## Open Questions

# Open Questions

These questions drive the research agenda. Each question should be resolved by a specific test.

---

## Priority 1 — Must Answer (Blocking hypotheses)

### Q-001: What is the exact zombification count?
- **Type**: Core unknown
- **Candidates**: 40, 45, 49, 50
- **Blocked hypotheses**: All CORE_COUNT and TAIL hypotheses depend on this
- **Test needed**: Systematic checkpoint testing at 40, 45, 49, 50 with same-gender targets
- **Evidence**: Amount 50-ish, 57 too much (SRC-0005)
- **Status**: OPEN

### Q-002: Does the character mirror mechanic need to be activated before the count, during, or after?
- **Type**: Timing unknown
- **Blocked hypotheses**: HYP-CHAR_MIRROR-001, HYP-BC_GENDER-001
- **Test needed**: Test mirror activation timing relative to zombification count
- **Evidence**: "copy/mirror character appearance + same-gender final zombify while mirror is active" (SRC-0004)
- **Status**: OPEN

### Q-003: Does "mirror" mean appearance copy (matching race/class) or literal mirror order?
- **Type**: Definition unknown
- **Blocked hypotheses**: HYP-CHAR_MIRROR-001
- **Test needed**: Test both interpretations — bc rule vs xy mirror rule
- **Evidence**: "bc=char rule, xy=mirror rule" (SRC-0008)
- **Status**: OPEN

---

## Priority 2 — Important (Affects efficiency)

### Q-004: Does the final NPC check require the NPC immediately after the last zombification, or after a short delay?
- **Type**: Timing unknown
- **Affects**: All hypothesis protocols — NPC timing could be the difference between PASS and FAIL
- **Test needed**: Test immediate vs delayed NPC check
- **Evidence**: Checkpoint observations from zombie_analysis.py
- **Status**: OPEN

### Q-005: What NPC dialogue or balance change indicates progress toward the goal?
- **Type**: Observation unknown
- **Affects**: All tests — need to know what "good" looks like
- **Test needed**: Record NPC dialogue and balance at each checkpoint (40, 45, 49, 50)
- **Evidence**: None yet — need baseline data
- **Status**: OPEN

### Q-006: Is the character mirror mechanic binary (on/off) or does it have intensity levels?
- **Type**: Mechanism unknown
- **Affects**: HYP-CHAR_MIRROR-001 — if binary, just activate it; if intensity, need to measure
- **Test needed**: Observe if mirror effect stacks or is binary
- **Evidence**: Character copy relationship confirmed (SRC-0008)
- **Status**: OPEN

---

## Priority 3 — Nice to Know (Reduces uncertainty)

### Q-007: Can the quest be completed on any world or does it require specific world settings?
- **Type**: Context unknown
- **Affects**: Test protocol setup
- **Evidence**: Server type mentioned in 03_TOOLS setup
- **Status**: OPEN

### Q-008: Are there race-specific requirements for the zombie targets?
- **Type**: Target constraint
- **Affects**: CLM-0009 (any race claim)
- **Evidence**: "Targets can be any race" (SRC-0006) — but not proven
- **Status**: OPEN — CLM-0009 needs validation

### Q-009: Does passive Blood Bar need to be maintained continuously or just accumulated once?
- **Type**: Method unknown
- **Affects**: CLM-0010 (passive blood bar constraint)
- **Evidence**: Passive blood bar involved (SRC-0006)
- **Status**: OPEN

---

## Recently Resolved

*None yet. All tests are pending execution.*

---

## Recent Decisions

NOTES and 03_TOOLS into the Research Brain claim ledger.
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

---

## Contradictions

# Contradiction Log

Every contradiction between claims is logged here with resolution status.

| Claim A | Claim B | Conflict Description | Strength | Resolution | Resolved At |
|---------|---------|---------------------|----------|-----------|------------|
| CLM-0002 (same-gender only) | CLM-0099 (deprecated multi-reroll) | Multi-reroll potentially implied cross-gender targets | Strong | CLM-0002 wins (hard constraint). CLM-0099 marked deprecated. | 2026-05-22 |

---

## Pending Contradictions

*None currently pending. All known contradictions resolved.*

---

## Resolution History

### 2026-05-22
- **CLM-0002 vs CLM-0099**: The multi-reroll route implied multiple gender changes, which contradicts the same-gender constraint from CLM-0002. Resolution: One-reroll constraint (CLM-0001) established as hard, multi-reroll (CLM-0099) marked deprecated. This simplifies the search space significantly.

---

## Test Protocols

### PROT-0000 — HYP-CHAR_MIRROR-001

**Goal**: Test whether Character Mirror + Same-Gender Final is the correct tail mechanic.
**Steps**: 10
**PASS**: NPC dialogue indicates quest completion or significant progress. Balance/appearance changes match ex
**FAIL**: NPC dialogue unchanged after completing all steps. No progress indicator. Route fails to advance.

### PROT-0001 — HYP-BC_GENDER-001

**Goal**: Test whether BC/xy Same-Gender Character Mirror Pair is the correct tail mechanic.
**Steps**: 10
**PASS**: NPC dialogue indicates quest completion or significant progress. Balance/appearance changes match ex
**FAIL**: NPC dialogue unchanged after completing all steps. No progress indicator. Route fails to advance.

### PROT-0002 — HYP-APP_COPY-001

**Goal**: Test whether Appearance Copy Before Count, Keep Active is the correct tail mechanic.
**Steps**: 10
**PASS**: NPC dialogue indicates quest completion or significant progress. Balance/appearance changes match ex
**FAIL**: NPC dialogue unchanged after completing all steps. No progress indicator. Route fails to advance.

---

*Report generated by Zombie Research Brain at 2026-05-23 15:04 UTC*
*Project: https://github.com/lhcaps/zombie*