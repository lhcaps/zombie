#!/usr/bin/env python3
"""
ingest_sources.py — Ingest a new source document into the Research Brain.

Usage:
    python ingest_sources.py --path ../01_SOURCES/new_doc.md --title "My Note"
    python ingest_sources.py --path ../01_SOURCES/ --title "Bulk ingest"
    python ingest_sources.py --list
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from core import (
    RB_DIR, source_registry_path, detect_source_type, next_source_id,
    utc_now, section, subsection, bullet, info, ok, warn, load_json, save_json,
)


def _read_source_content(path: Path) -> tuple[str, list[str]]:
    """Extract text content and key findings from a source file."""
    if path.suffix.lower() == ".pdf":
        return _read_pdf(path)
    if path.suffix.lower() == ".docx":
        return _read_docx(path)
    if path.suffix.lower() == ".json":
        return _read_json(path)
    return _read_text(path)


def _read_text(path: Path) -> tuple[str, list[str]]:
    content = path.read_text(encoding="utf-8", errors="replace")
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    findings = []
    for line in lines[:20]:
        if len(line) > 20:
            findings.append(line[:120])
    return content, findings


def _read_pdf(path: Path) -> tuple[str, list[str]]:
    try:
        import pypdf

        reader = pypdf.PdfReader(path)
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text())
        content = "\n".join(text_parts)
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        findings = [l[:120] for l in lines[:15] if len(l) > 20]
        return content, findings
    except ImportError:
        warn("pypdf not installed; reading as binary")
        return f"[PDF binary content — {path.name}]", [f"PDF file: {path.name}"]


def _read_docx(path: Path) -> tuple[str, list[str]]:
    try:
        from docx import Document

        doc = Document(path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        content = "\n".join(paragraphs)
        findings = [p[:120] for p in paragraphs[:15] if len(p) > 20]
        return content, findings
    except ImportError:
        warn("python-docx not installed; reading as zip")
        return f"[DOCX binary content — {path.name}]", [f"DOCX file: {path.name}"]


def _read_json(path: Path) -> tuple[str, list[str]]:
    data = load_json(path)
    content = json.dumps(data, indent=2, ensure_ascii=False)
    findings = []
    if isinstance(data, dict):
        for key in list(data.keys())[:10]:
            val = data[key]
            if isinstance(val, str):
                findings.append(f"{key}: {val[:100]}")
            elif isinstance(val, list):
                findings.append(f"{key}: {len(val)} items")
            elif isinstance(val, (int, float, bool)):
                findings.append(f"{key}: {val}")
    return content, findings


def ingest_file(path: Path, title: str | None, added_by: str = "manual") -> dict:
    """Ingest a single file and add to registry."""
    registry = load_json(source_registry_path())
    sources = registry.get("sources", [])

    src_type = detect_source_type(path)
    src_id = next_source_id(sources)
    content, findings = _read_source_content(path)

    now = utc_now()
    source_entry = {
        "source_id": src_id,
        "source_path": str(path),
        "source_type": src_type,
        "title": title or path.name,
        "summary": "",
        "key_findings": findings,
        "contradictions_detected": [],
        "tags": _infer_tags(path, content, src_type),
        "ingested_at": now,
        "added_by": added_by,
        "notes": "",
        "_content_preview": content[:500],
    }

    sources.append(source_entry)
    registry["sources"] = sources
    save_json(source_registry_path(), registry)

    return source_entry


def _infer_tags(path: Path, content: str, src_type: str) -> list[str]:
    tags = [src_type]
    content_lower = content.lower()
    keywords = {
        "gender": ["gender", "reroll", "male", "female"],
        "character_mirror": ["mirror", "character copy", "appearance copy", "bc", "xy"],
        "count": ["count", "zombify", "amount", "50", "49", "45", "40"],
        "commands": ["command", "return", "die", "invade"],
        "mode": ["volt", "mode", "lock"],
        "hint": ["hint", "clue", "screenshot", "image"],
        "test": ["test", "fail", "pass", "result"],
        "zombie": ["zombie", "zombify", "blood bar", "grip"],
        "quest": ["quest", "npc", "check", "complete"],
    }
    for tag, kws in keywords.items():
        if any(kw in content_lower for kw in kws):
            tags.append(tag)
    return list(set(tags))


def list_sources() -> None:
    """List all registered sources."""
    registry = load_json(source_registry_path())
    sources = registry.get("sources", [])
    section(f"Sources ({len(sources)} total)")
    for src in sources:
        print(f"\n  [{src['source_id']}] {src['title']}")
        bullet(f"Type: {src['source_type']}")
        bullet(f"Path: {src['source_path']}")
        bullet(f"Ingested: {src['ingested_at']}")
        bullet(f"Tags: {', '.join(src['tags'])}")
        findings = src.get("key_findings", [])
        if findings:
            bullet(f"Findings ({len(findings)}):")
            for f in findings[:3]:
                print(f"        - {f[:100]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest source documents into Research Brain")
    parser.add_argument("--path", type=str, help="Path to file or directory to ingest")
    parser.add_argument("--title", type=str, help="Human-readable title for the source")
    parser.add_argument("--added-by", type=str, default="manual", help="Who added this (manual/agent-name)")
    parser.add_argument("--list", action="store_true", help="List all registered sources")
    args = parser.parse_args()

    if args.list:
        list_sources()
        return

    if not args.path:
        parser.print_help()
        return

    target = Path(args.path)
    if not target.exists():
        warn(f"Path does not exist: {target}")
        return

    section("Ingest Sources")

    if target.is_dir():
        files = []
        for ext in ("*.md", "*.txt", "*.json", "*.pdf", "*.docx"):
            files.extend(target.rglob(ext))
        files.sort()
        for f in files:
            if any(excluded in str(f) for excluded in ["node_modules", "__pycache__", ".git"]):
                continue
            try:
                entry = ingest_file(f, None, args.added_by)
                ok(f"Ingested {entry['source_id']}: {entry['title']}")
            except Exception as e:
                warn(f"Failed to ingest {f}: {e}")
    else:
        entry = ingest_file(target, args.title, args.added_by)
        subsection(f"Source Registered")
        print(f"\n  Source ID:    {entry['source_id']}")
        print(f"  Title:        {entry['title']}")
        print(f"  Type:         {entry['source_type']}")
        print(f"  Tags:         {', '.join(entry['tags'])}")
        print(f"  Findings:     {len(entry['key_findings'])} extracted")
        print(f"  Ingested at:  {entry['ingested_at']}")
        print(f"\n  Next: Run extract_claims.py --source-id {entry['source_id']}")
        ok("Source ingested successfully")


if __name__ == "__main__":
    main()
