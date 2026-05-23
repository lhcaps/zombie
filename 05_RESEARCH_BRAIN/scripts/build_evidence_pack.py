#!/usr/bin/env python3
"""
build_evidence_pack.py — Assemble a focused evidence pack for a research question.

An evidence pack is a curated, deduplicated set of chunks (max ~30-40)
optimized for LLM reasoning on a specific question.

Usage:
    python build_evidence_pack.py --question "..." --db ../indexes/trello.db --out ../evidence_packs/EPACK-001.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import io
from datetime import datetime, timezone
from pathlib import Path

from core import RB_DIR


_DEFAULT_TOPIC_QUERIES = {
    "zombie_candidates": [
        "zombie zombify blood grip charred undead ghoul",
        "burn convert knocked opponents Fire Bankai passive",
        "manual grip zombification 100 blood",
    ],
    "gender_appearance": [
        "gender reroll same gender appearance copy mirror vanity transform",
        "character copy bc xy rule character rule mirror rule",
        "race class gender relation partner",
    ],
    "ability_keys": [
        "T G Z X C critical passive mode overdrive",
        "M2 Volt Bankai Resurreccion Vollstandig",
        "move key input combo",
    ],
    "grip_mechanics": [
        "grip grab execute knocked opponent",
        "manual grip passive grip counter",
        "zombify convert target partner",
    ],
    "quest_mechanics": [
        "quest npc check obtainment milestone",
        "40 45 49 50 count zombify",
        "clean route step sequence",
    ],
    "tail_mechanics": [
        "tail mechanic character mirror passive",
        "two ish steps gender reroll zombification",
        "final check NPC timing",
    ],
}


def _query_expand(question: str) -> list[str]:
    expansions = []
    q_lower = question.lower()
    if any(kw in q_lower for kw in ["zombie", "zombify", "blood", "grip", "charred"]):
        expansions.extend(_DEFAULT_TOPIC_QUERIES["zombie_candidates"])
    if any(kw in q_lower for kw in ["gender", "appearance", "copy", "mirror", "vanity", "reroll"]):
        expansions.extend(_DEFAULT_TOPIC_QUERIES["gender_appearance"])
    if any(kw in q_lower for kw in ["t g z x c", "key", "critical", "passive", "mode", "overdrive"]):
        expansions.extend(_DEFAULT_TOPIC_QUERIES["ability_keys"])
    if any(kw in q_lower for kw in ["grip", "grab", "execute", "knocked"]):
        expansions.extend(_DEFAULT_TOPIC_QUERIES["grip_mechanics"])
    if any(kw in q_lower for kw in ["quest", "npc", "check", "count", "milestone"]):
        expansions.extend(_DEFAULT_TOPIC_QUERIES["quest_mechanics"])
    if any(kw in q_lower for kw in ["tail", "two", "ish", "step"]):
        expansions.extend(_DEFAULT_TOPIC_QUERIES["tail_mechanics"])
    if not expansions:
        terms = [t for t in re.split(r"[\s,.!?;:'\"()]+", q_lower) if len(t) > 2]
        expansions.append(" ".join(terms[:12]))
    seen = set()
    unique = []
    for e in expansions:
        if e not in seen:
            seen.add(e)
            unique.append(e)
    return unique


def _fts_search(conn: sqlite3.Connection, query: str, top_k: int) -> list[dict]:
    results: list[dict] = []

    # FTS5: convert space-separated terms to OR-separated for better recall
    terms = [t.strip() for t in query.split() if t.strip()]
    fts_query = " OR ".join(f'"{t}"' for t in terms) if terms else query

    try:
        cursor = conn.execute("""
            SELECT
                f.entity_id,
                f.entity_type,
                f.list_name,
                f.card_name,
                f.title,
                f.text,
                bm25(trello_fts) AS rank
            FROM trello_fts f
            WHERE f.trello_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (fts_query, top_k * 2))
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        rows = []

    if not rows:
        terms = query.strip().split()
        like = "%" + "%".join(terms) + "%"
        cursor = conn.execute("""
            SELECT entity_id, entity_type, list_name, card_name, title, text, 0.0 AS rank
            FROM trello_entities
            WHERE text LIKE ? OR card_name LIKE ? OR title LIKE ?
            ORDER BY evidence_weight DESC
            LIMIT ?
        """, (like, like, like, top_k * 2))
        rows = cursor.fetchall()

    entity_ids = [row[0] for row in rows]
    if not entity_ids:
        return []

    placeholders = ",".join("?" * len(entity_ids))
    meta_rows = conn.execute(f"""
        SELECT entity_id, url, evidence_weight, updated_at, card_id, board_name
        FROM trello_entities
        WHERE entity_id IN ({placeholders})
    """, entity_ids).fetchall()
    meta_map = {r[0]: r for r in meta_rows}

    for row in rows:
        eid = row[0]
        meta = meta_map.get(eid, (eid, "", 0.5, "", "", ""))
        results.append({
            "entity_id": eid,
            "entity_type": row[1],
            "list_name": row[2] or "",
            "card_name": row[3] or "",
            "title": row[4] or "",
            "text": row[5] or "",
            "url": meta[1],
            "evidence_weight": meta[2],
            "updated_at": meta[3],
            "card_id": meta[4],
            "board_name": meta[5],
            "rank": row[6],
            "highlighted_text": row[5] or "",
            "search_query": query,
        })

    return results


