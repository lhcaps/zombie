#!/usr/bin/env python3
"""
trello_search.py — Keyword + FTS5 search over indexed Trello entities.

Usage:
    python trello_search.py --db ../indexes/trello.db --query "zombie blood grip" --top-k 30
    python trello_search.py --db ../indexes/trello.db --query "gender reroll appearance" --top-k 50 --format json
    python trello_search.py --db ../indexes/trello.db --query "T G Z X C critical passive" --top-k 100 --out ../01_SOURCES/trello/views/ability_keys.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import re
import io
import random
from pathlib import Path


# --- FTS5 query escaping ---
# FTS5 special characters: " - : * NEAR AND OR NOT ( ) ^
# We convert user queries into OR-joined quoted terms, escaping embedded quotes.

_FTS_SPECIAL_RE = re.compile(r'["\-:\*\(\)\^]')


def fts_quote(term: str) -> str:
    """Escape and quote a single term for FTS5."""
    term = term.strip().replace('"', '""')
    return f'"{term}"'


def build_or_query(terms: list[str]) -> str:
    """Convert a list of terms into an FTS5 OR query, safely escaped."""
    clean = [t for t in terms if t.strip()]
    if not clean:
        return ""
    return " OR ".join(fts_quote(t) for t in clean)


def _sanitize_fts_query(raw_query: str) -> str:
    """Strip FTS5 operators that could change query semantics."""
    # Replace special FTS operators with spaces so they don't break MATCH
    return _FTS_SPECIAL_RE.sub(" ", raw_query)


def _highlight_text(text: str, query: str, max_len: int = 600) -> str:
    if not text:
        return ""
    terms = [t.strip() for t in query.split() if len(t) > 1]
    result = text
    for term in terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        result = pattern.sub(f"**{term.upper()}**", result)
    if len(result) > max_len:
        first_match = -1
        for term in terms:
            idx = result.lower().find(term.lower())
            if idx >= 0:
                first_match = max(0, idx - 50)
                break
        start = first_match
        result = "..." + result[start : start + max_len] + "..."
    return result


def _fts_search(
    conn: sqlite3.Connection,
    query: str,
    top_k: int = 50,
    include_debug: bool = False,
) -> tuple[list[dict], dict]:
    safe_query = _sanitize_fts_query(query)
    terms = [t.strip() for t in safe_query.split() if t.strip()]
    if not terms:
        return [], {}

    fts_query = build_or_query(terms)

    debug_info: dict = {}
    if include_debug:
        debug_info["sanitized_query"] = safe_query
        debug_info["fts_query"] = fts_query
        debug_info["terms"] = terms

    try:
        cursor = conn.execute(f"""
            SELECT
                f.entity_id,
                f.entity_type,
                f.list_name,
                f.card_name,
                f.title,
                f.text,
                bm25(trello_fts) AS rank
            FROM trello_fts f
            WHERE trello_fts MATCH :query
            ORDER BY rank
            LIMIT :limit
        """, {"query": fts_query, "limit": top_k * 2})
        rows = cursor.fetchall()
        if include_debug:
            debug_info["fts_hit"] = True
            debug_info["fts_row_count"] = len(rows)
    except sqlite3.OperationalError:
        rows = []
        if include_debug:
            debug_info["fts_hit"] = False
            debug_info["fts_error"] = True

    if not rows:
        like_pattern = "%" + "%".join(terms) + "%"
        cursor = conn.execute("""
            SELECT
                entity_id,
                entity_type,
                list_name,
                card_name,
                title,
                text,
                evidence_weight AS rank
            FROM trello_entities
            WHERE text LIKE :pattern
               OR card_name LIKE :pattern
               OR title LIKE :pattern
            ORDER BY evidence_weight DESC
            LIMIT :limit
        """, {"pattern": like_pattern, "limit": top_k * 2})
        rows = cursor.fetchall()
        if include_debug:
            debug_info["fallback_like"] = True

    results = []
    for row in rows:
        entity_id = row[0]
        cursor2 = conn.execute("""
            SELECT url, evidence_weight, updated_at, card_id, board_name
            FROM trello_entities
            WHERE entity_id = ?
        """, (entity_id,))
        meta = cursor2.fetchone()

        bm25_val = row[6] if len(row) > 6 else 0.0
        weight = meta[1] if meta else 0.5
        combined = weight * (1.0 / (1.0 + abs(bm25_val) * 0.01))

        result_dict = {
            "entity_id": entity_id,
            "entity_type": row[1],
            "list_name": row[2] or "",
            "card_name": row[3] or "",
            "title": row[4] or "",
            "text": row[5] or "",
            "url": meta[0] if meta else "",
            "evidence_weight": weight,
            "updated_at": meta[2] if meta else "",
            "card_id": meta[3] if meta else "",
            "board_name": meta[4] if meta else "",
            "bm25_rank": bm25_val,
            "combined_score": combined,
            "highlighted_text": _highlight_text(row[5] or "", query),
        }
        if include_debug:
            result_dict["_debug"] = {
                "bm25": round(bm25_val, 4),
                "weight": weight,
                "combined": round(combined, 4),
                "bm25_contrib": round(abs(bm25_val) * 0.01, 4),
                "weight_contrib": round(weight, 4),
            }
        results.append(result_dict)

    return results, debug_info


def _type_filter(results: list[dict], entity_types: list[str]) -> list[dict]:
    if not entity_types:
        return results
    return [r for r in results if r["entity_type"] in entity_types]


def _format_markdown(results: list[dict], query: str) -> str:
    lines = [
        f"# Trello Search Results",
        f"",
        f"**Query:** `{query}`",
        f"**Results:** {len(results)}",
        f"",
        f"---",
        f"",
    ]

    current_card = None
    for r in results:
        card_key = r["card_id"] or r["entity_id"]
        if card_key != current_card:
            lines.append(f"## {r['card_name'] or r['entity_id']}")
            meta_parts = []
            if r["list_name"]:
                meta_parts.append(f"List: *{r['list_name']}*")
            if r["entity_type"]:
                meta_parts.append(f"Type: `{r['entity_type']}`")
            if r["evidence_weight"]:
                meta_parts.append(f"Weight: {r['evidence_weight']:.2f}")
            if meta_parts:
                lines.append(f"**{' | '.join(meta_parts)}**")
            if r["url"]:
                lines.append(f"URL: {r['url']}")
            lines.append("")
            current_card = card_key

        text = r.get("highlighted_text", r.get("text", ""))
        if text:
            lines.append(f"{text}")
        lines.append("")

    return "\n".join(lines)


def _format_json(results: list[dict], query: str) -> str:
    output = {
        "query": query,
        "total_results": len(results),
        "results": results,
    }
    return json.dumps(output, indent=2, ensure_ascii=False)


def search(
    db_path: Path,
    query: str,
    top_k: int = 50,
    entity_types: list[str] | None = None,
    format: str = "markdown",
    include_debug: bool = False,
) -> tuple[list[dict], dict]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    raw, debug = _fts_search(conn, query, top_k * 2, include_debug)

    if entity_types:
        raw = _type_filter(raw, entity_types)

    raw.sort(key=lambda x: x["combined_score"], reverse=True)
    results = raw[:top_k]

    conn.close()
    return results, debug


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="Search indexed Trello entities using FTS5"
    )
    parser.add_argument(
        "--db", "-d", required=True,
        help="Path to trello.db"
    )
    parser.add_argument(
        "--query", "-q", required=True,
        help="Search query (space-separated terms)"
    )
    parser.add_argument(
        "--top-k", "-k", type=int, default=50,
        help="Maximum results to return (default: 50)"
    )
    parser.add_argument(
        "--type", "-t", action="append", dest="entity_types",
        help="Filter by entity type (card, chunk, attachment, list). Can be repeated."
    )
    parser.add_argument(
        "--format", "-f", choices=["markdown", "json"], default="markdown",
        help="Output format (default: markdown)"
    )
    parser.add_argument(
        "--out", "-o",
        help="Write output to file instead of stdout"
    )
    parser.add_argument(
        "--explain-ranking",
        action="store_true",
        help="Show ranking formula breakdown: bm25_norm * 0.65 + weight * 0.25 + recency * 0.10"
    )
    parser.add_argument(
        "--seed", "-s", type=int,
        help="Set random seed for deterministic tie-breaking (default: none)"
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        sys.stderr.write(f"[ERROR] Database not found: {db_path}\n")
        sys.exit(1)

    if args.seed is not None:
        random.seed(args.seed)
        print(f"[SEED] Random seed set to {args.seed} for deterministic results")

    print(f"Searching: '{args.query}' (top-{args.top_k})")
    include_debug = args.explain_ranking
    results, debug = search(db_path, args.query, args.top_k, args.entity_types, args.format, include_debug)

    if args.format == "json":
        output = _format_json(results, args.query)
    else:
        output = _format_markdown(results, args.query)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"[OK] Wrote {len(results)} results to {out_path}")
    else:
        print(output)

    if args.explain_ranking:
        print("\n" + "=" * 60)
        print("  RANKING FORMULA EXPLAINED")
        print("=" * 60)
        print(f"  Query:          {args.query}")
        print(f"  Sanitized:      {debug.get('sanitized_query', '')}")
        print(f"  FTS query:      {debug.get('fts_query', '')}")
        print(f"  FTS hit:        {debug.get('fts_hit', '?')}")
        print(f"  FTS row count:  {debug.get('fts_row_count', '?')}")
        if debug.get("fallback_like"):
            print(f"  Fallback:       LIKE pattern (FTS returned no results)")
        print()
        print("  Combined score = evidence_weight * (1 / (1 + |bm25| * 0.01))")
        print("    = weight * (1 / (1 + bm25_contribution))")
        print()
        print("  Top-5 breakdown:")
        for i, r in enumerate(results[:5], 1):
            d = r.get("_debug", {})
            print(f"  {i}. [{r['entity_id'][:30]}]")
            print(f"     bm25={d.get('bm25', 0):.4f}  weight={d.get('weight', 0):.2f}  combined={d.get('combined', 0):.4f}")
            print(f"     card={r.get('card_name', '(no name)')[:50]}")
        print()
        print("=" * 60)

    if len(results) < args.top_k:
        print(f"\n(Only {len(results)} results found)")


if __name__ == "__main__":
    main()
