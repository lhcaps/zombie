# Build Constraints

Given extracted claims, build a constraint model separating facts from guesses.

## Types of Constraints

**Hard Constraint** — Must be obeyed. Violating it = route is wrong.
- Example: "Exactly one gender reroll is required."

**Soft Constraint** — Likely true but could be wrong.
- Example: "The count is between 40 and 57."

**Negative Constraint** — Something that must NOT happen.
- Example: "No return/die commands needed."

**Deprecated Path** — A route that is known to fail under clean conditions.
- Example: "Two-reroll route was a failed path."

## Process

1. Read all active claims from the claim ledger.
2. Separate hard constraints from soft constraints.
3. Identify any contradictions between claims.
4. Build a constraint table with: constraint text, type, supporting claims, confidence, violated by.
5. Identify which hypotheses each constraint eliminates.
6. Flag any constraint that is uncertain — these are the unknowns to test.

## Output Format

### Constraint Table

```
| # | Constraint | Type | Confidence | Supporting Claims | Blocks |
|---|------------|------|------------|-------------------|--------|
| 1 | Exactly one gender reroll | hard | 0.90 | CLM-0001, CLM-0002 | OLD_MULTI_REROLL |
```

### Contradiction Log

```
| Claim A | Claim B | Conflict | Resolution |
|---------|---------|----------|------------|
| CLM-0003 | CLM-0004 | ... | pending / resolved |
```

### Unknowns

List constraints that have confidence < 0.7 — these are the open questions driving the research.

## Hard Constraints for Zombie Quest (from existing evidence)

- Exactly one gender reroll
- Same-gender targets after reroll
- Any race, non-unique targets
- Passive Blood Bar involved
- Manual grip zombification
- No return/die/invade commands
- No Volt/mode required
- Zombies do not need to act