def _deduplicate_chunks(results: list[dict]) -> list[dict]:
    seen_sigs: list[tuple] = []
    deduped: list[dict] = []

    for r in results:
        text = (r.get("text") or "")[:200].lower()
        card = r.get("card_id", "") or r.get("entity_id", "")
        sig = (card, text)
        is_dup = False
        for prev in seen_sigs:
            if sig[0] == prev[0] and len(sig[1]) > 10 and len(prev[1]) > 10:
                if sig[1][:100] == prev[1][:100]:
                    is_dup = True
                    break
        if not is_dup:
            seen_sigs.append(sig)
            deduped.append(r)

    return deduped


def _filter_low_content(chunks: list[dict], min_text_len: int = 50) -> list[dict]:
    filtered = []
    for c in chunks:
        text = c.get("text", "") or ""
        clean = re.sub(r"[\s\[\]\*\#]+", "", text).strip()
        if len(clean) >= min_text_len:
            filtered.append(c)
    return filtered


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
        start = first_match if first_match >= 0 else 0
        result = "..." + result[start : start + max_len] + "..."
    return result


def _build_chunk_text(r: dict) -> str:
    parts = []
    if r.get("card_name"):
        parts.append(f"[{r['card_name']}]")
    if r.get("list_name"):
        parts.append(f"({r['list_name']})")
    if r.get("section"):
        parts.append(f"[{r['section']}]")
    if parts:
        parts.append("")

    text = r.get("highlighted_text") or r.get("text", "")
    entity_type = r.get("entity_type", "")
    if entity_type == "action_snapshot":
        eid = r.get("entity_id", "")
        short_id = eid.split("_")[-1][:12] if eid else "unknown"
        text = f"[Historical snapshot: {short_id}]\n{text}"

    if len(text) > 800:
        text = text[:800] + "..."
    parts.append(text)
    return "\n".join(parts)


