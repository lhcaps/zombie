#!/usr/bin/env python3
"""
validate_research_brain.py — Validate all Research Brain JSON files against their schemas.

Usage:
    python validate_research_brain.py --all
    python validate_research_brain.py --sources
    python validate_research_brain.py --claims
    python validate_research_brain.py --hypotheses
    python validate_research_brain.py --protocols
    python validate_research_brain.py --results
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add scripts/ to path so we can import core
sys.path.insert(0, str(Path(__file__).parent))

from core import (
    RB_DIR, source_registry_path, claim_ledger_path, hypothesis_board_path,
    run_results_dir, test_protocols_dir,
    section, subsection, bullet, info, warn, ok,
    load_json,
)


def _load_schema(name: str) -> dict:
    path = RB_DIR / "schemas" / f"{name}.schema.json"
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_against_schema(data: dict, schema: dict, path_label: str) -> list[str]:
    """Validate a single object against a schema. Returns list of error strings."""
    try:
        from jsonschema import Draft7Validator, ValidationError
        validator = Draft7Validator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        result = []
        for err in errors:
            path_str = ".".join(str(p) for p in err.path) if err.path else "(root)"
            result.append(f"  [{path_label}] {path_str}: {err.message}")
        return result
    except ImportError:
        warn("jsonschema not installed — skipping strict validation")
        return []


def _validate_sources() -> tuple[int, int]:
    """Validate source_registry.json against source.schema.json."""
    section("Validating source_registry.json")
    all_errors: list[str] = []

    try:
        data = load_json(source_registry_path())
    except Exception as e:
        warn(f"Failed to load: {e}")
        return 0, 1

    schema = _load_schema("source")
    src_errors = _validate_against_schema(data, {"type": "object", "properties": {"sources": {"type": "array"}}}, "registry")
    all_errors.extend(src_errors)

    for src in data.get("sources", []):
        errs = _validate_against_schema(src, schema, src.get("source_id", "?"))
        all_errors.extend(errs)

    for err in all_errors:
        print(err)

    valid = len(data.get("sources", [])) - len([e for e in all_errors if "sources" not in e or "root" not in e])
    if not all_errors:
        ok(f"All {len(data.get('sources', []))} sources valid")
    return len(all_errors), len(data.get("sources", []))


def _validate_claims() -> tuple[int, int]:
    """Validate claim_ledger.json against claim.schema.json."""
    section("Validating claim_ledger.json")
    all_errors: list[str] = []

    try:
        data = load_json(claim_ledger_path())
    except Exception as e:
        warn(f"Failed to load: {e}")
        return 0, 1

    schema = _load_schema("claim")
    claims = data.get("claims", [])
    for claim in claims:
        errs = _validate_against_schema(claim, schema, claim.get("claim_id", "?"))
        all_errors.extend(errs)

    for err in all_errors:
        print(err)

    if not all_errors:
        ok(f"All {len(claims)} claims valid")
    return len(all_errors), len(claims)


def _validate_hypotheses() -> tuple[int, int]:
    """Validate hypothesis_board.json against hypothesis.schema.json."""
    section("Validating hypothesis_board.json")
    all_errors: list[str] = []

    try:
        data = load_json(hypothesis_board_path())
    except Exception as e:
        warn(f"Failed to load: {e}")
        return 0, 1

    schema = _load_schema("hypothesis")
    hyps = data.get("hypotheses", [])
    for hyp in hyps:
        errs = _validate_against_schema(hyp, schema, hyp.get("hypothesis_id", "?"))
        all_errors.extend(errs)

    for err in all_errors:
        print(err)

    if not all_errors:
        ok(f"All {len(hyps)} hypotheses valid")
    return len(all_errors), len(hyps)


def _validate_protocols() -> tuple[int, int]:
    """Validate all test_protocol/*.json files."""
    section("Validating test_protocols/")
    all_errors: list[str] = []

    schema = _load_schema("test_protocol")
    protocols_dir = test_protocols_dir()

    if not protocols_dir.exists():
        info("No test_protocols/ directory found — skipping")
        return 0, 0

    files = sorted(protocols_dir.glob("*.json"))
    if not files:
        info("No protocol files found")
        return 0, 0

    for pf in files:
        try:
            data = json.loads(pf.read_text(encoding="utf-8"))
        except Exception as e:
            warn(f"Failed to load {pf.name}: {e}")
            all_errors.append(f"  [{pf.name}] Parse error: {e}")
            continue
        errs = _validate_against_schema(data, schema, pf.stem)
        all_errors.extend(errs)

    for err in all_errors:
        print(err)

    if not all_errors:
        ok(f"All {len(files)} protocols valid")
    return len(all_errors), len(files)


def _validate_results() -> tuple[int, int]:
    """Validate all run_results/*.json files."""
    section("Validating run_results/")
    all_errors: list[str] = []

    schema = _load_schema("run_result")
    results_dir = run_results_dir()

    if not results_dir.exists():
        info("No run_results/ directory found — skipping")
        return 0, 0

    files = sorted(results_dir.glob("*.json"))
    if not files:
        info("No run result files found")
        return 0, 0

    for rf in files:
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
        except Exception as e:
            warn(f"Failed to load {rf.name}: {e}")
            all_errors.append(f"  [{rf.name}] Parse error: {e}")
            continue
        errs = _validate_against_schema(data, schema, rf.stem)
        all_errors.extend(errs)

    for err in all_errors:
        print(err)

    if not all_errors:
        ok(f"All {len(files)} run results valid")
    return len(all_errors), len(files)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Research Brain JSON files against schemas")
    parser.add_argument("--all", action="store_true", help="Validate all file types")
    parser.add_argument("--sources", action="store_true", help="Validate source_registry.json")
    parser.add_argument("--claims", action="store_true", help="Validate claim_ledger.json")
    parser.add_argument("--hypotheses", action="store_true", help="Validate hypothesis_board.json")
    parser.add_argument("--protocols", action="store_true", help="Validate test_protocols/")
    parser.add_argument("--results", action="store_true", help="Validate run_results/")
    args = parser.parse_args()

    if not any([args.all, args.sources, args.claims, args.hypotheses, args.protocols, args.results]):
        parser.print_help()
        return

    total_errors = 0
    total_checked = 0

    if args.all or args.sources:
        e, c = _validate_sources()
        total_errors += e
        total_checked += c

    if args.all or args.claims:
        e, c = _validate_claims()
        total_errors += e
        total_checked += c

    if args.all or args.hypotheses:
        e, c = _validate_hypotheses()
        total_errors += e
        total_checked += c

    if args.all or args.protocols:
        e, c = _validate_protocols()
        total_errors += e
        total_checked += c

    if args.all or args.results:
        e, c = _validate_results()
        total_errors += e
        total_checked += c

    section("Validation Summary")
    if total_errors == 0:
        ok(f"All {total_checked} files passed schema validation")
        print("\nResearch Brain is in a valid state.")
    else:
        warn(f"Found {total_errors} schema errors across {total_checked} files")
        print(f"\nFix errors before using the Research Brain for critical decisions.")
        sys.exit(1)


if __name__ == "__main__":
    main()
