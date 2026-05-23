#!/usr/bin/env python3
"""
trello_normalize.py — Extract clean, deduplicated entities from Trello raw JSON.

Layer 0 → Layer 1: raw JSON → canonical entities with evidence weights.

Entity types: card, list, label, attachment, action, comment

Usage:
    python trello_normalize.py --input ../trello.txt --out ../indexes/trello_entities.jsonl
    python trello_normalize.py --input ../trello.txt --out ../indexes/trello_entities.jsonl --skip-actions
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# --- Evidence weight table (from design doc) ---
_EVIDENCE_WEIGHTS = {
    "card_current_desc": 1.0,
    "card_checklist_item": 0.9,
    "card_attachment_caption": 0.8,
    "card_comment": 0.7,
    "action_card_snapshot": 0.35,
    "action_old_desc": 0.15,
    "board_admin_metadata": 0.05,
    "board_social": 0.03,
}


def _clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"\[\!\[.*?\]\(.*?\)\]\(.*?\)", "", text)
    text = re.sub(r"!\[\]\(https://trello\.com/.*?\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\(https://trello\.com[^\)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _entity_id(prefix: str, raw_id: str) -> str:
    return f"trello_{prefix}_{raw_id}"


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_labels(raw_labels: list[dict]) -> list[dict]:
    labels = []
    for lbl in raw_labels:
        labels.append({
            "id": lbl.get("id", ""),
            "name": lbl.get("name", ""),
            "color": lbl.get("color", ""),
            "uses": lbl.get("uses", 0),
        })
    return labels


def _extract_attachments(raw_attachments: list[dict]) -> list[dict]:
    attachments = []
    for att in raw_attachments:
        attachments.append({
            "id": att.get("id", ""),
            "name": _clean_text(att.get("name", "")),
            "url": att.get("url", ""),
            "bytes": att.get("bytes", 0),
            "mime_type": att.get("mimeType", ""),
            "is_upload": att.get("isUpload", False),
        })
    return attachments


def _dedupe_action_descs(actions: list[dict]) -> dict[str, dict]:
    seen_descs: dict[str, dict] = {}
    for action in actions:
        if action.get("type") != "updateCard":
            continue
        data = action.get("data", {})
        card_data = data.get("card", {})
        old_data = data.get("old", {})
        card_id = card_data.get("id", "")
        if not card_id:
            continue
        old_desc = old_data.get("desc", "")
        new_desc = card_data.get("desc", "")
        key = (card_id, old_desc, new_desc)
        if key not in seen_descs:
            seen_descs[key] = {
                "card_id": card_id,
                "card_name": card_data.get("name", ""),
                "old_desc": old_desc,
                "new_desc": new_desc,
                "date": action.get("date", ""),
                "action_id": action.get("id", ""),
            }
    return seen_descs


def _section_chunks(text: str, max_size: int = 1500) -> list[dict]:
    chunks = []
    if not text or len(text) < 50:
        return [{"chunk_type": "full", "text": text, "section": ""}]

    lines = text.split("\n")
    current = []
    current_size = 0
    section_name = ""

    for line in lines:
        stripped = line.strip()
        is_heading = bool(re.match(r"^#{1,3}\s+", stripped)) or bool(
            re.match(r"^\*\*[^*]+\*\*[\s:]*$", stripped)
        )

        if is_heading and current:
            chunk_text = _clean_text("\n".join(current))
            if chunk_text:
                chunks.append({
                    "chunk_type": "section",
                    "text": chunk_text,
                    "section": section_name or "general",
                })
            current = []
            current_size = 0

        if is_heading:
            section_name = re.sub(r"^#{1,3}\s+|\*\*", "", stripped).strip()

        current.append(line)
        current_size += len(line)

        if current_size >= max_size and current:
            chunk_text = _clean_text("\n".join(current))
            if chunk_text:
                chunks.append({
                    "chunk_type": "section",
                    "text": chunk_text,
                    "section": section_name or "general",
                })
            current = []
            current_size = 0

    if current:
        chunk_text = _clean_text("\n".join(current))
        if chunk_text:
            chunks.append({
                "chunk_type": "section",
                "text": chunk_text,
                "section": section_name or "general",
            })

    if not chunks:
        chunks.append({"chunk_type": "full", "text": _clean_text(text), "section": "general"})

    return chunks


def normalize_board(raw_data: dict, source_path: str, source_sha256: str) -> list[dict]:
    entities = []

    list_lookup = {lst["id"]: lst for lst in raw_data.get("lists", [])}
    label_lookup = {lbl["id"]: lbl for lbl in raw_data.get("labels", [])}

    for card in raw_data.get("cards", []):
        card_id = card.get("id", "")
        list_id = card.get("idList", "")
        list_info = list_lookup.get(list_id, {})
        list_name = list_info.get("name", "unknown")

        card_labels = [
            {"id": l["id"], "name": l.get("name", ""), "color": l.get("color", "")}
            for l in card.get("labels", [])
        ]
        card_attachments = _extract_attachments(card.get("attachments", []))

        evidence_weight = _EVIDENCE_WEIGHTS["card_current_desc"]

        # Main card entity
        card_text = _clean_text(card.get("desc", ""))
        card_entity = {
            "entity_id": _entity_id("card", card_id),
            "entity_type": "card",
            "board_id": raw_data.get("id", ""),
            "board_name": raw_data.get("name", ""),
            "list_id": list_id,
            "list_name": list_name,
            "card_id": card_id,
            "card_name": _clean_text(card.get("name", "")),
            "text": card_text,
            "labels": card_labels,
            "attachments": card_attachments,
            "attachment_count": len(card_attachments),
            "source_path": source_path,
            "source_sha256": source_sha256,
            "evidence_weight": evidence_weight,
            "updated_at": card.get("dateLastActivity", ""),
            "closed": card.get("closed", False),
            "pos": card.get("pos", 0),
        }
        entities.append(card_entity)

        # Section chunks for long cards
        if card_text and len(card_text) > 200:
            for i, chunk in enumerate(_section_chunks(card.get("desc", ""))):
                if chunk["text"] and len(chunk["text"]) > 50:
                    chunk_entity = {
                        "entity_id": _entity_id("chunk", f"{card_id}_sec{i}"),
                        "entity_type": "chunk",
                        "parent_card_id": card_id,
                        "board_id": raw_data.get("id", ""),
                        "board_name": raw_data.get("name", ""),
                        "list_id": list_id,
                        "list_name": list_name,
                        "card_name": _clean_text(card.get("name", "")),
                        "chunk_type": chunk["chunk_type"],
                        "section": chunk["section"],
                        "text": chunk["text"],
                        "labels": card_labels,
                        "source_path": source_path,
                        "source_sha256": source_sha256,
                        "evidence_weight": evidence_weight * 0.95,
                        "updated_at": card.get("dateLastActivity", ""),
                    }
                    entities.append(chunk_entity)

        # Attachment entities
        for att in card_attachments:
            att_entity = {
                "entity_id": _entity_id("attachment", att["id"]),
                "entity_type": "attachment",
                "parent_card_id": card_id,
                "card_name": _clean_text(card.get("name", "")),
                "list_name": list_name,
                "title": att["name"],
                "text": att["name"],
                "url": att["url"],
                "mime_type": att["mime_type"],
                "file_size": att["bytes"],
                "source_path": source_path,
                "source_sha256": source_sha256,
                "evidence_weight": _EVIDENCE_WEIGHTS["card_attachment_caption"],
                "updated_at": card.get("dateLastActivity", ""),
            }
            entities.append(att_entity)

    # List entities
    for lst in raw_data.get("lists", []):
        lst_entity = {
            "entity_id": _entity_id("list", lst.get("id", "")),
            "entity_type": "list",
            "board_id": raw_data.get("id", ""),
            "board_name": raw_data.get("name", ""),
            "list_id": lst.get("id", ""),
            "list_name": lst.get("name", ""),
            "text": lst.get("name", ""),
            "source_path": source_path,
            "source_sha256": source_sha256,
            "evidence_weight": 0.3,
            "closed": lst.get("closed", False),
            "pos": lst.get("pos", 0),
        }
        entities.append(lst_entity)

    # Label entities
    for lbl in raw_data.get("labels", []):
        lbl_entity = {
            "entity_id": _entity_id("label", lbl.get("id", "")),
            "entity_type": "label",
            "board_id": raw_data.get("id", ""),
            "board_name": raw_data.get("name", ""),
            "list_name": "",
            "text": f"{lbl.get('color', '')}: {lbl.get('name', '')}",
            "label_name": lbl.get("name", ""),
            "label_color": lbl.get("color", ""),
            "label_uses": lbl.get("uses", 0),
            "source_path": source_path,
            "source_sha256": source_sha256,
            "evidence_weight": 0.2,
        }
        entities.append(lbl_entity)

    # Action snapshot entities (only updateCard with old.desc)
    deduped_descs = _dedupe_action_descs(raw_data.get("actions", []))
    for key, snap in deduped_descs.items():
        if snap["old_desc"] and len(snap["old_desc"]) > 30:
            snap_entity = {
                "entity_id": _entity_id("action_snap", snap["action_id"]),
                "entity_type": "action_snapshot",
                "parent_card_id": snap["card_id"],
                "card_name": snap["card_name"],
                "list_name": "",
                "text": _clean_text(snap["old_desc"]),
                "source_path": source_path,
                "source_sha256": source_sha256,
                "evidence_weight": _EVIDENCE_WEIGHTS["action_old_desc"],
                "action_date": snap["date"],
            }
            entities.append(snap_entity)

    return entities


def generate_manifest(raw_data: dict, entities: list[dict], source_path: str, source_sha256: str) -> dict:
    entity_types: dict[str, int] = {}
    for e in entities:
        t = e.get("entity_type", "unknown")
        entity_types[t] = entity_types.get(t, 0) + 1

    return {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "path": source_path,
            "sha256": source_sha256,
            "board_name": raw_data.get("name", ""),
            "board_id": raw_data.get("id", ""),
        },
        "raw_counts": {
            "cards": len(raw_data.get("cards", [])),
            "lists": len(raw_data.get("lists", [])),
            "actions": len(raw_data.get("actions", [])),
            "labels": len(raw_data.get("labels", [])),
            "members": len(raw_data.get("members", [])),
        },
        "entity_counts": entity_types,
        "total_entities": len(entities),
        "search_topics": [
            "zombie_candidates",
            "gender_appearance_candidates",
            "ability_keys_candidates",
            "grip_execute_candidates",
            "quest_obtainment_candidates",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize Trello raw JSON into clean canonical entities"
    )
    parser.add_argument("--input", "-i", required=True, help="Path to raw Trello JSON file")
    parser.add_argument("--out", "-o", required=True, help="Output path for .jsonl entities")
    parser.add_argument(
        "--skip-actions",
        action="store_true",
        help="Skip action snapshot extraction (faster, less coverage)",
    )
    parser.add_argument(
        "--manifest",
        "-m",
        help="Optional path to write manifest JSON alongside entities",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.stderr.write(f"[ERROR] Input file not found: {input_path}\n")
        sys.exit(1)

    print(f"Loading raw Trello JSON from: {input_path}")
    raw_data = json.loads(input_path.read_text(encoding="utf-8"))
    source_sha256 = _sha256_of_file(input_path)
    print(f"  SHA256: {source_sha256[:16]}...")
    print(f"  Board: {raw_data.get('name', 'unknown')}")
    print(f"  Raw cards: {len(raw_data.get('cards', []))}")
    print(f"  Raw lists: {len(raw_data.get('lists', []))}")
    print(f"  Raw actions: {len(raw_data.get('actions', []))}")

    print("Normalizing entities...")
    entities = normalize_board(raw_data, str(input_path.resolve()), source_sha256)

    type_counts: dict[str, int] = {}
    for e in entities:
        t = e.get("entity_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, c in sorted(type_counts.items()):
        print(f"  {t}: {c}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing {len(entities)} entities to: {out_path}")
    written = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for entity in entities:
            f.write(json.dumps(entity, ensure_ascii=False) + "\n")
            written += 1
    print(f"  Wrote {written} entity records")

    if args.manifest:
        manifest_path = Path(args.manifest)
        manifest = generate_manifest(raw_data, entities, str(input_path.resolve()), source_sha256)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Manifest written to: {manifest_path}")

    print("[OK] Normalization complete")


if __name__ == "__main__":
    main()