def build_evidence_pack(
    question: str,
    db_path: Path,
    max_chunks: int = 40,
    top_k_per_query: int = 30,
) -> dict:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    manifest = dict(conn.execute("SELECT key, value FROM trello_manifest").fetchall())
    source_sha256 = manifest.get("source_sha256", "")

    queries = _query_expand(question)
    print(f"  Expanding question into {len(queries)} queries...")

    all_results: list[dict] = []
    for q in queries:
        results = _fts_search(conn, q, top_k_per_query)
        all_results.extend(results)

    conn.close()

    all_results = _deduplicate_chunks(all_results)
    all_results = _filter_low_content(all_results)

    for r in all_results:
        weight = r.get("evidence_weight", 0.5)
        rank = abs(r.get("rank", 0))
        r["combined_score"] = weight * (1.0 / (1.0 + rank * 0.01))

    all_results.sort(key=lambda x: x["combined_score"], reverse=True)
    all_results = all_results[:max_chunks]

    chunks = []
    for i, r in enumerate(all_results):
        chunks.append({
            "chunk_id": f"chunk_{i:04d}",
            "entity_id": r["entity_id"],
            "entity_type": r["entity_type"],
            "card_name": r.get("card_name", ""),
            "list_name": r.get("list_name", ""),
            "section": r.get("section", ""),
            "text": _build_chunk_text(r),
            "url": r.get("url", ""),
            "evidence_weight": r.get("evidence_weight", 0.5),
            "combined_score": r.get("combined_score", 0.0),
            "search_query": r.get("search_query", ""),
        })

    pack = {
        "pack_id": f"EPACK-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "question": question,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "type": "trello",
            "sha256": source_sha256,
            "db_path": str(db_path.resolve()),
        },
        "retrieval": {
            "expanded_queries": queries,
            "total_candidates": len(all_results),
            "final_chunks": len(chunks),
            "max_chunks": max_chunks,
            "top_k_per_query": top_k_per_query,
        },
        "coverage": {
            "trello_zombie": any(
                "zombie" in (c.get("text", "") + c.get("card_name", "")).lower()
                for c in chunks
            ),
            "trello_gender": any(
                "gender" in (c.get("text", "") + c.get("card_name", "")).lower()
                for c in chunks
            ),
            "trello_ability_keys": any(
                k in (c.get("text", "") + c.get("card_name", "")).lower()
                for c in chunks
                for k in ["T", "G", "Z", "X", "C", "critical", "passive"]
            ),
            "trello_grip": any(
                "grip" in (c.get("text", "") + c.get("card_name", "")).lower()
                for c in chunks
            ),
            "trello_quest": any(
                k in (c.get("text", "") + c.get("card_name", "")).lower()
                for c in chunks
                for k in ["quest", "npc", "check", "count"]
            ),
        },
        "chunks": chunks,
    }

    return pack


def _pack_to_markdown(pack: dict) -> str:
    lines = [
        f"# Evidence Pack: {pack['pack_id']}",
        "",
        f"**Question:** {pack['question']}",
        f"**Created:** {pack['created_at']}",
        f"**Chunks:** {pack['retrieval']['final_chunks']} / {pack['retrieval']['total_candidates']} candidates",
        "",
        f"**Source SHA256:** `{pack['source']['sha256'][:16]}...`",
        "",
        f"## Retrieval Queries ({len(pack['retrieval']['expanded_queries'])})",
    ]
    for i, q in enumerate(pack["retrieval"]["expanded_queries"], 1):
        lines.append(f"  {i}. `{q}`")

    lines.extend(["", f"## Evidence Chunks ({len(pack['chunks'])})", ""])
    for chunk in pack["chunks"]:
        lines.append(f"### [{chunk['chunk_id']}] {chunk['card_name'] or chunk['entity_id']}")
        meta = []
        if chunk["list_name"]:
            meta.append(f"List: *{chunk['list_name']}*")
        if chunk["section"]:
            meta.append(f"Section: {chunk['section']}")
        meta.append(f"Type: `{chunk['entity_type']}`")
        meta.append(f"Weight: {chunk['evidence_weight']:.2f}")
        meta.append(f"Score: {chunk['combined_score']:.4f}")
        if chunk.get("url"):
            meta.append(f"URL: {chunk['url']}")
        lines.append("  " + " | ".join(meta))
        lines.append("")
        lines.append(f"```")
        lines.append(chunk["text"])
        lines.append(f"```")
        lines.append(f"Query: `{chunk['search_query']}`")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="Build a focused evidence pack for a research question"
    )
    parser.add_argument("--question", "-q", required=True)
    parser.add_argument("--db", "-d", required=True)
    parser.add_argument("--out", "-o", required=True)
    parser.add_argument("--markdown", help="Also write markdown version here")
    parser.add_argument("--max-chunks", "-m", type=int, default=40)
    parser.add_argument("--top-k", "-k", type=int, default=30)
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        sys.stderr.write(f"[ERROR] Database not found: {db_path}\n")
        sys.exit(1)

    print(f"Building evidence pack for question:\n  {args.question}\n  DB: {db_path}")

    pack = build_evidence_pack(
        args.question, db_path,
        max_chunks=args.max_chunks,
        top_k_per_query=args.top_k,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Wrote pack to: {out_path}")
    print(f"  Pack ID: {pack['pack_id']}")
    print(f"  Chunks: {pack['retrieval']['final_chunks']}")
    print(f"  Coverage: {pack['coverage']}")

    if args.markdown:
        md_path = Path(args.markdown)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(_pack_to_markdown(pack), encoding="utf-8")
        print(f"[OK] Markdown written to: {md_path}")


if __name__ == "__main__":
    main()
