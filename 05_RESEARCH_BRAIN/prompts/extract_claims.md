# Extract Claims

Read the provided source document carefully.

Return only atomic claims — one independent fact per claim.

## Rules

- Do NOT summarize loosely. Each claim must be a single, specific, verifiable statement.
- Do NOT merge multiple ideas into one claim.
- Do NOT assume truth. Mark uncertainty clearly.
- If the source says something failed, preserve the exact condition that failed.
- If the source is a player rumor, mark as "rumor".
- If the source contradicts current claims, flag it as a potential contradiction.
- If the claim depends on interpretation, mark the confidence accordingly.
- If multiple sources agree, combine them as supporting evidence but still extract one claim per distinct fact.

## Claim Types

| Type | Meaning |
|------|---------|
| `hard_constraint` | Must be true for any clean route |
| `soft_constraint` | Likely true but not proven |
| `observation` | Observable game behavior |
| `failed_test` | A specific test condition that failed |
| `passed_test` | A specific test condition that passed |
| `rumor` | Unverified player claim |
| `inference` | Deduced from other facts |
| `deprecated_path` | Known broken route |

## Output Format

For each extracted claim, output:

```
CLAIM_ID: CLM-XXXX
SOURCE: SRC-XXXX
CLAIM: [exact statement]
TYPE: [type]
CONFIDENCE: 0.0-1.0
EVIDENCE: [exact quote or reference from source]
TAGS: [tag1, tag2, ...]
STATUS: active
```

Then output a JSON array:

```json
[
  {
    "claim": "...",
    "type": "...",
    "confidence": 0.0,
    "evidence": "...",
    "tags": []
  }
]
```

## Conflict Check

Before finalizing, check each new claim against the existing claim ledger:
- Does this contradict any existing claim?
- Does this strengthen any existing claim?
- Does this create a new hypothesis?
- Does this close any open question?

Output any detected conflicts at the end.
