#!/usr/bin/env python3
"""
research_question.py — Unified CLI entry point for the Research Brain Trello pipeline.

This is the single command that orchestrates the full research pipeline:
  Raw Trello JSON → Entities → Index → Evidence Pack → Claims → Hypotheses → Protocol

Usage:
    python research_question.py --question "..." --raw-trello ../trello.txt

    # Full pipeline (builds index if needed, generates pack + claims + hypotheses):
    python research_question.py --question "Resolve the exact two unknown steps after gender reroll and same-gender zombification" --raw-trello ../trello.txt --raw-trello ../trello.txt --pipeline all

    # Just search Trello (fast, requires existing index):
    python research_question.py --question "zombie mechanics" --search-only

    # Build/update index:
    python research_question.py --build-index --raw-trello ../trello.txt

    # Full pipeline with evidence pack:
    python research_question.py --question "..." --evidence-pack ../evidence_packs/EPACK-001.json --pipeline all
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
RB_DIR = SCRIPT_DIR.parent
REPO_ROOT = RB_DIR.parent
SRC_DIR = REPO_ROOT / "01_SOURCES"
INDEX_DIR = RB_DIR / "indexes"
EVIDENCE_DIR = RB_DIR / "evidence_packs"


def _print_banner() -> None:
    print("=" * 70)
    print("  RESEARCH BRAIN — Trello Compiler & Evidence Pipeline")
    print("=" * 70)
    print()


def _default_paths() -> dict[str, Path]:
    return {
        "raw_trello": REPO_ROOT / "trello.txt",
        "entities": INDEX_DIR / "trello_entities.jsonl",
        "manifest": INDEX_DIR / "trello_manifest.json",
        "db": INDEX_DIR / "trello.db",
        "ontology": RB_DIR / "mechanics_ontology.json",
        "hypothesis_board": RB_DIR / "hypothesis_board.json",
        "claim_ledger": RB_DIR / "claim_ledger.json",
    }


def _step_normalize(raw_path: Path, entities_path: Path, manifest_path: Path) -> dict:
    from trello_normalize import normalize_board, generate_manifest

    print(f"\n[STEP 1] Normalizing Trello raw JSON...")
    print(f"  Input:  {raw_path}")

    raw_data = json.loads(raw_path.read_text(encoding="utf-8"))
    import hashlib
    sha256 = hashlib.sha256(raw_path.read_bytes()).hexdigest()

    entities = normalize_board(raw_data, str(raw_path.resolve()), sha256)
    manifest = generate_manifest(raw_data, entities, str(raw_path.resolve()), sha256)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    with open(entities_path, "w", encoding="utf-8") as f:
        for e in entities:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  Output: {entities_path} ({len(entities)} entities)")
    print(f"  Manifest: {manifest_path}")
    return manifest


def _step_index(entities_path: Path, db_path: Path, rebuild: bool = False) -> dict:
    from trello_index import index_entities

    print(f"\n[STEP 2] Building SQLite FTS5 index...")
    print(f"  Entities: {entities_path}")
    print(f"  Database: {db_path}")

    stats = index_entities(entities_path, db_path, rebuild)

    print(f"  Indexed: {stats['total_entities']} entities")
    print(f"  FTS entries: {stats['fts_entries']}")
    return stats


def _step_search(db_path: Path, question: str, top_k: int = 30) -> list[dict]:
    from trello_search import search

    print(f"\n[STEP 3] Searching Trello index...")
    print(f"  Query: {question[:80]}")

    results = search(db_path, question, top_k)
    print(f"  Found: {len(results)} results")
    return results


def _step_evidence_pack(
    question: str,
    db_path: Path,
    out_dir: Path,
    max_chunks: int = 40,
    seed: int | None = None,
) -> Path:
    from build_evidence_pack import build_evidence_pack, _pack_to_markdown

    print(f"\n[STEP 4] Building evidence pack...")
    print(f"  Question: {question[:80]}")
    if seed is not None:
        print(f"  Seed: {seed} (deterministic mode)")

    pack = build_evidence_pack(question, db_path, max_chunks=max_chunks, seed=seed)
    pack_id = pack["pack_id"]

    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{pack_id}.json"
    md_path = out_dir / f"{pack_id}.md"

    json_path.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(_pack_to_markdown(pack), encoding="utf-8")

    print(f"  Pack ID: {pack_id}")
    print(f"  Chunks: {pack['retrieval']['final_chunks']} "
          f"({pack['retrieval'].get('positive_chunks', '?')} positive + "
          f"{pack['retrieval'].get('negative_chunks', '?')} negative)")
    print(f"  Queries: {len(pack['retrieval'].get('positive_queries', []))} positive + "
          f"{len(pack['retrieval'].get('negative_queries', []))} negative")
    print(f"  Coverage: {pack['coverage']}")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")
    return json_path


def _step_extract_claims(pack_path: Path, out_dir: Path) -> Path:
    from extract_claims_batch import extract_from_evidence_pack

    print(f"\n[STEP 5] Extracting claims from evidence pack...")

    claims_path = out_dir / f"claims_{pack_path.stem}.jsonl"
    claims = extract_from_evidence_pack(pack_path, claims_path, add_to_ledger=False)

    print(f"  Extracted: {len(claims)} claims")
    print(f"  Output: {claims_path}")
    return claims_path


def _step_generate_hypotheses(
    question: str,
    pack_path: Path,
    out_dir: Path,
    add_to_board: bool = False,
    board_list: str | None = None,
    idempotency_key: str | None = None,
) -> Path:
    from generate_hypotheses_from_claims import generate_hypotheses

    print(f"\n[STEP 6] Generating hypotheses from evidence...")
    if idempotency_key:
        print(f"  Idempotency key: {idempotency_key}")

    hyp_path = out_dir / f"hypotheses_{pack_path.stem}.json"
    hyps = generate_hypotheses(
        question, pack_path, hyp_path,
        add_to_board=add_to_board,
        board_list=board_list,
        idempotency_key=idempotency_key,
    )

    print(f"  Generated: {len(hyps)} hypotheses")
    for h in hyps[:3]:
        print(f"  [{h['hypothesis_id']}] {h['title'][:60]}")
        print(f"    score={h['priority_score']:.4f} status={h['status']}")
    print(f"  Output: {hyp_path}")
    return hyp_path


def _step_search_only(db_path: Path, question: str, top_k: int) -> None:
    from trello_search import search, _format_markdown

    results = search(db_path, question, top_k)
    print(f"\n[SEARCH RESULTS] Found {len(results)} results for: {question}")
    print(_format_markdown(results, question))


def _build_index_only(raw_path: Path, paths: dict) -> None:
    manifest = _step_normalize(raw_path, paths["entities"], paths["manifest"])
    _step_index(paths["entities"], paths["db"], rebuild=True)
    print("\n[OK] Index built successfully. Run without --build-index to search.")


def run_full_pipeline(
    question: str,
    raw_path: Path,
    paths: dict,
    rebuild_index: bool = False,
    add_to_board: bool = False,
    max_chunks: int = 40,
    top_k: int = 30,
    seed: int | None = None,
    dry_run: bool = False,
    board_list: str = "Research Output",
    idempotency_key: str | None = None,
) -> dict:
    manifest = _step_normalize(raw_path, paths["entities"], paths["manifest"])
    _step_index(paths["entities"], paths["db"], rebuild=rebuild_index)

    results = _step_search(paths["db"], question, top_k)
    pack_path = _step_evidence_pack(question, paths["db"], EVIDENCE_DIR, max_chunks, seed)
    claims_path = _step_extract_claims(pack_path, EVIDENCE_DIR)
    hyp_path = _step_generate_hypotheses(
        question, pack_path, EVIDENCE_DIR,
        add_to_board=add_to_board and not dry_run,
        board_list=board_list if not dry_run else None,
        idempotency_key=idempotency_key,
    )

    return {
        "question": question,
        "manifest": manifest,
        "search_results": len(results),
        "pack_path": str(pack_path),
        "claims_path": str(claims_path),
        "hypotheses_path": str(hyp_path),
        "dry_run": dry_run,
        "seed": seed,
    }


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="Research Brain — Trello Compiler & Evidence Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Search only (fast, needs existing index):
    python research_question.py --question "zombie blood grip" --search-only

    # Build/update index:
    python research_question.py --build-index --raw-trello ../trello.txt

    # Full pipeline (dry-run, no board mutation):
    python research_question.py \
        --question "Resolve the two unknown steps after gender reroll" \
        --raw-trello ../trello.txt \
        --pipeline all \
        --dry-run \
        --idempotency-key EPACK-001

    # Full pipeline with board write (idempotent):
    python research_question.py \
        --question "Resolve the two unknown steps after gender reroll" \
        --raw-trello ../trello.txt \
        --pipeline all \
        --add-to-board \
        --idempotency-key EPACK-001 \
        --board-list "Research Output"

    # Deterministic run for reproducibility:
    python research_question.py \
        --question "zombie zombify blood grip charred" \
        --pipeline retrieve \
        --seed 42
        """,
    )
    parser.add_argument(
        "--question", "-q",
        help="Research question to answer"
    )
    parser.add_argument(
        "--raw-trello", "-r",
        help="Path to raw Trello JSON export"
    )
    parser.add_argument(
        "--db",
        help="Path to trello.db (default: 05_RESEARCH_BRAIN/indexes/trello.db)"
    )
    parser.add_argument(
        "--pipeline",
        choices=["all", "pack-only", "claims-only", "hypotheses-only"],
        default="all",
        help="Which pipeline steps to run"
    )
    parser.add_argument(
        "--build-index",
        action="store_true",
        help="Rebuild the Trello index from scratch"
    )
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Force rebuild index (same as --build-index)"
    )
    parser.add_argument(
        "--evidence-pack", "-e",
        help="Use existing evidence pack instead of generating new one"
    )
    parser.add_argument(
        "--add-to-board",
        action="store_true",
        help="Add generated hypotheses to hypothesis_board.json (requires --idempotency-key)"
    )
    parser.add_argument(
        "--board-list",
        default="Research Output",
        help="Trello list name for board mutation (default: 'Research Output')"
    )
    parser.add_argument(
        "--idempotency-key",
        help="Unique key for idempotent board writing (e.g. EPACK-2ISH-001). "
             "Prevents duplicate entries on re-runs."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline but do NOT write to hypothesis_board.json. "
             "Use this to validate output before committing."
    )
    parser.add_argument(
        "--write-pack",
        action="store_true",
        help="Write evidence pack to disk (default: true). "
             "Use --no-write-pack to skip writing."
    )
    parser.add_argument(
        "--max-chunks", "-m", type=int, default=40,
        help="Max chunks in evidence pack (default: 40)"
    )
    parser.add_argument(
        "--top-k", "-k", type=int, default=30,
        help="Results per search query (default: 30)"
    )
    parser.add_argument(
        "--seed", type=int,
        help="Random seed for deterministic chunk selection. "
             "Same seed + same question = identical evidence pack."
    )
    parser.add_argument(
        "--search-only",
        action="store_true",
        help="Just search the existing index, don't build pack or generate hypotheses"
    )
    args = parser.parse_args()

    if args.add_to_board and not args.idempotency_key:
        sys.stderr.write("[ERROR] --add-to-board requires --idempotency-key\n")
        sys.exit(1)

    _print_banner()

    paths = _default_paths()
    if args.db:
        paths["db"] = Path(args.db)

    raw_path = Path(args.raw_trello) if args.raw_trello else None
    if raw_path and not raw_path.exists():
        sys.stderr.write(f"[ERROR] Raw Trello file not found: {raw_path}\n")
        sys.exit(1)

    db_exists = paths["db"].exists()
    entities_exist = paths["entities"].exists()

    if args.search_only:
        if not db_exists:
            sys.stderr.write(f"[ERROR] No index found at {paths['db']}. Run with --build-index first.\n")
            sys.exit(1)
        if not args.question:
            sys.stderr.write("[ERROR] --question required for search\n")
            sys.exit(1)
        _step_search_only(paths["db"], args.question, args.top_k)
        return

    if args.build_index or args.rebuild_index:
        if not raw_path:
            sys.stderr.write("[ERROR] --raw-trello required with --build-index\n")
            sys.exit(1)
        _build_index_only(raw_path, paths)
        return

    if args.pipeline == "all" or args.pipeline == "pack-only":
        if not raw_path and not db_exists:
            sys.stderr.write("[ERROR] Need either --raw-trello or existing index at {paths['db']}\n")
            sys.exit(1)

        if raw_path:
            print(f"Running full pipeline for question:")
            print(f"  {args.question}")
            if args.dry_run:
                print(f"  [DRY RUN] No board mutations will be written")
            if args.idempotency_key:
                print(f"  Idempotency key: {args.idempotency_key}")
            result = run_full_pipeline(
                args.question or "Unknown",
                raw_path,
                paths,
                rebuild_index=args.rebuild_index or not db_exists,
                add_to_board=args.add_to_board,
                max_chunks=args.max_chunks,
                top_k=args.top_k,
                seed=args.seed,
                dry_run=args.dry_run,
                board_list=args.board_list,
                idempotency_key=args.idempotency_key,
            )
            print(f"\n{'=' * 70}")
            print(f"  Pipeline complete!")
            print(f"  Evidence pack: {result['pack_path']}")
            print(f"  Claims: {result['claims_path']}")
            print(f"  Hypotheses: {result['hypotheses_path']}")
            if args.dry_run:
                print(f"  [DRY RUN] No board was mutated")
        elif args.evidence_pack:
            from build_evidence_pack import build_evidence_pack
            pack_path = Path(args.evidence_pack)
            if not pack_path.exists():
                sys.stderr.write(f"[ERROR] Evidence pack not found: {pack_path}\n")
                sys.exit(1)
            if args.pipeline == "all":
                _step_extract_claims(pack_path, EVIDENCE_DIR)
                _step_generate_hypotheses(
                    args.question or "Research question",
                    pack_path, EVIDENCE_DIR,
                    add_to_board=args.add_to_board and not args.dry_run,
                    board_list=args.board_list if not args.dry_run else None,
                    idempotency_key=args.idempotency_key,
                )
            print("\n[OK] Pipeline complete")
        return

    if not args.question:
        parser.print_help()
        return


if __name__ == "__main__":
    main()
