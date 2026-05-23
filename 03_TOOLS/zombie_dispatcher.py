"""
Zombie Quest — Multi-Agent Task Dispatcher
==========================================
Spawns AI sub-agents to execute tests in parallel.
Each agent gets a unique test assignment with full context.
"""
from __future__ import annotations
import sys as _sys, os as _os
if _sys.platform == "win32":
    try: _os.environ["PYTHONIOENCODING"] = "utf-8"; _sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
import uuid
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterator, Callable
from threading import Lock

from zombie_csp_model import (
    ZombCSP, ProbabilityEngine, Outcome, TestResult,
    make_model, make_engine
)


# ── Agent Config ─────────────────────────────────────────────────────────────

@dataclass
class AgentConfig:
    """Configuration for a single AI agent worker."""
    name:        str
    model:       str   = "claude-sonnet-4"
    max_retries: int   = 2
    timeout_min: float = 30.0
    persona:     str   = "game_tester"
    enabled:     bool  = True


# ── Task Assignment ──────────────────────────────────────────────────────────

@dataclass
class TaskAssignment:
    """One test task to be dispatched to an AI agent."""
    task_id:    str
    agent_id:   str
    test_type:  str           # "core_count" | "unknown_pair"
    spec:       str           # e.g. "FMF" or "MMMM"
    label:      str           # human-readable label
    blocks:     list[dict]    # step-by-step blocks
    hard_rules: list[str]
    probability: float
    info_gain:  float
    score:      float
    context_md: str           # full context to give the AI agent
    created_at: str          = ""
    status:     str           = "pending"  # pending|assigned|running|done|failed
    result:     TestResult | None = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


# ── Dispatcher ───────────────────────────────────────────────────────────────

