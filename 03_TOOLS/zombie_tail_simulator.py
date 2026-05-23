"""
Zombie Quest - Tail Task Simulator
==================================

Scores the last "two-ish" Zombie quest tasks against every usable hint we have:

- SideCharacter: one reroll -> same-gender zombifying -> two randomized tail tasks
- Count hint: 50-ish, 57 is too much
- Image solve: BC = char, xy = mirror, bc = gender
- Appearance-copy screenshot
- Items/accessories are not needed

This is not a magic solver. It is a repeatable way to keep the guessing honest.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "03_TOOLS" / "zombie_test_runner" / "reports"


@dataclass(frozen=True)
class Evidence:
    key: str
    weight: float
    note: str


@dataclass(frozen=True)
class TailCandidate:
    id: str
    label: str
    tasks: tuple[str, str]
    prior: float
    supports: tuple[str, ...]
    contradicts: tuple[str, ...] = ()
    caution: str = ""


@dataclass
class ScoredCandidate:
    id: str
    label: str
    tasks: tuple[str, str]
    raw_score: float
    probability: float
    top1_rate: float
    support_score: float
    contradiction_score: float
    caution: str


def evidence_bank() -> dict[str, Evidence]:
    return {
        "one_reroll": Evidence("one_reroll", 3.0, "Only one gender reroll is needed; extra rerolls reset progress."),
        "same_gender_zombify": Evidence("same_gender_zombify", 3.0, "Zombification targets match the post-reroll gender."),
        "amount_50ish": Evidence("amount_50ish", 2.5, "The amount is 50-ish."),
        "below_57": Evidence("below_57", 1.8, "57 was called too much, so the count is below that."),
        "any_race": Evidence("any_race", 1.2, "Targets can be any race."),
        "not_unique": Evidence("not_unique", 1.2, "Targets do not have to be unique."),
        "passive_blood": Evidence("passive_blood", 1.5, "Zombie passive Blood Bar is involved in the zombifying step."),
        "manual_grip": Evidence("manual_grip", 1.7, "Manual grip is the clean zombification method."),
        "no_commands": Evidence("no_commands", 2.2, "Return/die/invade commands are not needed for the clean route."),
        "no_mode": Evidence("no_mode", 1.2, "No Volt/mode lock is part of the clean route."),
        "zombie_do_nothing": Evidence("zombie_do_nothing", 1.6, "Converted zombies do not need to act."),
        "tail_order_randomized": Evidence("tail_order_randomized", 1.8, "The two tail tasks are same for everyone but order can differ."),
        "after_zombify_tail": Evidence("after_zombify_tail", 2.0, "SideCharacter gave the order as reroll -> zombify -> ??? -> ???."),
        "bc_char": Evidence("bc_char", 3.5, "Image solution says BC uses the char rule."),
        "xy_mirror": Evidence("xy_mirror", 3.2, "Image solution says xy uses the mirror rule."),
        "bc_gender": Evidence("bc_gender", 3.2, "Image solution says bc uses the gender rule."),
        "appearance_copy_seen": Evidence("appearance_copy_seen", 3.0, "Screenshot shows one player copied another player's appearance."),
        "items_not_needed": Evidence("items_not_needed", 2.2, "Items/accessories are explicitly not needed."),
    }


def candidates() -> list[TailCandidate]:
    return [
        TailCandidate(
            "COPY_MIRROR_FINAL_GRIP",
            "Copy/mirror appearance, then same-gender final zombify",
            (
                "copy or mirror another player's character appearance after the count",
                "zombify/grip a same-gender target while that copied/mirrored relation is active",
            ),
            0.30,
            (
                "one_reroll",
                "same_gender_zombify",
                "amount_50ish",
                "below_57",
                "manual_grip",
                "passive_blood",
                "no_commands",
                "zombie_do_nothing",
                "tail_order_randomized",
                "after_zombify_tail",
                "bc_char",
                "xy_mirror",
                "bc_gender",
                "appearance_copy_seen",
                "items_not_needed",
            ),
            caution="Best fit, but exact direction is still unknown: actor copies target, target copies actor, or B/C copy each other.",
        ),
        TailCandidate(
            "BC_SAME_GENDER_CHAR_MIRROR",
            "B/C same-gender character mirror pair",
            (
                "make the relevant B/C players same gender after the one reroll route",
                "make their character appearance mirror/copy relation match before the final check",
            ),
            0.24,
            (
                "one_reroll",
                "same_gender_zombify",
                "amount_50ish",
                "below_57",
                "no_commands",
                "zombie_do_nothing",
                "tail_order_randomized",
                "after_zombify_tail",
                "bc_char",
                "xy_mirror",
                "bc_gender",
                "appearance_copy_seen",
                "items_not_needed",
            ),
            caution="Strong decode fit. It may be a state check rather than an extra kill/count check.",
        ),
        TailCandidate(
            "COPY_BEFORE_KEEP_ACTIVE",
            "Copy appearance before count and keep it active",
            (
                "copy/mirror appearance before starting the same-gender count",
                "keep the relation active through the x50-ish zombification loop",
            ),
            0.18,
            (
                "one_reroll",
                "same_gender_zombify",
                "amount_50ish",
                "below_57",
                "manual_grip",
                "passive_blood",
                "no_commands",
                "bc_char",
                "xy_mirror",
                "bc_gender",
                "appearance_copy_seen",
                "items_not_needed",
            ),
            ("after_zombify_tail",),
            "Very plausible mechanically, but it slightly fights the stated order of zombify -> ??? -> ???.",
        ),
        TailCandidate(
            "APPEARANCE_ONLY_CHECK",
            "Appearance copy as the whole tail",
            (
                "copy another player's character appearance",
                "talk/check NPC without items/accessory matching",
            ),
            0.11,
            (
                "one_reroll",
                "amount_50ish",
                "below_57",
                "no_commands",
                "after_zombify_tail",
                "bc_char",
                "xy_mirror",
                "appearance_copy_seen",
                "items_not_needed",
            ),
            ("same_gender_zombify", "bc_gender"),
            "Explains the screenshot, but underuses the same-gender zombification hint.",
        ),
        TailCandidate(
            "PASSIVE_GRIP_COUNTERS",
            "Passive Blood Bar and manual grip are the two tail counters",
            (
                "fill same-gender targets with passive Blood Bar",
                "manual-grip those same-gender targets into zombies",
            ),
            0.16,
            (
                "one_reroll",
                "same_gender_zombify",
                "amount_50ish",
                "below_57",
                "passive_blood",
                "manual_grip",
                "any_race",
                "not_unique",
                "no_commands",
                "zombie_do_nothing",
            ),
            ("bc_char", "xy_mirror", "appearance_copy_seen"),
            "Could be part of the zombifying phase rather than the two decoded tail tasks.",
        ),
        TailCandidate(
            "COUNT_ONLY",
            "The x50-ish same-gender count is all visible work",
            (
                "complete the true same-gender zombification amount",
                "perform the NPC/progress check after the amount",
            ),
            0.13,
            (
                "one_reroll",
                "same_gender_zombify",
                "amount_50ish",
                "below_57",
                "manual_grip",
                "any_race",
                "not_unique",
                "no_commands",
            ),
            ("bc_char", "xy_mirror", "bc_gender", "appearance_copy_seen"),
            "Good baseline, but it does not explain the new image solution.",
        ),
        TailCandidate(
            "BASE_TG_MOVES",
            "Base Zombie T/G move counters",
            (
                "use Splatter/T on same-gender targets",
                "use Self Infliction/G on same-gender targets",
            ),
            0.06,
            (
                "one_reroll",
                "same_gender_zombify",
                "tail_order_randomized",
                "no_commands",
            ),
            ("bc_char", "xy_mirror", "appearance_copy_seen", "zombie_do_nothing"),
            "Fallback only; current hints point to char/mirror/gender, not move names.",
        ),
        TailCandidate(
            "BASE_XC_MOVES",
            "Base Zombie X/C move counters",
            (
                "use Dancing Dead Boys/X on same-gender targets",
                "use Blood Drive/C on same-gender targets",
            ),
            0.04,
            (
                "one_reroll",
                "same_gender_zombify",
                "tail_order_randomized",
                "no_commands",
            ),
            ("bc_char", "xy_mirror", "appearance_copy_seen", "zombie_do_nothing"),
            "Lower fallback than T/G because no current hint points at X/C specifically.",
        ),
        TailCandidate(
            "COMMANDS",
            "Return/die command route",
            (
                "use return command after zombifying",
                "use die command after zombifying",
            ),
            0.02,
            ("one_reroll", "after_zombify_tail"),
            ("no_commands", "zombie_do_nothing", "bc_char", "xy_mirror", "appearance_copy_seen"),
            "Strongly contradicted by newer hints.",
        ),
        TailCandidate(
            "ITEM_ACCESSORY_MATCH",
            "Item/accessory cosplay match",
            (
                "match visible accessories/items",
                "talk/check NPC after cosmetic matching",
            ),
            0.02,
            ("bc_char", "appearance_copy_seen"),
            ("items_not_needed", "same_gender_zombify", "bc_gender"),
            "Explicitly downgraded because items/accessories are not needed.",
        ),
        TailCandidate(
            "OLD_MULTI_REROLL",
            "Old repeated-reroll A/B/C route",
            (
                "reroll between gender path blocks",
                "repeat the old A/B/C or 2x2 matrix",
            ),
            0.01,
            ("tail_order_randomized",),
            ("one_reroll", "same_gender_zombify", "bc_char", "xy_mirror", "appearance_copy_seen"),
            "Reset-risk route. Do not test first.",
        ),
    ]


def support_score(candidate: TailCandidate, bank: dict[str, Evidence], weights: dict[str, float] | None = None) -> float:
    weights = weights or {k: e.weight for k, e in bank.items()}
    return sum(weights[k] for k in candidate.supports if k in weights)


def contradiction_score(candidate: TailCandidate, bank: dict[str, Evidence], weights: dict[str, float] | None = None) -> float:
    weights = weights or {k: e.weight for k, e in bank.items()}
    return sum(weights[k] for k in candidate.contradicts if k in weights)


def raw_score(candidate: TailCandidate, bank: dict[str, Evidence], weights: dict[str, float] | None = None) -> float:
    prior_term = math.log(max(candidate.prior, 0.001))
    return prior_term + support_score(candidate, bank, weights) - 1.15 * contradiction_score(candidate, bank, weights)


def softmax(scores: list[float], temperature: float = 5.5) -> list[float]:
    scaled = [s / temperature for s in scores]
    m = max(scaled)
    exps = [math.exp(s - m) for s in scaled]
    total = sum(exps)
    return [e / total for e in exps]


def monte_carlo_top_rates(
    pool: list[TailCandidate],
    bank: dict[str, Evidence],
    runs: int = 5000,
    seed: int = 20260522,
) -> dict[str, float]:
    rng = random.Random(seed)
    wins = {c.id: 0 for c in pool}
    base_weights = {k: e.weight for k, e in bank.items()}

    for _ in range(runs):
        noisy = {
            k: max(0.1, rng.gauss(weight, max(0.15, weight * 0.18)))
            for k, weight in base_weights.items()
        }
        ranked = sorted(pool, key=lambda c: raw_score(c, bank, noisy), reverse=True)
        wins[ranked[0].id] += 1

    return {k: v / runs for k, v in wins.items()}


def score_candidates() -> list[ScoredCandidate]:
    bank = evidence_bank()
    pool = candidates()
    scores = [raw_score(c, bank) for c in pool]
    probs = softmax(scores)
    top_rates = monte_carlo_top_rates(pool, bank)
    scored = []
    for c, score, prob in zip(pool, scores, probs):
        scored.append(
            ScoredCandidate(
                c.id,
                c.label,
                c.tasks,
                score,
                prob,
                top_rates[c.id],
                support_score(c, bank),
                contradiction_score(c, bank),
                c.caution,
            )
        )
    scored.sort(key=lambda c: (-c.probability, -c.top1_rate, c.label))
    return scored


def count_distribution() -> list[dict]:
    # SideCharacter gave "50-ish" and 57 too much. Keep this intentionally simple.
    rows = [
        {"amount": 50, "probability": 0.48, "reason": "literal 50-ish and clean upper candidate below 57"},
        {"amount": 49, "probability": 0.25, "reason": "just under 50 if exact 50 was rounded upward"},
        {"amount": 45, "probability": 0.17, "reason": "still 50-ish but lower"},
        {"amount": 40, "probability": 0.10, "reason": "lower fallback if logs/counting are noisy"},
    ]
    total = sum(r["probability"] for r in rows)
    for row in rows:
        row["probability"] = row["probability"] / total
    return rows


def write_reports(scored: list[ScoredCandidate]) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = REPORT_DIR / f"tail_simulation_{stamp}.json"
    md_path = REPORT_DIR / f"tail_simulation_{stamp}.md"

    payload = {
        "generated": datetime.now().isoformat(),
        "evidence": [asdict(e) for e in evidence_bank().values()],
        "count_distribution": count_distribution(),
        "tail_candidates": [asdict(c) for c in scored],
        "best_route": {
            "steps": [
                "Use exactly one gender reroll.",
                "Zombify same-gender targets with passive Blood Bar -> knock -> manual grip.",
                "Check milestones at 40, 45, 49, and 50; top count is 50.",
                "For the two tail tasks, first test appearance copy/mirror plus same-gender final zombify.",
            ]
        },
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Zombie Tail Simulation",
        f"Generated: {payload['generated']}",
        "",
        "## Count Distribution",
        "",
        "| Amount | Probability | Reason |",
        "|---:|---:|---|",
    ]
    for row in count_distribution():
        lines.append(f"| {row['amount']} | {row['probability']:.1%} | {row['reason']} |")
    lines.extend(
        [
            "",
            "## Tail Candidate Ranking",
            "",
            "| # | Candidate | Probability | Top-1 Stability | Two Tasks |",
            "|---:|---|---:|---:|---|",
        ]
    )
    for i, c in enumerate(scored, 1):
        tasks = " + ".join(c.tasks)
        lines.append(f"| {i} | **{c.label}** | {c.probability:.1%} | {c.top1_rate:.1%} | {tasks} |")
    lines.extend(
        [
            "",
            "## Current Best Reading",
            "",
            "```text",
            "Gender reroll once",
            "-> same-gender zombify, most likely x50",
            "-> copy/mirror character appearance",
            "-> same-gender final zombify/check while that mirror relation is active",
            "```",
            "",
            "The key uncertainty is direction/order of the char mirror: actor copies target, target copies actor, or B/C copy each other.",
            "Do not prioritize items/accessories, commands, mode, or extra gender rerolls.",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def print_summary(scored: list[ScoredCandidate]):
    print("=" * 88)
    print("ZOMBIE QUEST TAIL SIMULATOR")
    print("=" * 88)
    print("\nCount candidates:")
    for row in count_distribution():
        print(f"  x{row['amount']:<2}  P={row['probability']:.1%}  {row['reason']}")

    print("\nTail candidates:")
    for i, c in enumerate(scored, 1):
        print(f"  #{i:<2} {c.label:<52} P={c.probability:.1%} stable_top1={c.top1_rate:.1%}")
        print(f"      A: {c.tasks[0]}")
        print(f"      B: {c.tasks[1]}")
        if c.caution:
            print(f"      caution: {c.caution}")

    best = scored[0]
    print("\nBest current answer:")
    print("  Gender reroll once")
    print("  -> same-gender zombify, most likely x50")
    print(f"  -> {best.tasks[0]}")
    print(f"  -> {best.tasks[1]}")


def main():
    scored = score_candidates()
    print_summary(scored)
    json_path, md_path = write_reports(scored)
    print("\nReports:")
    print(f"  {json_path}")
    print(f"  {md_path}")


if __name__ == "__main__":
    main()
