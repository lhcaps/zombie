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
from pathlib import Path


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


def _fts_search(conn: sqlite3.Connection, query: str, top_k: int = 50) -> list[dict]:
    terms = [t.strip() for t in query.split() if t.strip()]
    if not terms:
        return []

    fts_query = " OR ".join(f'"{t}"' for t in terms)

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
    except sqlite3.OperationalError:
        rows = []

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

    results = []
    for row in rows:
        entity_id = row[0]
        cursor2 = conn.execute("""
            SELECT url, evidence_weight, updated_at, card_id, board_name
            FROM trello_entities
            WHERE entity_id = ?
        """, (entity_id,))
        meta = cursor2.fetchone()

        results.append({
            "entity_id": entity_id,
            "entity_type": row[1],
            "list_name": row[2] or "",
            "card_name": row[3] or "",
            "title": row[4] or "",
            "text": row[5] or "",
            "url": meta[0] if meta else "",
            "evidence_weight": meta[1] if meta else 0.5,
            "updated_at": meta[2] if meta else "",
            "card_id": meta[3] if meta else "",
            "board_name": meta[4] if meta else "",
            "rank": row[6] if len(row) > 6 else 0.0,
            "highlighted_text": _highlight_text(row[5] or "", query),
        })

    return results


def _type_filter(results: list[dict], entity_types: list[str]) -> list[dict]:
    if not entity_types:
        return results
    return [r for r in results if r["entity_type"] in entity_types]


def _score_and_rank(results: list[dict]) -> list[dict]:
    for r in results:
        weight = r.get("evidence_weight", 0.5)
        rank_score = abs(r.get("rank", 0))
        r["combined_score"] = weight * (1.0 / (1.0 + rank_score * 0.01))
    results.sort(key=lambda x: x["combined_score"], reverse=True)
    return results


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
) -> list[dict]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    results = _fts_search(conn, query, top_k * 2)

    if entity_types:
        results = _type_filter(results, entity_types)

    results = _score_and_rank(results)
    results = results[:top_k]

    conn.close()
    return results


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
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        sys.stderr.write(f"[ERROR] Database not found: {db_path}\n")
        sys.exit(1)

    print(f"Searching: '{args.query}' (top-{args.top_k})")
    results = search(db_path, args.query, args.top_k, args.entity_types, args.format)

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

    if len(results) < args.top_k:
        print(f"\n(Only {len(results)} results found)")


if __name__ == "__main__":
    main()
