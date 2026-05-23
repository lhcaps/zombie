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
