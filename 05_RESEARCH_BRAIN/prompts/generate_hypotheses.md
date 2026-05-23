# Generate Hypotheses

Given the claim ledger, constraint model, and failed/passed tests, generate candidate solution hypotheses.

## Hypothesis Definition

A hypothesis is a specific, testable path that could solve the quest. It must:
- Respect all hard constraints
- Be supported by at least one claim
- Have at least one unknown variable that can be tested
- Produce a protocol that can pass, fail, or be inconclusive

## Hypothesis Components

Every hypothesis must have:
- `hypothesis_id`: Unique identifier (e.g., HYP-CHAR_MIRROR-001)
- `title`: Short name (e.g., "Character Mirror + Same-Gender Final")
- `summary`: 1-2 paragraph description of the path
- `required_conditions`: Game state requirements
- `supporting_claims`: Claim IDs that support this
- `contradicting_claims`: Claim IDs that contradict this
- `unknowns`: Open questions this path raises
- `test_cost`: 1-10 scale (1=trivial, 10=very expensive)
- `risk`: 1-5 scale (1=low risk of wasting time, 5=high)
- `likelihood`: 0.0-1.0 based on current evidence fit
- `expected_info_gain`: 0.0-10.0 reduction in search space if test passes
- `evidence_fit`: 0.0-1.0 how well it fits existing evidence
- `constraint_fit`: 0.0-1.0 respects hard constraints
- `priority_score`: computed as likelihood * info_gain * constraint_fit / test_cost
- `status`: active / weak / blocked / rejected / deprecated / confirmed

## Generation Process

1. Read all active claims and hard constraints.
2. Identify the "tail" — the unknown portion after the core count.
3. For each tail candidate, check if it fits constraints.
4. Generate testable hypotheses from viable candidates.
5. Score each hypothesis on 5 axes:
   - **Evidence Fit**: How many supporting claims vs contradicting
   - **Constraint Fit**: Does it violate any hard constraint?
   - **Test Cost**: Time/effort to execute
   - **Information Gain**: How much does a pass/fail narrow the search?
   - **Reproducibility**: Can this be cleanly repeated?

## Scoring Formula

```
priority = likelihood × expected_info_gain × constraint_fit / test_cost
```

## Output

For each hypothesis, output the full structured data plus a brief justification of the score.

List hypotheses by priority_score descending.
