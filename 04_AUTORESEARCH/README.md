# zombie-autoresearch

Autonomous LLM research for the **Zombie Almighty** quest in Bleach: Brave Souls.

Forked from [karpathy/autoresearch](https://github.com/karpathy/autoresearch), adapted for Windows + consumer GPU (RTX series) using PyTorch SDPA instead of FlashAttention3.

## How it works

This repo runs nanochat-style GPT training experiments. Each experiment trains for a **fixed 5 minutes**, and the agent tries to find the best model configuration (architecture, optimizer, hyperparameters) that minimizes `val_bpb` (validation bits per byte).

The long-term goal: train a model that generalizes to the zombie quest domain, so that it can generate better test hypotheses and accelerate discovery of the full Zombie Almighty solution.

## Quick start

```bash
# 1. Install uv if needed
# curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Navigate to this directory
cd 04_AUTORESEARCH

# 3. Install dependencies
uv sync

# 4. Download TinyStories data + train tokenizer (~2 min)
uv run prepare.py

# 5. Quick smoke test (~10 sec)
uv run train.py --smoke-test

# 6. Full experiment (~5 min)
uv run train.py
```

## Project structure

```
04_AUTORESEARCH/
  prepare.py      — data prep + tokenizer (DO NOT MODIFY)
  train.py        — GPT model + training loop (agent modifies this)
  program.md      — agent instructions (customized for zombie quest)
  pyproject.toml  — dependencies
  README.md       — this file
```

## What to modify

The only file the agent edits is `train.py`. Everything in the model architecture, optimizer, hyperparameters, and training loop is fair game.

Key knobs to experiment with:
- `DEPTH` — number of transformer layers (default: 8)
- `ASPECT_RATIO` — model dimension = depth * aspect_ratio (default: 64)
- `WINDOW_PATTERN` — "SSSL" or "LLLL" attention pattern
- `MATRIX_LR` — Muon optimizer learning rate (default: 0.04)
- `TOTAL_BATCH_SIZE` — training batch size (default: 2^19)
- `DEVICE_BATCH_SIZE` — per-GPU batch (autotuned)

## Related tools

The main zombie quest research happens in `../03_TOOLS/`:

- `zombie_test_runner.py` — run test cases against the game
- `zombie_tail_simulator.py` — score hypothesis variants
- `zombie_csp_model.py` — CSP probability model
- `zombie_dispatcher.py` — multi-agent dispatch

After training a model, evaluate it against the zombie quest corpus by running the test runner.

## Architecture notes

- **Single GPU** — works on any NVIDIA GPU with CUDA
- **SDPA attention** — no FlashAttention3 dependency (compatible with RTX consumer cards)
- **Muon optimizer** — Newton's method-based optimizer from nanochat
- **Fixed 5-min time budget** — all experiments are directly comparable regardless of config changes

## Running autonomous research

Point your AI agent here with:

```
Hi! Look at program.md and let's kick off a new experiment. Run the setup first.
```

The agent will create a branch (e.g. `autoresearch/may23`), establish a baseline, then loop indefinitely — modifying `train.py`, running experiments, logging results, and advancing the branch when val_bpb improves.

## Data cache

Default location: `~/.cache/autoresearch/` (Linux/macOS) or `%LOCALAPPDATA%\autoresearch\` (Windows).

Override with: `set AUTORESEARCH_CACHE_DIR=D:\path\to\cache`

## License

MIT (same as upstream karpathy/autoresearch)
