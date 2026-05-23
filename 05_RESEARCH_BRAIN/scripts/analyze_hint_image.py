#!/usr/bin/env python3
"""
analyze_hint_image.py — Extract visual claims from hint images.

Uses vision-capable LLM to analyze images and extract game mechanics claims.

Usage:
    python analyze_hint_image.py --image path/to/hint.png --out ../indexes/image_claims.jsonl
    python analyze_hint_image.py --image path/to/grid.png --out ../indexes/image_claims.jsonl --analysis-type critical_grid
    python analyze_hint_image.py --dir ../01_SOURCES/images/ --out ../indexes/all_image_claims.jsonl
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from core import RB_DIR, utc_now


def _encode_image(image_path: Path) -> str | None:
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


def _call_vision_llm(
    image_path: Path,
    analysis_type: str = "general",
    model: str = "gpt-4o",
) -> str | None:
    b64_image = _encode_image(image_path)
    if not b64_image:
        return None

    prompts = {
        "general": (
            "Analyze this game hint image carefully. "
            "Extract ALL text, symbols, patterns, arrows, colors, and visual elements. "
            "What game mechanics, steps, or relationships does this image suggest? "
            "Be precise about any text you can read and any visual patterns."
        ),
        "critical_grid": (
            "Analyze this critical grid or matrix image. "
            "Extract ALL text, symbols, labels, and patterns. "
            "Identify any move keys (T, G, Z, X, C, M2, Critical, Passive), "
            "arrows, groupings, or structural patterns. "
            "Describe the exact layout and what each element represents."
        ),
        "character_pair": (
            "Analyze this image showing character pairs or relationships. "
            "Extract labels like 'bc', 'xy', 'character', 'mirror', 'same', 'opposite'. "
            "What do the character positions, colors, or labels suggest about "
            "gender, race, or pairing mechanics?"
        ),
        "hint_sequence": (
            "Analyze this hint image showing a sequence or steps. "
            "Extract numbered steps, arrows, directional indicators, "
            "and any text. What order of operations does this suggest?"
        ),
    }

    prompt = prompts.get(analysis_type, prompts["general"])

    try:
        import openai
        import os
        if not os.environ.get("OPENAI_API_KEY"):
            return None

        client = openai.OpenAI()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64_image}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ]
        resp = client.chat.completions.create(model=model, messages=messages, temperature=0.1)
        return resp.choices[0].message.content
    except Exception as e:
        sys.stderr.write(f"[WARN] Vision LLM call failed: {e}\n")
        return None


def _call_anthropic_vision(image_path: Path, analysis_type: str = "general") -> str | None:
    b64_image = _encode_image(image_path)
    if not b64_image:
        return None

    prompts = {
        "general": "Analyze this game hint image carefully. Extract ALL text, symbols, patterns, arrows, colors, and visual elements. What game mechanics or relationships does this image suggest? Be precise.",
        "critical_grid": "Analyze this critical grid image. Extract ALL text, symbols, labels, move keys (T, G, Z, X, C, M2, Critical, Passive), arrows, and patterns. Describe the exact layout.",
        "character_pair": "Analyze this character pair image. Extract labels like 'bc', 'xy', 'character', 'mirror', 'same', 'opposite'. What do the positions suggest?",
        "hint_sequence": "Analyze this hint sequence image. Extract numbered steps, arrows, directional indicators, and text. What order does this suggest?",
    }

    prompt = prompts.get(analysis_type, prompts["general"])

    try:
        import anthropic
        import os
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return None

        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-7-latest",
            max_tokens=4096,
            system="You are a meticulous game mechanics analyst.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": b64_image,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        return resp.content[0].text
    except Exception as e:
        sys.stderr.write(f"[WARN] Anthropic vision call failed: {e}\n")
        return None


def _extract_claims_from_analysis(
    analysis: str,
    image_path: Path,
    analysis_type: str,
) -> list[dict]:
    claims = []

    claim_patterns = [
        (r"\b(bc|xy)\b.*?(?:character|rule|match|mirror)", "character_rule", 0.85, "image_analysis"),
        (r"\b(zombie|zombif)\b", "zombie_mechanic", 0.8, "image_analysis"),
        (r"\b(blood|grip)\b", "blood_grip_mechanic", 0.7, "image_analysis"),
        (r"\b(gender|reroll|same|opposite)\b", "gender_mechanic", 0.7, "image_analysis"),
        (r"\b(mirror|copy|appearance)\b", "appearance_mechanic", 0.7, "image_analysis"),
        (r"\b(character|bc|xy)\b", "character_pair", 0.6, "image_analysis"),
        (r"\b(T|G|Z|X|C|M2|Critical|Passive|Mode)\b", "ability_keys", 0.8, "image_analysis"),
        (r"\b(40|45|49|50|count|step)\b", "count_mechanic", 0.6, "image_analysis"),
    ]

    matched_tags = set()
    for pattern, tag, conf, _ in claim_patterns:
        if re.search(pattern, analysis, re.IGNORECASE):
            matched_tags.add(tag)

    if matched_tags:
        claim_text = f"Image analysis ({image_path.name}): " + analysis[:300]
        claims.append({
            "claim_id": f"IMG-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "source_type": "hint_image",
            "source_path": str(image_path.resolve()),
            "analysis_type": analysis_type,
            "claim": claim_text,
            "type": "observation",
            "polarity": "neutral",
            "confidence": 0.75,
            "evidence": analysis[:500],
            "status": "pending_review",
            "contradicts": [],
            "supported_by": [],
            "tags": list(matched_tags),
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "notes": "Extracted from vision model analysis",
        })

    return claims


def analyze_image(
    image_path: Path,
    analysis_type: str = "general",
) -> tuple[str, list[dict]]:
    print(f"  Analyzing: {image_path.name} (type: {analysis_type})")

    response = _call_vision_llm(image_path, analysis_type)
    if not response:
        response = _call_anthropic_vision(image_path, analysis_type)

    if not response:
        sys.stderr.write(f"[WARN] No vision API available for {image_path}\n")
        return "", []

    claims = _extract_claims_from_analysis(response, image_path, analysis_type)
    print(f"    Extracted {len(claims)} claims")

    return response, claims


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze hint images and extract visual claims"
    )
    parser.add_argument(
        "--image", "-i",
        help="Path to a single image file"
    )
    parser.add_argument(
        "--dir", "-d",
        help="Process all images in a directory"
    )
    parser.add_argument(
        "--out", "-o", required=True,
        help="Output path for extracted claims (.jsonl)"
    )
    parser.add_argument(
        "--analysis-type", "-t",
        choices=["general", "critical_grid", "character_pair", "hint_sequence"],
        default="general",
        help="Type of analysis to perform"
    )
    args = parser.parse_args()

    image_paths: list[Path] = []
    if args.image:
        image_paths = [Path(args.image)]
    elif args.dir:
        image_dir = Path(args.dir)
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp"):
            image_paths.extend(image_dir.glob(ext))
    else:
        sys.stderr.write("[ERROR] Must provide --image or --dir\n")
        sys.exit(1)

    if not image_paths:
        sys.stderr.write("[WARN] No images found\n")
        sys.exit(0)

    all_claims = []
    all_analyses = {}

    for img_path in sorted(image_paths):
        if not img_path.exists():
            continue
        analysis, claims = analyze_image(img_path, args.analysis_type)
        if analysis:
            all_analyses[img_path.name] = analysis
        all_claims.extend(claims)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for c in all_claims:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"[OK] Wrote {len(all_claims)} claims from {len(all_analyses)} images to {out_path}")
    for c in all_claims:
        print(f"  [{c['claim_id']}] tags={c['tags']}")


if __name__ == "__main__":
    main()
