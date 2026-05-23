# Zombie Research Brain — Rules

## Golden Rules

1. **No claim without source.** Every fact must trace to a document.
2. **No hypothesis without claim.** Every guess needs evidence backing it.
3. **No test without protocol.** Every proposed test needs exact steps.
4. **No belief change without reason.** Every update needs logged reasoning.
5. **No vague instructions.** "Try this" is not a test. Exact steps are.
6. **Simple beats complex.** If a 1-step route explains evidence, prefer it.
7. **Evidence beats intuition.** If the data says otherwise, update beliefs.
8. **INCONCLUSIVE is not PASS.** Don't count unclear results as wins.
9. **INCONCLUSIVE is not FAIL.** Don't penalize a hypothesis for unclear results.
10. **Hard constraints are immovable.** BLOCK any hypothesis that violates them.

## Claim Rules

### Adding a Claim

- Always cite the source_id.
- Set confidence honestly (0.1 for rumors, 0.9 for hard constraints).
- If the claim contradicts existing claims, flag it immediately.
- Never claim certainty when there is none.

### Claim Types

| Type | Confidence Range | Example |
|------|-----------------|---------|
| `hard_constraint` | 0.85–1.0 | "Exactly one gender reroll" |
| `soft_constraint` | 0.6–0.85 | "Count is between 40-57" |
| `observation` | 0.7–1.0 | "NPC dialogue changes at checkpoint" |
| `failed_test` | 1.0 | "x57 failed with same-gender targets" |
| `passed_test` | 1.0 | "x50 with passive grip confirmed" |
| `rumor` | 0.1–0.3 | "Player claimed command route works" |
| `inference` | 0.4–0.7 | "Character mirror must be activated before final check" |
| `deprecated_path` | 1.0 | "Two-reroll route was abandoned" |

### Claim Conflict Protocol

```
New claim arrives
        |
        v
Compare against existing claims of same type
        |
  +------+--------+
  |               |
  v               v
No conflict    Conflict detected
  |               |
  v               v
Add to ledger   Add both claims
                Flag in contradiction_log.md
                Score contradiction strength
                Recommend resolution test
```

## Hypothesis Rules

### Creating a Hypothesis

1. Start with supporting claims (at least 1).
2. State required conditions explicitly.
3. List unknowns honestly.
4. Score conservatively — prefer underestimation.
5. Assign test_cost honestly.

### Scoring Hypotheses

```
priority_score = likelihood × expected_info_gain × constraint_fit / test_cost
```

Axes:
- **Evidence Fit**: Count supporting claims vs contradicting claims.
- **Constraint Fit**: 1.0 if no hard constraint violated, else 0.0.
- **Test Cost**: 1 (trivial) to 10 (very expensive). Estimate honestly.
- **Information Gain**: How many other hypotheses does a pass eliminate?
- **Reproducibility**: Can this test be cleanly repeated?

### Hypothesis Lifecycle

```
HYPOTHESIS CREATED (weak, needs testing)
        |
        v
TEST PROTOCOL GENERATED
        |
        v
TEST RUN PERFORMED
        |
  +-----+-----+-----+
  |           |     |
  v           v     v
PASS         FAIL   INCONCLUSIVE
  |           |     |
  v           v     v
+likelihood   -likelihood   no change
mark active   add to failed_tests
                recommend new hyp
```

### When to Reject a Hypothesis

- A hard constraint contradicts it → BLOCKED
- Multiple clean tests failed → REJECTED
- A simpler hypothesis fits the same evidence better → DEPRECATED
- New evidence strongly contradicts it → REJECTED

## Test Protocol Rules

### Protocol Quality Checklist

- [ ] Goal is specific and answerable
- [ ] Hypothesis is clearly stated
- [ ] Setup preconditions are listed
- [ ] Controlled variables are named
- [ ] Tested variables are isolated
- [ ] Every step is exact and recordable
- [ ] PASS condition is specific
- [ ] FAIL condition is specific
- [ ] INCONCLUSIVE condition is defined
- [ ] Common mistakes are listed
- [ ] Follow-up actions are defined for each outcome

### Test Execution Standards

1. Follow all current hard constraints.
2. Record NPC dialogue before and after every milestone check.
3. Record exact count at every checkpoint (40, 45, 49, 50).
4. Record gender at each step.
5. Take screenshots at key moments.
6. Note any unexpected behavior.
7. If the test cannot be completed as planned, mark INCONCLUSIVE with reason.

### Result Recording Standards

Every result must include:
- Exact setup (game, server, world, race, genders, mode)
- Exact execution (count, method, NPC check points)
- Exact evidence (quotes, screenshots, video)
- Honest interpretation (not optimistic)
- Clear outcome (PASS / FAIL / INCONCLUSIVE)
- Confidence level (low / medium / high)

## Decision Log Rules

Every significant decision must be logged with:
- Date/time
- Decision made
- Evidence that drove the decision
- Alternatives considered
- Who/what made the decision

Decision types:
- **CLAIM_ADDED**: New claim entered the ledger
- **CLAIM_CONTRADICTED**: Conflict detected between claims
- **HYPOTHESIS_CREATED**: New hypothesis added
- **HYPOTHESIS_REJECTED**: Hypothesis marked rejected
- **HYPOTHESIS_DEPRECATED**: Hypothesis replaced by better one
- **TEST_DESIGNED**: New test protocol created
- **TEST_EXECUTED**: Test run completed
- **BELIEF_UPDATED**: Hypothesis likelihood changed
- **CONSTRAINT_ADDED**: New hard/soft constraint
- **CONSTRAINT_REMOVED**: Constraint was wrong

## Priority Rules

When deciding what to test next:

1. Test BLOCKED hypotheses? NO — they violate constraints.
2. Test REJECTED hypotheses? NO — unless testing as control.
3. Test CONFIRMED hypotheses? NO — already validated.
4. Test WEAK hypotheses? Only if all ACTIVE are tested.
5. Test ACTIVE hypotheses? YES — in priority order.

Within ACTIVE hypotheses:
- Higher evidence_fit first.
- Lower test_cost wins ties.
- Higher information_gain wins ties.
- Higher constraint_fit wins ties.

## Three-Layer Architecture Rules

### Layer 1 — Knowledge (source_registry, claim_ledger, contradiction_log)
- Ingest sources completely — no skipping "boring" parts.
- Extract all atomic claims, not just obvious ones.
- Tag every claim with source, type, confidence.
- Flag contradictions immediately.

### Layer 2 — Reasoning (hypothesis_board, decision_log, open_questions)
- Build hypotheses from claims, not from intuition.
- Score hypotheses honestly — no inflated scores.
- Log every decision with full reasoning.
- Maintain open_questions as the research agenda.

### Layer 3 — Testing (test_protocols, run_results, 03_TOOLS)
- Every test gets a protocol with exact steps.
- Every result gets recorded in full detail.
- Use 03_TOOLS for simulation, ranking, and coverage.
- Use 05_RESEARCH_BRAIN for thinking and planning.

## Anti-Patterns to Avoid

- **Hypothesis inflation**: Creating 20 hypotheses when 3 cover the evidence.
- **Score inflation**: Assigning 0.9 likelihood with only 1 supporting claim.
- **Vague tests**: "Try zombifying 50 times and see" without exact steps.
- **Optimistic interpretation**: Calling INCONCLUSIVE a PASS.
- **Claim merging**: Combining multiple facts into one claim.
- **Evidence ignoring**: Dismissing failed tests as "bad execution."
- **Complexity worship**: Preferring complex routes over simple ones.
- **Source skipping**: Ignoring "boring" sections of a document.
