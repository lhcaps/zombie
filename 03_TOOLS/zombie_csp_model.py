"""
Zombie Quest - CSP Model & Probability Engine
=============================================

Current model after the SideCharacter update:

    gender reroll once -> same-gender zombification amount -> unknown task A -> unknown task B

The old A/B/C path and multi-reroll 2x2 matrix are intentionally obsolete.
Those routes are now treated as reset-risk patterns, not priorities.
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field
from enum import Enum, auto


if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


class Gender(Enum):
    M = "M"
    F = "F"

    @property
    def label(self) -> str:
        return "Male" if self is Gender.M else "Female"


class Outcome(Enum):
    UNTESTED = auto()
    PASS = auto()
    FAIL = auto()
    BLOCKED = auto()
    UNKNOWN = auto()


@dataclass(frozen=True)
class CountCandidate:
    amount: int
    confidence: float
    reason: str


@dataclass(frozen=True)
class UnknownTaskPair:
    id: str
    label: str
    tasks: tuple[str, str]
    confidence: float
    reason: str
    violates: tuple[str, ...] = ()


@dataclass
class ZombCSP:
    """Small functional CSP for the updated Zombie quest."""

    genders: tuple[Gender, Gender] = (Gender.M, Gender.F)
    counts: tuple[CountCandidate, ...] = field(default_factory=tuple)
    unknown_pairs: tuple[UnknownTaskPair, ...] = field(default_factory=tuple)

    @classmethod
    def make(cls) -> "ZombCSP":
        return cls(
            counts=(
                CountCandidate(
                    50,
                    0.42,
                    "SideCharacter said the amount is 50-ish and 57 is too much.",
                ),
                CountCandidate(
                    49,
                    0.23,
                    "Just under 50; useful if '50-ish' means capped below 50.",
                ),
                CountCandidate(
                    45,
                    0.15,
                    "Conservative 50-ish fallback while still high-count.",
                ),
                CountCandidate(
                    40,
                    0.08,
                    "Lower bound check if 45/49/50 fail or logging was noisy.",
                ),
            ),
            unknown_pairs=(
                UnknownTaskPair(
                    "CHAR_MIRROR",
                    "Appearance Mirror / Character Copy",
                    (
                        "copy or mirror another player's character appearance without item/accessory requirements",
                        "zombify a same-gender target while the character-copy/mirror relation is active",
                    ),
                    0.55,
                    "New image solution says BC=char, xy=mirror, bc=gender; screenshot evidence shows appearance copying while items/accessories are not needed.",
                ),
                UnknownTaskPair(
                    "PASSIVE_GRIP",
                    "Passive Blood Bar + Manual Grip",
                    ("same-gender passive Blood Bar buildup", "same-gender manual grip zombification"),
                    0.22,
                    "Directly matches Blood Bar passive/manual grip, but new BC/xy/bc clue makes it more likely these are the zombification mechanism rather than both tail tasks.",
                ),
                UnknownTaskPair(
                    "COUNT_ONLY",
                    "Same-Gender Zombification Count Only",
                    ("same-gender zombification amount", "NPC progress check after the full amount"),
                    0.14,
                    "The two unknowns may be bookkeeping around the same zombification loop rather than extra mechanics.",
                ),
                UnknownTaskPair(
                    "T_G_BASE",
                    "Base T/G After Count",
                    ("Splatter/T hits on same-gender targets", "Self Infliction/G hits on same-gender targets"),
                    0.06,
                    "If two tasks remain after zombifying, base Zombie moves are possible, but the new clue points harder at character/gender/mirror logic.",
                ),
                UnknownTaskPair(
                    "X_C_BASE",
                    "Base X/C After Count",
                    ("Dancing Dead Boys/X hits on same-gender targets", "Blood Drive/C hits on same-gender targets"),
                    0.03,
                    "Secondary Zombie-move pair. Lower because older broad move tests were noisy and no-mode does not imply all moves.",
                ),
                UnknownTaskPair(
                    "COMMANDS",
                    "Return/Die Commands",
                    ("return command", "die command"),
                    0.01,
                    "Old logs tried commands, but newer hints say commands are not needed.",
                    violates=("no_commands", "zombie_do_nothing"),
                ),
            ),
        )

    @property
    def all_final_genders(self) -> list[Gender]:
        return list(self.genders)

    @property
    def all_counts(self) -> list[CountCandidate]:
        return list(self.counts)

    @property
    def all_unknown_pairs(self) -> list[UnknownTaskPair]:
        return list(self.unknown_pairs)


@dataclass
class TestResult:
    """One test execution record."""

    run_id: str
    test_type: str
    spec: str = ""
    pair_sequence: list[str] = field(default_factory=list)
    path: str = ""
    rotation: str = ""
    blocks: list[dict] = field(default_factory=list)
    use_passive: bool = True
    use_manual_grip: bool = True
    gender_swap_between_blocks: bool = False
    outcome: Outcome = Outcome.UNTESTED
    notes: str = ""
    timestamp: str = ""
    ai_agent: str = ""
    duration_min: float = 0.0

    def summary(self) -> str:
        return f"[{self.run_id}] {self.test_type} | spec={self.spec} | outcome={self.outcome.name}"


@dataclass(frozen=True)
class ConstraintWeight:
    name: str
    description: str
    weight: float
    satisfied: bool = False


class ProbabilityEngine:
    """Scores updated tests using the latest hard constraints."""

    CONSTRAINTS = {
        "h1": ConstraintWeight("one_gender_reroll", "Exactly one gender reroll total for the clean route", 1.0, True),
        "h2": ConstraintWeight("same_gender_targets", "Zombification targets match the post-reroll gender", 1.0, True),
        "h3": ConstraintWeight("manual_grip", "Zombification is through manual grip", 1.0, True),
        "h4": ConstraintWeight("passive_Blood_Bar", "Blood Bar passive is involved", 1.0, True),
        "h5": ConstraintWeight("any_race", "Targets can be any race", 1.0, True),
        "h6": ConstraintWeight("no_commands", "Zombie commands are not needed", 1.0, True),
        "h7": ConstraintWeight("zombie_do_nothing", "Zombies do not need to act", 1.0, True),
        "h8": ConstraintWeight("no_Volt_mode", "Can be done in base; no Volt/mode lock", 1.0, True),
        "s1": ConstraintWeight("amount_50ish", "Zombification amount is 50-ish but below 57", 0.9, True),
        "s2": ConstraintWeight("randomized_tail_order", "The final two tasks are same for everyone but order can differ", 0.8, True),
        "s3": ConstraintWeight("functional_CSP", "A small function-like constraint table, not literal CS", 0.7, True),
        "s4": ConstraintWeight("char_mirror", "BC/xy/bc clue points to character-copy plus mirror/gender constraints", 0.9, True),
        "s5": ConstraintWeight("appearance_not_items", "Appearance copying is relevant, but items/accessories are not required", 0.8, True),
    }

    def __init__(self, csp: ZombCSP | None = None):
        self.csp = csp or ZombCSP.make()

    def p_core_count(self, amount: int, final_gender: str) -> float:
        count = self._count(amount)
        gender_factor = 1.0
        if final_gender not in {"M", "F"}:
            gender_factor = 0.5
        return min(count.confidence * gender_factor, 1.0)

    def p_unknown_pair(self, pair_id: str, amount: int, final_gender: str) -> float:
        pair = self._pair(pair_id)
        count_p = self.p_core_count(amount, final_gender)
        violation_penalty = 0.35 ** len(pair.violates)
        return min(count_p * pair.confidence * violation_penalty, 1.0)

    def p_combined_route(self, test_type: str, spec: str) -> float:
        parsed = self.parse_spec(spec)
        if test_type == "core_count":
            return self.p_core_count(parsed["amount"], parsed["gender"])
        if test_type == "unknown_pair":
            return self.p_unknown_pair(parsed["pair_id"], parsed["amount"], parsed["gender"])
        return 0.0

    def expected_info_gain(self, test_type: str, spec: str) -> float:
        p = self.p_combined_route(test_type, spec)
        if p <= 0:
            return 0.0
        return -math.log2(p)

    def ranked_tests(self, max_tests: int = 20) -> list[dict]:
        tests: list[dict] = []

        for gender in self.csp.all_final_genders:
            for count in self.csp.all_counts:
                spec = f"{gender.value}_{count.amount}"
                p = self.p_core_count(count.amount, gender.value)
                ig = self.expected_info_gain("core_count", spec)
                tests.append(
                    {
                        "type": "core_count",
                        "spec": spec,
                        "label": f"Core Same-Gender x{count.amount} ({gender.label})",
                        "p": p,
                        "info_gain": ig,
                        "score": p * ig,
                        "blocks": self._core_blocks(gender, count.amount),
                    }
                )

        for gender in self.csp.all_final_genders:
            for pair in self.csp.all_unknown_pairs:
                # Use 50 for the post-count probe first; lower counts are covered by core milestone checks.
                amount = 50
                spec = f"{gender.value}_{amount}_{pair.id}"
                p = self.p_unknown_pair(pair.id, amount, gender.value)
                ig = self.expected_info_gain("unknown_pair", spec)
                tests.append(
                    {
                        "type": "unknown_pair",
                        "spec": spec,
                        "label": f"{pair.label} after x{amount} ({gender.label})",
                        "p": p,
                        "info_gain": ig,
                        "score": p * ig,
                        "blocks": self._unknown_blocks(gender, amount, pair),
                    }
                )

        tests.sort(key=lambda x: (-x["score"], -x["p"], x["label"]))
        return tests[:max_tests]

    def parse_spec(self, spec: str) -> dict:
        parts = spec.split("_")
        gender = parts[0]
        amount = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 50
        pair_id = "_".join(parts[2:]) if len(parts) > 2 else ""
        return {"gender": gender, "amount": amount, "pair_id": pair_id}

    def count_probabilities(self) -> dict[int, float]:
        return {c.amount: c.confidence for c in self.csp.all_counts}

    def unknown_pair_probabilities(self) -> dict[str, float]:
        return {p.id: p.confidence for p in self.csp.all_unknown_pairs}

    def _count(self, amount: int) -> CountCandidate:
        for c in self.csp.all_counts:
            if c.amount == amount:
                return c
        return CountCandidate(amount, 0.02, "Unlisted count candidate.")

    def _pair(self, pair_id: str) -> UnknownTaskPair:
        for p in self.csp.all_unknown_pairs:
            if p.id == pair_id:
                return p
        return UnknownTaskPair(pair_id, pair_id, ("unknown task A", "unknown task B"), 0.02, "Unlisted pair.")

    def _core_blocks(self, final_gender: Gender, amount: int) -> list[dict]:
        return [
            {
                "step": 1,
                "phase": "gender_reroll",
                "actor": "quest_holder",
                "target": "-",
                "action": f"Use exactly one gender reroll so actor final gender is {final_gender.label}.",
            },
            {
                "step": 2,
                "phase": "same_gender_zombify",
                "actor": final_gender.value,
                "target": final_gender.value,
                "repeat": f"x{amount}",
                "action": "For each same-gender target: passive Blood Bar -> knock -> manual grip -> confirm zombie.",
            },
            {
                "step": 3,
                "phase": "milestone_checks",
                "actor": "quest_holder",
                "target": "-",
                "action": "Check NPC only at safe milestones: 40, 45, 49, 50, then stop before extra rerolls.",
            },
        ]

    def _unknown_blocks(self, final_gender: Gender, amount: int, pair: UnknownTaskPair) -> list[dict]:
        blocks = self._core_blocks(final_gender, amount)
        blocks.extend(
            [
                {
                    "step": 4,
                    "phase": "unknown_task_a",
                    "actor": final_gender.value,
                    "target": final_gender.value,
                    "repeat": "same fixed amount if measurable",
                    "action": pair.tasks[0],
                },
                {
                    "step": 5,
                    "phase": "unknown_task_b",
                    "actor": final_gender.value,
                    "target": final_gender.value,
                    "repeat": "same fixed amount if measurable",
                    "action": pair.tasks[1],
                },
                {
                    "step": 6,
                    "phase": "check",
                    "actor": "quest_holder",
                    "target": "-",
                    "action": "Check Jugram/Balance. If failed, swap the order of task A/B only.",
                },
            ]
        )
        return blocks


def make_model() -> ZombCSP:
    return ZombCSP.make()


def make_engine(csp: ZombCSP | None = None) -> ProbabilityEngine:
    return ProbabilityEngine(csp)


if __name__ == "__main__":
    csp = make_model()
    eng = make_engine(csp)
    print("=" * 70)
    print("  ZOMBIE QUEST - UPDATED CSP MODEL")
    print("=" * 70)
    print("\nKnown route skeleton:")
    print("  one gender reroll -> same-gender zombify amount -> unknown task A -> unknown task B")
    print("\nCount candidates:")
    for c in csp.all_counts:
        print(f"  x{c.amount:<2} P={c.confidence:.2f}  {c.reason}")
    print("\nUnknown task-pair candidates:")
    for p in csp.all_unknown_pairs:
        print(f"  {p.id:<14} P={p.confidence:.2f}  {p.label}")
    print("\nTop ranked tests:")
    for i, test in enumerate(eng.ranked_tests(12), 1):
        print(f"  #{i:<2} {test['label']:<48} P={test['p']:.4f} IG={test['info_gain']:.2f} score={test['score']:.4f}")
