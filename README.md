# Zombie Almighty Workspace

This folder is organized around the latest usable Zombie Almighty theory and test material.

## Three-Layer Architecture

The project uses three layers:

| Layer | Name | Purpose | Directory |
|-------|------|---------|-----------|
| Layer 1 | **Knowledge** | Sources, claims, evidence, contradictions | `05_RESEARCH_BRAIN/` |
| Layer 2 | **Reasoning** | Constraints, hypotheses, scoring, decisions | `05_RESEARCH_BRAIN/` |
| Layer 3 | **Testing** | Protocols, run results, coverage, simulation | `03_TOOLS/` |

## Research Brain — Primary Reasoning Engine

**`05_RESEARCH_BRAIN/`** is the main reasoning layer for quest discovery.

```
Sources (docs, images, notes)
        ↓
ingest_sources.py
        ↓
extract_claims.py        → claim_ledger.json
        ↓
build_claim_table.py    → constraint_model.md
        ↓
Hypotheses             → hypothesis_board.json
        ↓
rank_hypotheses.py
        ↓
generate_next_tests.py  → test_protocols/
        ↓
Test in game
        ↓
zombie_test_runner.py --mode=record --rich  → run_results/
        ↓
update_after_result.py  → belief update + decision log
        ↓
export_research_report.py
        ↓
Repeat
```

### Quick Start

```bash
# 1. Ingest new source documents
python 05_RESEARCH_BRAIN/scripts/ingest_sources.py --path ../01_SOURCES/new_doc.md --title "My Note"
python 05_RESEARCH_BRAIN/scripts/ingest_sources.py --list

# 2. Extract claims from all sources
python 05_RESEARCH_BRAIN/scripts/extract_claims.py --all --llm-backend openai

# 3. Build constraint model
python 05_RESEARCH_BRAIN/scripts/build_claim_table.py

# 4. Rank hypotheses
python 05_RESEARCH_BRAIN/scripts/rank_hypotheses.py
python 05_RESEARCH_BRAIN/scripts/rank_hypotheses.py --hypothesis-id HYP-CHAR_MIRROR-001

# 5. Generate test protocols
python 05_RESEARCH_BRAIN/scripts/generate_next_tests.py --top-n 3

# 6. After testing: record result
python 03_TOOLS/zombie_test_runner.py --mode=record --case-id=CORE_F_50 --outcome=fail --rich --hypothesis-id=HYP-CHAR_MIRROR-001 --run-id=RUN-20260523-001 --confidence=high --gender=F --race="Soul Reaper" --count-target=50 --count-actual=50 --npc-after="..." --notes="..."

# 7. Update beliefs
python 05_RESEARCH_BRAIN/scripts/update_after_result.py --run-id=RUN-20260523-001

# 8. Export report
python 05_RESEARCH_BRAIN/scripts/export_research_report.py
```

### Research Brain Files

- `program.md` — agent instructions (read first)
- `research_rules.md` — 10 golden rules and anti-patterns
- `source_registry.json` — all ingested sources (9 sources)
- `claim_ledger.json` — 17 atomic claims with evidence
- `hypothesis_board.json` — 6 hypotheses ranked by priority
- `contradiction_log.md` — conflicts between claims
- `decision_log.md` — every research decision with reasoning
- `open_questions.md` — 9 open questions driving research
- `schemas/` — JSON schemas for all data types
- `prompts/` — LLM prompts for each reasoning step
- `scripts/` — 7 Python scripts for the pipeline
- `test_protocols/` — generated test protocols
- `run_results/` — recorded test results in rich format

### Current Top Hypothesis

**HYP-CHAR_MIRROR-001** (Priority: 0.251, Likelihood: 55.8%)

```
After one gender reroll and ~50 same-gender manual-grip zombifications
through passive Blood Bar, activate character-copy/mirror relation,
then perform final same-gender zombify/check while the mirror is active.
```

## Testing Tools — Execution Layer

**`03_TOOLS/`** handles test execution, simulation, and coverage tracking.

```bash
cd 03_TOOLS

# List all test cases
python zombie_test_runner.py --mode=list

# Ranked priorities
python zombie_test_runner.py --mode=priorities

# Next best test
python zombie_test_runner.py --mode=next

# Coverage report
python zombie_test_runner.py --mode=coverage

# Tail simulation
python zombie_test_runner.py --mode=simulate

# Dispatch to agents
python zombie_test_runner.py --mode=dispatch --max=4

# Full analysis report
python zombie_test_runner.py --mode=report

# Generate test cases
python zombie_test_runner.py --mode=generate

# Record a result (legacy format)
python zombie_test_runner.py --mode=record --case-id=CORE_F_50 --outcome=fail

# Record a result (Research Brain format, recommended)
python zombie_test_runner.py --mode=record --case-id=TAIL_F_50_CHAR_MIRROR --outcome=fail \
    --rich --hypothesis-id=HYP-CHAR_MIRROR-001 --confidence=high \
    --gender=F --count-target=50 --count-actual=50 --npc-after="..." --notes="..."
```

### Hard Constraints (Immovable)

- Exactly one gender reroll for clean route
- Same-gender targets after reroll
- Any race, non-unique targets
- Passive Blood Bar involved
- Manual grip zombification
- No return/die/invade commands
- No Volt/mode required
- Zombies do not need to act

## Final Artifacts

Final shareable files in `00_FINAL/`:

- `Zombie Almighty.docx`
- `Zombie Almighty.pdf`
- `Zombie Almighty.zip` (bundle for sharing)

## Folder Map

- `00_FINAL/` - latest usable `Zombie_Almighty` final artifacts.
- `01_SOURCES/` - original docs, hint images, Cristi screenshots, and extracted source text.
- `02_WORKING_NOTES/` - current markdown notes and latest green-only image analysis.
- `03_TOOLS/` - test runner, scorer, dispatcher, coverage tracker, document builder.
- `04_AUTORESEARCH/` - optional model-training experiment (lowest priority).
- `05_RESEARCH_BRAIN/` - primary reasoning engine: claims, hypotheses, protocols, evidence ledger.
- `99_ARCHIVE_OLD_RUNS/` - archived old scripts, analyses, and outputs.

## Note

`_Zombie Checklist Database.docx` in root is locked by another process. A copy is at:

```
01_SOURCES/_Zombie Checklist Database.docx
```
