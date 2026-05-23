# Update Beliefs

After each test run, update the claim ledger, hypothesis board, and evidence base.

## Trigger

Run this after: a PASS, FAIL, or INCONCLUSIVE result is recorded.

## Process

### 1. Read the Run Result

Extract from run_result.json:
- run_id
- hypothesis_id tested
- outcome (PASS / FAIL / INCONCLUSIVE)
- confidence level
- what was actually tested vs what was planned
- any anomalies or unexpected observations

### 2. Read the Hypothesis Being Tested

Get the hypothesis summary, required conditions, and current likelihood.

### 3. Apply Bayesian Update

**If PASS (well-executed):**
- Increase hypothesis likelihood significantly
- Decrease likelihood of competing hypotheses
- Add new claims for the passing conditions
- Mark unknowns as resolved if the test answered them

**If FAIL (well-executed):**
- Decrease hypothesis likelihood significantly
- Add the failed condition to deprecated_paths or failed_tests
- Check if this failure creates a contradiction with existing claims
- Look for new hypotheses that this failure suggests

**If INCONCLUSIVE:**
- Do not change hypothesis likelihood
- Flag the test protocol as flawed or execution as flawed
- Identify what went wrong
- Recommend a repeat test with fixes

### 4. Update Claim Ledger

- Add or update claims based on what was observed
- Mark claim confidence changes
- Flag any new contradictions detected
- Deprecate claims that were contradicted

### 5. Update Hypothesis Board

- Recalculate priority scores for all hypotheses
- Mark REJECTED / DEPRECATED as appropriate
- Add any new hypotheses suggested by the result
- Recompute priority ranking

### 6. Write Decision Log Entry

Every belief update must be logged with:
- What changed
- Why it changed
- What evidence drove the change
- Who/what made the decision

### 7. Check Open Questions

- Which questions were answered?
- Which questions became more urgent?
- Which questions are now moot?

## Output

1. **Belief Update Summary**: What changed and why
2. **Claim Ledger Updates**: New/changed claims
3. **Hypothesis Board Updates**: Status changes and new priority scores
4. **New Contradictions Found**: Any new conflicts detected
5. **New Open Questions**: Questions this test raised
6. **Decision Log Entry**: Formatted log entry
7. **Next Recommendation**: What to do next

## Rules

- Never change a hypothesis status without evidence.
- INCONCLUSIVE is not FAIL. Do not penalize the hypothesis.
- If a PASS contradicts existing claims, investigate before updating.
- Document the reasoning, not just the result.