class MultiAgentDispatcher:
    """
    Manages a pool of AI agents and dispatches test tasks to them.
    Each agent runs independently and reports results back.

    Architecture:
      dispatcher
        ├── AgentWorker  (spawns sub-agents via Task tool)
        ├── TaskQueue    (pending tasks)
        ├── ResultStore  (completed results)
        └── CoverageMap  (what's been tested)
    """

    def __init__(
        self,
        out_dir: Path,
        max_agents: int = 4,
        enable_subagents: bool = True,
    ):
        self.out_dir    = Path(out_dir)
        self.max_agents = max_agents
        self.enable_subagents = enable_subagents

        self.csp   = make_model()
        self.eng   = make_engine(self.csp)

        # Agent pool
        self.agents: list[AgentConfig] = [
            AgentConfig(name=f"agent_{i}", enabled=True)
            for i in range(max_agents)
        ]

        # Task queue
        self._queue: list[TaskAssignment] = []
        self._queue_lock = Lock()

        # Results store
        self._results: list[TestResult] = []
        self._results_lock = Lock()

        # Coverage map
        self._coverage: dict[str, dict] = {}

        # Agent task assignments
        self._agent_tasks: dict[str, TaskAssignment] = {}

        # Setup dirs
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_dir    = self.out_dir / "tasks"
        self.results_dir  = self.out_dir / "results"
        self.reports_dir  = self.out_dir / "reports"
        for d in [self.tasks_dir, self.results_dir, self.reports_dir]:
            d.mkdir(parents=True, exist_ok=True)

    # ── Context Builder ────────────────────────────────────────────────────

    def build_context(self, task: TaskAssignment) -> str:
        """Build the full context markdown that gets passed to the AI agent."""
        blocks_md = "\n".join(
            f"{b['step']}. **{b['action']}** — actor={b['actor']}, target={b['target']}"
            + (f", repeat={b.get('repeat','')}" if "repeat" in b else "")
            for b in task.blocks
        )

        hard_md = "\n".join(f"- {r}" for r in task.hard_rules)

        return f"""# AI Test Runner — Task Assignment

## Task ID: {task.task_id}

## Test Type: {task.test_type}
## Spec: {task.spec}
## Label: {task.label}

## Probability of Success: {task.probability:.4f} ({task.probability*100:.2f}%)
## Expected Info Gain: {task.info_gain:.2f} bits
## Score (P × IG): {task.score:.4f}

---

## Steps to Execute

{blocks_md}

---

## Hard Rules — Do NOT Break

{hard_md}

---

## Outcome Logging

After completing the test, fill in:

```
Run ID: {task.task_id}
Outcome: PASS / FAIL / BLOCKED / UNKNOWN
NPC Result: (what Jugram/Balance said)
Notes: (anything unusual)
Target genders confirmed:
Target races:
Blood Bar values:
Manual grip confirmed: YES / NO
Zombie confirmed: YES / NO
Gender swap confirmed: YES / NO
Commands used: NONE
Volt/mode used: NONE
```

Save your result to:
`{self.results_dir / (task.task_id + ".json")}`
"""

    # ── Queue Management ─────────────────────────────────────────────────

    def enqueue(self, task: TaskAssignment):
        with self._queue_lock:
            self._queue.append(task)

    def enqueue_all(self, tests: list[dict]):
        """Enqueue a batch of tests from ranked_tests()."""
        hard_rules = [
            "Exactly one gender reroll for the clean route",
            "After the reroll, use same-gender targets only",
            "Targets can be any race and do not need to be unique",
            "Every zombification must be manual grip",
            "Use passive Blood Bar whenever possible",
            "No return/die/invade commands for clean tests",
            "Zombies do NOT act after conversion",
            "No Volt or mode for clean tests",
            "Do not use a second gender reroll unless deliberately resetting after a failed route",
        ]
        for t in tests:
            blocks = t["blocks"]
            task_id = f"task_{uuid.uuid4().hex[:8]}"

            # Build context
            spec     = t["spec"]
            test_type = t["type"]
            ctx = self.build_context(TaskAssignment(
                task_id    = task_id,
                agent_id   = "",
                test_type  = test_type,
                spec       = spec,
                label      = t["label"],
                blocks     = blocks,
                hard_rules = hard_rules,
                probability = t["p"],
                info_gain  = t["info_gain"],
                score      = t["score"],
                context_md = "",
            ))

            task = TaskAssignment(
                task_id     = task_id,
                agent_id    = "",
                test_type   = test_type,
                spec        = spec,
                label       = t["label"],
                blocks      = blocks,
                hard_rules  = hard_rules,
                probability = t["p"],
                info_gain   = t["info_gain"],
                score       = t["score"],
                context_md  = ctx,
            )

            # Save task file
            task_file = self.tasks_dir / f"{task_id}.json"
            task_file.write_text(json.dumps({
                "task_id":    task.task_id,
                "test_type":  task.test_type,
                "spec":       task.spec,
                "label":      task.label,
                "blocks":     task.blocks,
                "hard_rules": task.hard_rules,
                "probability": task.probability,
                "info_gain":  task.info_gain,
                "score":      task.score,
                "context":    task.context_md,
                "created_at": task.created_at,
                "status":     "pending",
            }, indent=2), encoding="utf-8")

            self.enqueue(task)

    def dequeue(self) -> TaskAssignment | None:
        with self._queue_lock:
            for i, t in enumerate(self._queue):
                if t.status == "pending":
                    t.status = "assigned"
                    return t
            return None

    def pending_count(self) -> int:
        with self._queue_lock:
            return sum(1 for t in self._queue if t.status in ("pending", "assigned"))

    def assigned_count(self) -> int:
        with self._queue_lock:
            return sum(1 for t in self._queue if t.status == "assigned")

    # ── Result Management ─────────────────────────────────────────────────

    def report_result(self, result: TestResult):
        with self._results_lock:
            self._results.append(result)

        # Save result file
        result_file = self.results_dir / f"{result.run_id}.json"
        result_file.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")

        # Update coverage
        key = f"{result.test_type}:{result.path or '/'.join(result.pair_sequence)}"
        self._coverage[key] = {
            "outcome":  result.outcome.name,
            "notes":    result.notes,
            "agent":    result.ai_agent,
            "duration": result.duration_min,
        }
        self._save_coverage()

    def get_results(self) -> list[TestResult]:
        with self._results_lock:
            return list(self._results)

    def get_coverage(self) -> dict[str, dict]:
        return dict(self._coverage)

    # ── Coverage Tracking ─────────────────────────────────────────────────

    def _save_coverage(self):
        cov_file = self.out_dir / "coverage_map.json"
        cov_file.write_text(json.dumps(self._coverage, indent=2), encoding="utf-8")

    def coverage_summary(self) -> dict:
        total = len(self._queue)
        done  = sum(1 for t in self._queue if t.status == "done")
        by_type: dict[str, dict] = {}
        for t in self._queue:
            if t.status == "done":
                by_type.setdefault(t.test_type, {"done": 0, "pass": 0, "fail": 0})
                by_type[t.test_type]["done"] += 1
                if t.result and t.result.outcome == Outcome.PASS:
                    by_type[t.test_type]["pass"] += 1
                elif t.result and t.result.outcome == Outcome.FAIL:
                    by_type[t.test_type]["fail"] += 1
        return {
            "total":   total,
            "done":    done,
            "pending": total - done,
            "by_type": by_type,
        }

    # ── Dispatch (sub-agent spawning) ─────────────────────────────────────

    def dispatch_next(self, spawn_fn: Callable[[TaskAssignment], None]) -> bool:
        """
        Dispatch the next pending task using the provided spawn function.
        spawn_fn(task: TaskAssignment) -> None
        Returns True if a task was dispatched, False if queue is empty.
        """
        task = self.dequeue()
        if task is None:
            return False

        task.status = "running"
        spawn_fn(task)
        return True

    def dispatch_all(self, spawn_fn: Callable[[TaskAssignment], None], max_dispatch: int | None = None):
        """Dispatch all pending tasks using spawn_fn."""
        count = 0
        while True:
            if max_dispatch and count >= max_dispatch:
                break
            if not self.dispatch_next(spawn_fn):
                break
            count += 1

    # ── Report Generation ─────────────────────────────────────────────────

    def generate_report(self) -> str:
        """Generate a markdown report of all results."""
        results = self.get_results()
        summary = self.coverage_summary()
        ranked  = self.eng.ranked_tests(20)

        lines = [
            "# Zombie Quest — Multi-AI Test Report",
            f"**Generated:** {datetime.now().isoformat()}",
            "",
            "## Coverage Summary",
            f"- Total tasks enqueued: {summary['total']}",
            f"- Tasks completed: {summary['done']}",
            f"- Tasks pending: {summary['pending']}",
            "",
            "### By Test Type",
        ]

        for ttype, counts in summary["by_type"].items():
            lines.append(f"- **{ttype}**: {counts['done']} done, {counts['pass']} pass, {counts['fail']} fail")

        lines += [
            "",
            "## Results",
        ]

        for r in results:
            status_icon = "[OK]" if r.outcome == Outcome.PASS else "[X]" if r.outcome == Outcome.FAIL else "[?]"
            lines.append(f"\n### {status_icon} {r.run_id} — {r.test_type} / {r.path or '/'.join(r.pair_sequence)}")
            lines.append(f"- Outcome: **{r.outcome.name}**")
            lines.append(f"- Agent: {r.ai_agent}")
            lines.append(f"- Duration: {r.duration_min:.1f} min")
            if r.notes:
                lines.append(f"- Notes: {r.notes}")

        lines += [
            "",
            "## Ranked Test Priority",
            "(P × information gain, highest first)",
        ]

        for i, t in enumerate(ranked, 1):
            tested = "[x]" if f"{t['type']}:{t['spec']}" in self._coverage else "[ ]"
            lines.append(f"{tested} #{i} **{t['label']}** — P={t['p']:.4f} IG={t['info_gain']:.2f}bits")

        report_path = self.reports_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_path.write_text("\n".join(lines), encoding="utf-8")

        return str(report_path)

    # ── Full Auto-Dispatch ────────────────────────────────────────────────

    def run_all_ranked(self, spawn_fn: Callable[[TaskAssignment], None], max_dispatch: int | None = None):
        """
        Enqueue all ranked tests and dispatch them.
        spawn_fn: function that takes a TaskAssignment and spawns an AI agent to execute it.
        """
        tests = self.eng.ranked_tests(20)
        self.enqueue_all(tests)
        print(f"[Dispatcher] Enqueued {len(tests)} tests")
        self.dispatch_all(spawn_fn, max_dispatch)


if __name__ == "__main__":
    out = Path(r"D:\Study\Project\zombie\03_TOOLS\zombie_test_runner")
    disp = MultiAgentDispatcher(out_dir=out, max_agents=4)

    # Enqueue all ranked tests
    disp.run_all_ranked(lambda t: print(f"[SPAWN] {t.task_id}: {t.label}"))
