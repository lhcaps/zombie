# Rank Hypotheses

Given the full claim ledger, active constraints, test results, open questions, and current hypotheses, rank all active hypotheses by testing priority.

## Input

- claim_ledger.json: All known claims with types and confidence
- constraint_model.md: Hard and soft constraints
- hypothesis_board.json: All hypotheses with current scores
- run_results.json: All past test results
- open_questions.md: Current open questions
- failed_tests.json: Specific test conditions that failed

## Ranking Axes

Score each hypothesis on 6 axes:

| Axis | What it measures | Weight |
|------|-----------------|--------|
| Evidence Fit | Claim support vs contradiction | high |
| Constraint Fit | Respects all hard constraints | mandatory |
| Contradiction Penalty | Any claim against it? | high |
| Test Cost | Time/effort (1=cheap, 10=expensive) | medium |
| Information Gain | Eliminates how many branches if passed? | high |
| Reproducibility | Can test be cleanly repeated? | medium |

## Priority Formula

```
priority_score = likelihood × expected_info_gain × constraint_fit / test_cost
```

## Decision Rules

- If constraint_fit < 1.0, the hypothesis is BLOCKED, not ranked.
- Never rank a complex hypothesis above a simpler one with equal evidence.
- Never rank a hypothesis that violates hard constraints.
- A FAILED test that was well-executed should reduce likelihood significantly.
- An INCONCLUSIVE test should not change likelihood but flags the test as flawed.
- Reproducibility matters: tests that are hard to reproduce get lower priority.

## Output

1. **Full ranking table**: All hypotheses sorted by priority_score
2. **Top 5 with justification**: Why each is ranked where it is
3. **What evidence supports each top hypothesis**
4. **What evidence weakens each top hypothesis**
5. **The exact next test needed** for the #1 hypothesis
6. **Open questions** that block ranking for lower hypotheses
7. **Hypotheses to reject** with reason
8. **Hypotheses to deprecate** with reason

## Recommendation

End with a clear recommendation:
- Which hypothesis to test next
- What protocol to follow
- What outcome to look for
- What to do if PASS / FAIL / INCONCLUSIVE
