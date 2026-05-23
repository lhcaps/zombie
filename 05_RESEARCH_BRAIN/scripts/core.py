"""
Shared utilities for 05_RESEARCH_BRAIN scripts.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# --- Paths ---
SCRIPT_DIR = Path(__file__).parent
RB_DIR = SCRIPT_DIR.parent
DATA_DIR = RB_DIR
SCHEMAS_DIR = RB_DIR / "schemas"
PROMPTS_DIR = RB_DIR / "prompts"


# --- State file paths ---
def source_registry_path() -> Path:
    return DATA_DIR / "source_registry.json"


def claim_ledger_path() -> Path:
    return DATA_DIR / "claim_ledger.json"


def hypothesis_board_path() -> Path:
    return DATA_DIR / "hypothesis_board.json"


def contradiction_log_path() -> Path:
    return DATA_DIR / "contradiction_log.md"


def decision_log_path() -> Path:
    return DATA_DIR / "decision_log.md"


def open_questions_path() -> Path:
    return DATA_DIR / "open_questions.md"


def test_protocols_dir() -> Path:
    d = DATA_DIR / "test_protocols"
    d.mkdir(exist_ok=True)
    return d


def run_results_dir() -> Path:
    d = DATA_DIR / "run_results"
    d.mkdir(exist_ok=True)
    return d


# --- JSON helpers ---
def load_json(path: Path) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict | list, indent: int = 2) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    print(f"  [saved] {path.relative_to(RB_DIR)}")


def load_or_init(path: Path, schema: dict) -> dict | list:
    if path.exists():
        return load_json(path)
    save_json(path, schema)
    return schema


# --- ID generators ---
def next_source_id(sources: list[dict]) -> str:
    existing = [s["source_id"] for s in sources if s.get("source_id", "").startswith("SRC-")]
    return _next_id(existing, "SRC-", 4)


def next_claim_id(claims: list[dict]) -> str:
    existing = [c["claim_id"] for c in claims if c.get("claim_id", "").startswith("CLM-")]
    return _next_id(existing, "CLM-", 4)


def next_hypothesis_id(hypotheses: list[dict]) -> str:
    existing = [h["hypothesis_id"] for h in hypotheses if h.get("hypothesis_id", "").startswith("HYP-")]
    return _next_id(existing, "HYP-", 3)


def next_protocol_id() -> str:
    d = test_protocols_dir()
    existing = []
    if d.exists():
        for f in d.glob("*.json"):
            m = re.match(r"PROT-(\d{4})", f.stem)
            if m:
                existing.append(f"PROT-{m.group(1)}")
    return _next_id(existing, "PROT-", 4)


def next_run_id() -> str:
    d = run_results_dir()
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    existing = []
    if d.exists():
        for f in d.glob("*.json"):
            m = re.match(r"RUN-(\d{8})-(\d{3})", f.stem)
            if m and m.group(1) == today:
                existing.append(f"RUN-{m.group(1)}-{m.group(2)}")
    base = f"RUN-{today}-"
    if not existing:
        return f"{base}001"
    nums = sorted(int(e.replace(base, "")) for e in existing)
    return f"{base}{nums[-1] + 1:03d}"


def _next_id(existing: list[str], prefix: str, digits: int) -> str:
    if not existing:
        return f"{prefix}{'0' * digits}"
    nums = sorted(int(re.sub(r"\D", "", e)) for e in existing)
    return f"{prefix}{nums[-1] + 1:0{digits}d}"


# --- Timestamps ---
def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- Source type detection ---
def detect_source_type(path: Path) -> str:
    ext = path.suffix.lower()
    type_map = {
        ".md": "markdown",
        ".pdf": "pdf",
        ".docx": "docx",
        ".json": "json",
        ".txt": "txt",
        ".log": "chat_log",
        ".png": "screenshot_description",
        ".jpg": "screenshot_description",
        ".jpeg": "screenshot_description",
    }
    return type_map.get(ext, "other")


# --- Prompt loading ---
def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


# --- Console output helpers ---
def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def subsection(title: str) -> None:
    print(f"\n  -- {title} --")


def bullet(msg: str) -> None:
    print(f"    {msg}")


def info(msg: str) -> None:
    print(f"  [info] {msg}")


def warn(msg: str) -> None:
    print(f"  [warn] {msg}", file=sys.stderr)


def error(msg: str) -> None:
    print(f"  [ERROR] {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")
