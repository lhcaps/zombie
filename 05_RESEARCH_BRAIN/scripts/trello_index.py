#!/usr/bin/env python3
"""
trello_index.py — Build SQLite FTS5 index from normalized Trello entities.

Usage:
    python trello_index.py --entities ../indexes/trello_entities.jsonl --db ../indexes/trello.db
    python trello_index.py --entities ../indexes/trello_entities.jsonl --db ../indexes/trello.db --rebuild
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def _init_db(db_path: Path, rebuild: bool = False) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")

    if rebuild:
        for table in [
            "trello_entities",
            "trello_fts",
            "trello_links",
            "trello_manifest",
        ]:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS trello_entities (
            entity_id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            board_id TEXT,
            board_name TEXT,
            list_id TEXT,
            list_name TEXT,
            card_id TEXT,
            card_name TEXT,
            title TEXT,
            text TEXT,
            url TEXT,
            source_path TEXT,
            source_sha256 TEXT,
            evidence_weight REAL DEFAULT 0.5,
            updated_at TEXT,
            metadata_json TEXT,
            searchable INTEGER DEFAULT 1
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_entities_type ON trello_entities(entity_type)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_entities_list ON trello_entities(list_name)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_entities_card ON trello_entities(card_name)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_entities_card_id ON trello_entities(card_id)
    """)

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS trello_fts USING fts5(
            entity_id UNINDEXED,
            entity_type,
            list_name,
            card_name,
            title,
            text,
            tokenize='unicode61 remove_diacritics 1'
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS trello_links (
            from_entity_id TEXT,
            to_entity_id TEXT,
            relation TEXT,
            weight REAL DEFAULT 1.0,
            PRIMARY KEY (from_entity_id, to_entity_id, relation)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS trello_manifest (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    conn.commit()
    return conn


def _insert_entity(conn: sqlite3.Connection, entity: dict) -> None:
    metadata = {
        k: v for k, v in entity.items()
        if k not in (
            "entity_id", "entity_type", "board_id", "board_name",
            "list_id", "list_name", "card_id", "card_name",
            "title", "text", "url", "source_path", "source_sha256",
            "evidence_weight", "updated_at", "searchable",
        )
    }

    text = entity.get("text", "") or ""
    # Only index in FTS if text is non-empty and long enough
    searchable = 1 if (text and len(text.strip()) > 10) else 0

    conn.execute("""
        INSERT OR REPLACE INTO trello_entities
        (entity_id, entity_type, board_id, board_name, list_id, list_name,
         card_id, card_name, title, text, url, source_path, source_sha256,
         evidence_weight, updated_at, metadata_json, searchable)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entity.get("entity_id"),
        entity.get("entity_type"),
        entity.get("board_id"),
        entity.get("board_name"),
        entity.get("list_id"),
        entity.get("list_name"),
        entity.get("card_id"),
        entity.get("card_name"),
        entity.get("title") or entity.get("card_name", ""),
        text,
        entity.get("url", ""),
        entity.get("source_path", ""),
        entity.get("source_sha256", ""),
        entity.get("evidence_weight", 0.5),
        entity.get("updated_at", ""),
        json.dumps(metadata) if metadata else None,
        searchable,
    ))


def _rebuild_fts(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM trello_fts")
    conn.execute("""
        INSERT INTO trello_fts(entity_id, entity_type, list_name, card_name, title, text)
        SELECT entity_id, entity_type, list_name, card_name, title, text
        FROM trello_entities
        WHERE searchable = 1
    """)
    conn.commit()


def _build_links(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM trello_links")
    conn.execute("""
        INSERT OR IGNORE INTO trello_links(from_entity_id, to_entity_id, relation, weight)
        SELECT e1.entity_id, e2.entity_id, 'same_card', e1.evidence_weight * e2.evidence_weight
        FROM trello_entities e1
        JOIN trello_entities e2
            ON e1.card_id = e2.card_id
            AND e1.entity_id != e2.entity_id
            AND e1.entity_type = 'chunk'
            AND e2.entity_type = 'card'
    """)
    conn.commit()


def _update_manifest(conn: sqlite3.Connection, stats: dict) -> None:
    manifest_entries = [
        ("version", "1.0"),
        ("indexed_at", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
        ("source_sha256", stats.get("source_sha256", "")),
        ("total_entities", str(stats.get("total_entities", 0))),
        ("entity_counts", json.dumps(stats.get("entity_counts", {}))),
    ]
    for key, value in manifest_entries:
        conn.execute(
            "INSERT OR REPLACE INTO trello_manifest(key, value) VALUES (?, ?)",
            (key, value),
        )
    conn.commit()


def index_entities(
    entities_path: Path,
    db_path: Path,
    rebuild: bool = False,
) -> dict:
    conn = _init_db(db_path, rebuild)

    entities = []
    with open(entities_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entities.append(json.loads(line))

    print(f"Indexing {len(entities)} entities...")

    entity_counts: dict[str, int] = {}
    source_sha256 = ""
    for i, entity in enumerate(entities):
        _insert_entity(conn, entity)
        t = entity.get("entity_type", "unknown")
        entity_counts[t] = entity_counts.get(t, 0) + 1
        if not source_sha256:
            source_sha256 = entity.get("source_sha256", "")
        if (i + 1) % 500 == 0:
            print(f"  Processed {i + 1}/{len(entities)}...")

    conn.commit()
    print("  Building FTS5 index...")
    _rebuild_fts(conn)
    print("  Building entity links...")
    _build_links(conn)

    stats = {
        "source_sha256": source_sha256,
        "total_entities": len(entities),
        "entity_counts": entity_counts,
        "searchable_entities": sum(1 for e in entities if e.get("text", "") and len((e.get("text", "") or "").strip()) > 10),
    }
    _update_manifest(conn, stats)

    row = conn.execute(
        "SELECT COUNT(*) FROM trello_entities"
    ).fetchone()
    fts_row = conn.execute(
        "SELECT COUNT(*) FROM trello_fts"
    ).fetchone()
    searchable_row = conn.execute(
        "SELECT COUNT(*) FROM trello_entities WHERE searchable = 1"
    ).fetchone()

    conn.close()

    return {
        **stats,
        "db_entities_indexed": row[0] if row else 0,
        "fts_entries": fts_row[0] if fts_row else 0,
        "searchable_entities": searchable_row[0] if searchable_row else stats.get("searchable_entities", 0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SQLite FTS5 index from Trello entities")
    parser.add_argument(
        "--entities", "-e", required=True,
        help="Path to trello_entities.jsonl"
    )
    parser.add_argument(
        "--db", "-d", required=True,
        help="Output path for SQLite database"
    )
    parser.add_argument(
        "--rebuild", action="store_true",
        help="Drop existing tables and rebuild from scratch"
    )
    args = parser.parse_args()

    entities_path = Path(args.entities)
    db_path = Path(args.db)

    if not entities_path.exists():
        sys.stderr.write(f"[ERROR] Entities file not found: {entities_path}\n")
        sys.exit(1)

    print(f"Indexing entities from: {entities_path}")
    print(f"Database: {db_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    stats = index_entities(entities_path, db_path, args.rebuild)

    print(f"\nIndex built successfully:")
    print(f"  Total entities: {stats['total_entities']}")
    for t, c in sorted(stats.get("entity_counts", {}).items()):
        print(f"    {t}: {c}")
    print(f"  DB rows: {stats['db_entities_indexed']}")
    print(f"  FTS entries: {stats['fts_entries']}")
    print(f"  SHA256: {stats['source_sha256'][:16]}...")


if __name__ == "__main__":
    main()
