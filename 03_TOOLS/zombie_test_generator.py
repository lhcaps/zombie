"""
Zombie Quest - Test Case Generator & Coverage Tracker
====================================================

Generates test cases for the updated SideCharacter model:
one gender reroll, same-gender zombification amount, then two possible tail tasks.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from zombie_csp_model import make_engine, make_model


if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


@dataclass
class TestCase:
    case_id: str
    test_type: str
    spec: str
    label: str
    description: str
    steps: list[dict]
    constraints: list[str]
    probability: float = 0.0
    info_gain: float = 0.0
    score: float = 0.0
    priority: int = 0
    status: str = "untested"


@dataclass
class CoverageDimension:
    name: str
    description: str
    total: int
    covered: int = 0

    @property
    def pct(self) -> float:
        return (self.covered / self.total * 100.0) if self.total else 0.0


class CoverageTracker:
    """Tracks generated test cases and recorded outcomes."""

    HARD_RULES = [
        "Exactly one gender reroll for the clean route.",
        "After the reroll, zombify same-gender targets only.",
        "Targets can be any race and do not need to be unique.",
        "Use passive Blood Bar whenever possible.",
        "Every zombification must be manual grip.",
        "No return/die/invade commands for clean tests.",
        "Zombies do not need to do anything.",
        "No Volt/mode requirement for clean tests.",
        "Do not add a second gender reroll unless deliberately resetting after a failed route.",
    ]

    def __init__(self, out_dir: Path):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.out_dir / "coverage_log.json"

        self.csp = make_model()
        self.eng = make_engine(self.csp)
        self.dims: dict[str, CoverageDimension] = {}
        self.cases: list[TestCase] = []

        self._init_dimensions()
        self._generate_all_cases()
        self._load()

    def _init_dimensions(self):
        self.dims = {
            "final_gender": CoverageDimension("final_gender", "Post-reroll actor gender", 2),
            "count": CoverageDimension("count", "Same-gender zombification amount candidates", len(self.csp.all_counts)),
            "unknown_pair": CoverageDimension("unknown_pair", "Candidate pair for the two tail tasks", len(self.csp.all_unknown_pairs)),
            "core_count": CoverageDimension("core_count", "Core count-only routes tested", len(self.csp.all_counts) * 2),
            "tail_probe": CoverageDimension("tail_probe", "Post-count unknown-pair probes tested", len(self.csp.all_unknown_pairs) * 2),
        }

    def _generate_all_cases(self):
        cases: list[TestCase] = []
        for item in self.eng.ranked_tests(100):
            spec = item["spec"]
            case_id = self._case_id(item["type"], spec)
            desc = self._description(item["type"], spec, item["label"])
            cases.append(
                TestCase(
                    case_id=case_id,
                    test_type=item["type"],
                    spec=spec,
                    label=item["label"],
                    description=desc,
                    steps=item["blocks"],
                    constraints=list(self.HARD_RULES),
                    probability=item["p"],
                    info_gain=item["info_gain"],
                    score=item["score"],
                )
            )

        cases.sort(key=lambda c: (-c.score, -c.probability, c.label))
        for i, case in enumerate(cases, 1):
            case.priority = i
        self.cases = cases

    def _case_id(self, test_type: str, spec: str) -> str:
        prefix = "CORE" if test_type == "core_count" else "TAIL"
        return f"{prefix}_{spec}"

    def _description(self, test_type: str, spec: str, label: str) -> str:
        parsed = self.eng.parse_spec(spec)
        gender = "Male" if parsed["gender"] == "M" else "Female"
        if test_type == "core_count":
            return (
                f"Use one gender reroll so the actor is {gender}, then zombify "
                f"{parsed['amount']} same-gender targets through passive Blood Bar and manual grip."
            )
        pair = self.eng._pair(parsed["pair_id"])
        return (
            f"After the one-reroll x{parsed['amount']} same-gender zombification core, "
            f"probe the tail pair: {pair.tasks[0]} + {pair.tasks[1]}."
        )

    def _load(self):
        if not self.log_file.exists():
            return
        try:
            data = json.loads(self.log_file.read_text(encoding="utf-8"))
        except Exception:
            return
        status_by_id = {entry.get("case_id"): entry.get("status", "tested") for entry in data.get("results", [])}
        for case in self.cases:
            if case.case_id in status_by_id:
                case.status = status_by_id[case.case_id]
        self._recompute_dimensions()

    def _save(self):
        self._recompute_dimensions()
        data = {
            "saved_at": datetime.now().isoformat(),
            "dimensions": {
                name: {"total": dim.total, "covered": dim.covered, "pct": dim.pct}
                for name, dim in self.dims.items()
            },
            "results": [
                {"case_id": c.case_id, "test_type": c.test_type, "spec": c.spec, "status": c.status}
                for c in self.cases
                if c.status != "untested"
            ],
        }
        self.log_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def mark_tested(self, case_id: str, outcome: str, notes: str = ""):
        outcome = outcome.lower()
        for case in self.cases:
            if case.case_id == case_id:
                case.status = outcome
                self._save()
                return
        raise ValueError(f"Unknown case_id: {case_id}")

    def _recompute_dimensions(self):
        tested = [c for c in self.cases if c.status != "untested"]
        final_genders = {self.eng.parse_spec(c.spec)["gender"] for c in tested}
        counts = {self.eng.parse_spec(c.spec)["amount"] for c in tested}
        pairs = {
            self.eng.parse_spec(c.spec)["pair_id"]
            for c in tested
            if c.test_type == "unknown_pair"
        }
        self.dims["final_gender"].covered = len(final_genders)
        self.dims["count"].covered = len(counts)
        self.dims["unknown_pair"].covered = len(pairs)
        self.dims["core_count"].covered = sum(1 for c in tested if c.test_type == "core_count")
        self.dims["tail_probe"].covered = sum(1 for c in tested if c.test_type == "unknown_pair")

    def coverage_report(self) -> str:
        self._recompute_dimensions()
        lines = [
            "# Zombie Quest - Updated Coverage Report",
            f"**Saved:** {datetime.now().isoformat()}",
            "",
            "## Coverage Dimensions",
            "",
            "| Dimension | Covered | Total | Pct |",
            "|---|---:|---:|---:|",
        ]
        for dim in self.dims.values():
            lines.append(f"| {dim.name} | {dim.covered} | {dim.total} | {dim.pct:.1f}% |")

        lines.extend(
            [
                "",
                "## Test Cases",
                "",
                "| # | Type | Spec | Label | P(success) | IG | Status |",
                "|---:|---|---|---|---:|---:|---|",
            ]
        )
        for case in self.cases:
            lines.append(
                f"| {case.priority} | {case.test_type} | **{case.spec}** | {case.label} | "
                f"{case.probability:.4f} | {case.info_gain:.2f} | {case.status} |"
            )
        return "\n".join(lines)

    def save_coverage_report(self) -> Path:
        path = self.out_dir / f"coverage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        path.write_text(self.coverage_report(), encoding="utf-8")
        return path

    def untested_cases(self) -> list[TestCase]:
        return [c for c in self.cases if c.status == "untested"]

    def next_case(self) -> TestCase | None:
        cases = self.untested_cases()
        return cases[0] if cases else None

    def all_cases(self) -> list[TestCase]:
        return list(self.cases)

    def cases_by_type(self, test_type: str) -> list[TestCase]:
        return [c for c in self.cases if c.test_type == test_type]


if __name__ == "__main__":
    out = Path(r"D:\Study\Project\zombie\03_TOOLS\zombie_test_runner")
    tracker = CoverageTracker(out)
    print(f"Generated {len(tracker.cases)} updated test cases")
    print(f"Untested: {len(tracker.untested_cases())}")
    print(f"Coverage report: {tracker.save_coverage_report()}")
    for case in tracker.untested_cases()[:12]:
        print(f"  #{case.priority} {case.case_id}: {case.label} P={case.probability:.4f}")
