"""
Zombie Quest - Analysis Engine
==============================

Bayesian-ish analysis for the updated one-reroll model. This does not magically
solve the quest without in-game evidence; it keeps the next test honest.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from zombie_csp_model import ProbabilityEngine, ZombCSP, make_engine, make_model
from zombie_test_generator import CoverageTracker


if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


@dataclass
class Hypothesis:
    id: str
    name: str
    description: str
    prior_p: float
    supports: list[str]
    risks: list[str]
    posterior_p: float = 0.0
    status: str = "active"

    def update(self, results: list[dict]):
        relevant = [r for r in results if r.get("hypothesis") == self.id or r.get("pair_id") == self.id]
        if not relevant:
            self.posterior_p = self.prior_p
            return
        passes = sum(1 for r in relevant if norm_outcome(r.get("outcome")) == "PASS")
        fails = sum(1 for r in relevant if norm_outcome(r.get("outcome")) == "FAIL")
        if passes:
            self.posterior_p = min(0.95, self.prior_p + 0.18 * passes)
            self.status = "confirmed" if passes else "active"
        elif fails:
            self.posterior_p = max(0.01, self.prior_p * (0.55 ** fails))
        else:
            self.posterior_p = self.prior_p


@dataclass
class AnalysisResult:
    timestamp: str
    total_tests: int
    pass_count: int
    fail_count: int
    blocked_count: int
    pass_rate: float
    next_best: list[dict]
    insights: list[str]
    recommendations: list[str]


def norm_outcome(value: str | None) -> str:
    return (value or "").strip().upper()


class AnalysisEngine:
    def __init__(self, csp: ZombCSP | None = None, engine: ProbabilityEngine | None = None):
        self.csp = csp or make_model()
        self.eng = engine or make_engine(self.csp)
        self.hypotheses = self._init_hypotheses()

    def _init_hypotheses(self) -> list[Hypothesis]:
        return [
            Hypothesis(
                "CHAR_MIRROR",
                "Appearance Mirror / Character Copy",
                "The BC/xy/bc solve points to B/C character appearance copying plus mirror/gender constraints. Items and accessories are not the requirement.",
                0.42,
                ["BC=char", "xy=mirror", "bc=gender", "appearance-copy screenshot", "items/accessories not needed"],
                ["Need exact direction: actor copies target, target copies actor, or B/C copy each other"],
            ),
            Hypothesis(
                "PASSIVE_GRIP",
                "Passive Blood Bar + Manual Grip Are The Two Hidden Counters",
                "The game may split the same zombification loop into passive Blood Bar credit and manual-grip zombie credit.",
                0.20,
                ["Directly named by hints", "No commands", "No race lock", "Zombie does nothing"],
                ["Likely part of the zombifying phase, not the newly decoded char/mirror tail"],
            ),
            Hypothesis(
                "COUNT_ONLY",
                "One Reroll + Same-Gender Zombification Amount Completes It",
                "The two tail slots may be internal bookkeeping/order, while the only real player-visible work is the same-gender amount.",
                0.16,
                ["SideCharacter emphasized the zombification amount", "57 too much implies count is the key"],
                ["Does not explain BC=char and xy=mirror"],
            ),
            Hypothesis(
                "T_G_BASE",
                "Two Base Zombie Move Counters: T + G",
                "After the same-gender amount, the remaining tasks may be base Zombie move counters.",
                0.07,
                ["Fits two-ish tasks with same amount", "T/G were repeatedly tested in older logs"],
                ["New clue points to appearance/gender/mirror, not moves"],
            ),
            Hypothesis(
                "X_C_BASE",
                "Two Base Zombie Move Counters: X + C",
                "A lower-priority move-pair fallback after T/G.",
                0.03,
                ["Still base Zombie-kit actions"],
                ["No hint points specifically to X/C"],
            ),
            Hypothesis(
                "COMMANDS",
                "Return/Die Commands",
                "Old community tests used commands after zombifying.",
                0.01,
                ["Historically tested often"],
                ["Contradicted by commands-not-needed and zombie-does-nothing hints"],
            ),
            Hypothesis(
                "OLD_MULTI_REROLL",
                "Old A/B/C Or 2x2 Multi-Reroll Routes",
                "Previous CSP model with repeated gender swaps.",
                0.01,
                ["Fit older CSP reading"],
                ["SideCharacter says repeated rerolls are doing it wrong and resetting progress"],
                status="ruled_out",
            ),
        ]

    def analyze_results(self, results: list[dict]) -> AnalysisResult:
        usable = [r for r in results if r.get("test_type") in {"core_count", "unknown_pair"}]
        total = len(usable)
        passes = sum(1 for r in usable if norm_outcome(r.get("outcome")) == "PASS")
        fails = sum(1 for r in usable if norm_outcome(r.get("outcome")) == "FAIL")
        blocked = sum(1 for r in usable if norm_outcome(r.get("outcome")) == "BLOCKED")

        for h in self.hypotheses:
            h.update(usable)

        next_best = self._next_best(usable)
        insights = self._insights(usable, passes, fails)
        recs = self._recommendations(usable, next_best)
        return AnalysisResult(
            timestamp=datetime.now().isoformat(),
            total_tests=total,
            pass_count=passes,
            fail_count=fails,
            blocked_count=blocked,
            pass_rate=(passes / total) if total else 0.0,
            next_best=next_best,
            insights=insights,
            recommendations=recs,
        )

    def _next_best(self, results: list[dict]) -> list[dict]:
        tested = {(r.get("test_type"), r.get("spec")) for r in results}
        out = []
        for t in self.eng.ranked_tests(100):
            if (t["type"], t["spec"]) in tested:
                continue
            out.append(
                {
                    "type": t["type"],
                    "spec": t["spec"],
                    "label": t["label"],
                    "p": t["p"],
                    "ig": t["info_gain"],
                    "score": t["score"],
                    "reason": self._reason(t["type"], t["spec"]),
                }
            )
        return out[:10]

    def _reason(self, test_type: str, spec: str) -> str:
        parsed = self.eng.parse_spec(spec)
        if test_type == "core_count":
            return f"confirm same-gender amount x{parsed['amount']} after one reroll"
        pair = self.eng._pair(parsed["pair_id"])
        return f"probe tail pair: {pair.label}"

    def _insights(self, results: list[dict], passes: int, fails: int) -> list[str]:
        if not results:
            return [
                "Current hard constraint: one gender reroll total, then same-gender zombification.",
                "Old A/B/C and 2x2 multi-reroll routes are reset-risk and should not be tested first.",
                "New image solve adds BC=char, xy=mirror, bc=gender; this promotes appearance mirror / character copy as the top tail hypothesis.",
                "Best count probe is staged: check at 40, 45, 49, and 50 during one clean same-gender run.",
            ]

        insights = []
        pass_specs = [r.get("spec") for r in results if norm_outcome(r.get("outcome")) == "PASS"]
        fail_specs = [r.get("spec") for r in results if norm_outcome(r.get("outcome")) == "FAIL"]
        if pass_specs:
            insights.append(f"Passing specs: {pass_specs}. Stop broad testing and isolate shared constraints.")
        if fail_specs:
            insights.append(f"Failed specs: {fail_specs}. Do not add rerolls; change one variable at a time.")
        if fails and not passes:
            insights.append("Failures with the clean route push attention toward count precision or post-count tail tasks.")
        top = sorted(self.hypotheses, key=lambda h: -h.posterior_p)[0]
        insights.append(f"Top hypothesis now: {top.name} (P={top.posterior_p:.2f}).")
        return insights

    def _recommendations(self, results: list[dict], next_best: list[dict]) -> list[str]:
        if not results:
            return [
                "Run CORE_M_50 or CORE_F_50 depending on the actor's post-reroll gender.",
                "During that same run, log NPC checks at 40, 45, 49, and 50 to discover the real amount without extra resets.",
                "If the count alone does not pass, test the CHAR_MIRROR tail pair before passive/grip bookkeeping, commands, or mode routes.",
            ]
        if next_best:
            top = next_best[0]
            return [f"Next priority: {top['label']} (P={top['p']:.3f}, IG={top['ig']:.1f} bits)."]
        return ["All updated cases have results. Review pass/fail clusters manually."]

    def hypothesis_report(self) -> str:
        for h in self.hypotheses:
            if h.posterior_p == 0.0:
                h.posterior_p = h.prior_p
        rows = sorted(self.hypotheses, key=lambda h: -h.posterior_p)
        lines = [
            "# Zombie Quest - Updated Hypothesis Analysis",
            f"**Updated:** {datetime.now().isoformat()}",
            "",
            "| # | Hypothesis | Prior | Posterior | Status |",
            "|---:|---|---:|---:|---|",
        ]
        for i, h in enumerate(rows, 1):
            lines.append(f"| {i} | **{h.name}** | {h.prior_p:.2f} | {h.posterior_p:.3f} | {h.status} |")
            lines.append(f"| | {h.description} | | | |")
        return "\n".join(lines)

    def full_report(self, results: list[dict]) -> str:
        ar = self.analyze_results(results)
        lines = [
            "# Zombie Quest - Full Updated Analysis Report",
            f"**Generated:** {ar.timestamp}",
            "",
            "## Summary",
            f"- Total updated-model tests: {ar.total_tests}",
            f"- Passed: {ar.pass_count}",
            f"- Failed: {ar.fail_count}",
            f"- Blocked: {ar.blocked_count}",
            f"- Pass rate: {ar.pass_rate:.1%}",
            "",
            "## Current Best Quest Shape",
            "",
            "```text",
            "Gender reroll exactly once",
            "-> zombify N same-gender targets, any race, not necessarily unique",
            "-> tail task A/B: likely character appearance copy / mirror relation",
            "```",
            "",
            "Newest clue: image solve found BC (char), xy (mirror), and bc (gender). The third screenshot shows appearance copying; items/accessories remain ruled out.",
            "",
            "Best current N prior: 50, with milestone checks at 40/45/49/50 because 57 was called too much.",
            "",
            "## Key Insights",
            "",
        ]
        lines.extend(f"- {x}" for x in ar.insights)
        lines.extend(["", "## Recommendations", ""])
        lines.extend(f"- {x}" for x in ar.recommendations)
        lines.extend(
            [
                "",
                "## Next Best Tests",
                "",
                "| Type | Spec | P(success) | Info Gain | Reason |",
                "|---|---|---:|---:|---|",
            ]
        )
        for nb in ar.next_best[:8]:
            lines.append(f"| {nb['type']} | **{nb['spec']}** | {nb['p']:.4f} | {nb['ig']:.1f} | {nb['reason']} |")
        lines.extend(["", self.hypothesis_report()])
        return "\n".join(lines)

    def save_report(self, results: list[dict], path: Path) -> Path:
        path.write_text(self.full_report(results), encoding="utf-8")
        return path


class IterativeTester:
    def __init__(self, tracker: CoverageTracker, dispatcher, analysis: AnalysisEngine):
        self.tracker = tracker
        self.dispatcher = dispatcher
        self.analysis = analysis

    def step(self) -> dict | None:
        case = self.tracker.next_case()
        if not case:
            return None
        return {
            "case_id": case.case_id,
            "type": case.test_type,
            "spec": case.spec,
            "label": case.label,
            "steps": case.steps,
            "constraints": case.constraints,
            "probability": case.probability,
            "info_gain": case.info_gain,
        }

    def record(self, case_id: str, outcome: str, notes: str = ""):
        self.tracker.mark_tested(case_id, outcome, notes)


if __name__ == "__main__":
    out = Path(r"D:\Study\Project\zombie\03_TOOLS\zombie_test_runner")
    engine = AnalysisEngine()
    print(engine.full_report([]))
