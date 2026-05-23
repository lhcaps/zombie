# zombie-autoresearch

This is an experiment to have the LLM autonomously research the **Zombie Almighty** quest in Bleach: Brave Souls.

## Context: What is this?

The parent project (`../03_TOOLS/`) already contains:
- `zombie_test_runner.py` — CLI tool that runs test cases against the game, scores them, and tracks coverage.
- `zombie_tail_simulator.py` — scoring engine that evaluates which hypothesis variants best explain the observed test data.
- `zombie_analysis.py`, `zombie_csp_model.py`, `zombie_dispatcher.py` — analysis, probability modeling, and multi-agent dispatch.

This autoresearch setup is different. It trains a **nanochat-style GPT model** on the Zombie Almighty knowledge base (docs, notes, test results) and lets the agent experiment with the training code to improve the model's understanding — and by extension, improve the test generation and hypothesis scoring.

## The Research Goal

Find the best nanochat configuration (architecture, optimizer, hyperparameters) that:
1. Produces the **lowest val_bpb** (bits per byte) — meaning the model best predicts the zombie quest text corpus.
2. Generalizes to the zombie quest domain — after training, the model should better predict what "works" for the Zombie Almighty quest (correct steps, conditions, edge cases).

The hypothesis: a better-trained model → better test case generation → faster discovery of the Zombie Almighty solution.

## Setup

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `may23`). The branch `autoresearch/` must not already exist.
2. **Create the branch**: `git checkout -b autoresearch/` from current main.
3. **Read the in-scope files**: Read these for full context:
   - `README.md` — this file.
   - `prepare.py` — fixed constants, data prep, tokenizer, dataloader, evaluation. Do NOT modify.
   - `train.py` — the file you modify. Model architecture, optimizer, training loop.
   - `../00_FINAL/Zombie Almighty.pdf` — the current best theory on the zombie quest.
   - `../03_TOOLS/zombie_test_runner.py` — the test runner that evaluates hypothesis variants.
   - `../03_TOOLS/zombie_tail_simulator.py` — the scoring engine that ranks candidates.
4. **Verify data exists**: Check that `~/.cache/autoresearch/` contains data and a tokenizer. If not, run `uv run prepare.py`.
5. **Initialize results.tsv**: Create `results.tsv` with just the header row.
6. **Confirm and go**.

## Experimentation

Each experiment runs on a single GPU for a **fixed 5 minutes** (wall clock, excluding startup/eval). Launch with: `uv run train.py`.

**What you CAN do:**
- Modify `train.py` — architecture, optimizer, hyperparameters, batch size, model size, etc.

**What you CANNOT do:**
- Modify `prepare.py` — read-only.
- Install new packages — only use `pyproject.toml` dependencies.
- Modify the evaluation harness.

**The goal: get the lowest val_bpb.**

## Output format

```
---
val_bpb:          0.997900
training_seconds: 300.1
total_seconds:    325.9
peak_vram_mb:     45060.2
mfu_percent:      39.80
total_tokens_M:   499.6
num_steps:        953
num_params_M:     50.3
depth:            8
```

Extract key metric: `grep "^val_bpb:" run.log`

## Logging results

Log to `results.tsv` (tab-separated):

```
commit	val_bpb	memory_gb	status	description
a1b2c3d	0.997900	44.0	keep	baseline
b2c3d4e	0.993200	44.2	keep	increase LR to 0.04
c3d4e5f	1.005000	44.0	discard	switch to GeLU activation
d4e5f6g	0.000000	0.0	crash	double model width (OOM)
```

## The experiment loop

LOOP FOREVER:

1. Look at git state: current branch/commit.
2. Tune `train.py` with an experimental idea.
3. `git commit`
4. Run: `uv run train.py > run.log 2>&1`
5. Read results: `grep "^val_bpb:\|^peak_vram_mb:" run.log`
6. If grep is empty → crash. Read `tail -n 50 run.log`, attempt fix. If stuck, skip.
7. Log to `results.tsv`
8. If val_bpb improved → keep the git commit.
9. If val_bpb is equal or worse → `git reset` back.

**NEVER STOP** until manually interrupted. The user may be asleep.

## Tips for this zombie quest domain

- The zombie quest has a very specific structure: gender reroll → same-gender passive Blood Bar → manual grip → confirm zombie. Consider architectures that model sequential dependencies well.
- The `WINDOW_PATTERN` ("SSSL" vs "LLLL") affects how the model handles long-range dependencies in quest sequences.
- Try smaller `DEPTH` (4, 6) and larger `DEPTH` (12, 16) to find the right model capacity for the zombie quest text domain.
- Experiment with `MATRIX_LR` (0.02 - 0.08) for the Muon optimizer.
- The `ASPECT_RATIO` (default 64) controls model dimension = depth * ASPECT_RATIO.
- For RTX GPUs with limited VRAM, lower `DEPTH` and `TOTAL_BATCH_SIZE` (e.g., down to 2^14) may be necessary.
- The model trains on TinyStories (simple short stories). After training, consider evaluating it against the zombie quest corpus by running `python ../03_TOOLS/zombie_tail_simulator.py` to score hypotheses.

## Platform notes (Windows + consumer GPU)

This fork uses **PyTorch SDPA** instead of FlashAttention3. It works on RTX consumer GPUs (tested on RTX series). FlashAttention3 is only available on H100/H200 Hopper GPUs.

Key tunables for smaller VRAM:
- `DEPTH`: try 4, 6, 8, 10
- `WINDOW_PATTERN`: try "L" (full attention) if "SSSL" is too slow
- `DEVICE_BATCH_SIZE`: autotuned but may need manual override via environment: `AUTORESEARCH_DISABLE_AUTOTUNE=1`

Use `uv run train.py --smoke-test` for a quick validation pass (~10 seconds).
