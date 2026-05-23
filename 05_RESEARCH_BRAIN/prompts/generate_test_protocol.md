# Generate Test Protocol

Generate one precise, executable test protocol for the selected hypothesis.

## Required Sections

### 1. Goal
What single question does this test answer?

### 2. Hypothesis Being Tested
The exact hypothesis ID and summary.

### 3. Required Setup
Pre-conditions that must be met before the test can start.
Example: "Character must be Soul Reaper, starting gender F, world must be base (not hard mode)."

### 4. Variables Controlled
Variables held constant across this test and any repeat runs.
Example: "Race = Soul Reaper, Server = private, No Volt mode."

### 5. Variables Being Tested
The specific variable this test probes.
Example: "Whether the NPC check triggers at exactly 50 same-gender zombifications."

### 6. Exact Steps
Numbered, sequential steps. Every step must be:
- Observable (can be recorded)
- Specific (no vague instructions like "wait a bit" or "try it")
- Complete (no missing context)

Format:
```
Step 1: [action] → [what_to_record]
Step 2: [action] → [what_to_record]
...
```

### 7. What to Record
Checklist of all data to capture:
- NPC dialogue before and after
- Gender at each checkpoint
- Count at each checkpoint
- Balance before/after
- Screenshots at key moments
- Video if available

### 8. PASS Condition
Exact condition(s) that constitute a PASS. Be specific — not "it worked."

### 9. FAIL Condition
Exact condition(s) that constitute a FAIL. Be specific — not "it didn't work."

### 10. INCONCLUSIVE Condition
Conditions that make the test inconclusive rather than pass or fail.
Examples: "crashed mid-test", "wrong character used", "missed a checkpoint"

### 11. Common Execution Mistakes
Known ways this test can go wrong:
- Using the wrong grip method
- Wrong gender target
- Missing checkpoint recording
- Interrupting the zombification sequence

### 12. Follow-up Test if PASS
What to test next if this test passes.

### 13. Follow-up Test if FAIL
What to test next if this test fails.

## Protocol ID
Assign PROT-XXXX format.

## Rules

- Never use vague instructions.
- Every step must produce a recordable output.
- If evidence is insufficient for a clear PASS/FAIL, mark INCONCLUSIVE.
- The test should isolate ONE variable when possible.
- Always obey current hard constraints.
- Include pre-check and post-check in every protocol.
