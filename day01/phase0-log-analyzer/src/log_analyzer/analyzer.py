import asyncio
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

from log_analyzer.models import AnalysisReport, LogEntry, ParseIssue
from log_analyzer.parser import parse_batch

Batch = list[tuple[int, str]]


def read_batch(handle: TextIO, first_line: int, batch_size: int) -> Batch:
    lines: Batch = []
    for offset in range(batch_size):
        line = handle.readline()
        if not line:
            break
        lines.append((first_line + offset, line))
    return lines


@dataclass
class Statistics:
    valid: int = 0
    invalid: int = 0
    levels: Counter[str] = field(default_factory=Counter)
    components: Counter[str] = field(default_factory=Counter)
    latency_sum: float = 0.0
    latency_max: float | None = None
    issues: list[ParseIssue] = field(default_factory=list)

    def add(self, entries: list[LogEntry], invalid: int, issues: list[ParseIssue]) -> None:
        self.valid += len(entries)
        self.invalid += invalid
        for entry in entries:
            self.levels[entry.level] += 1
            self.components[entry.component] += 1
            self.latency_sum += entry.latency_ms
            self.latency_max = max(self.latency_max or 0.0, entry.latency_ms)
        # Keep the first five bad lines in file order, independent of worker order.
        self.issues = sorted(self.issues + issues, key=lambda item: item.line_number)[:5]

    def report(self, elapsed: float) -> AnalysisReport:
        return AnalysisReport(
            total_lines=self.valid + self.invalid,
            valid_lines=self.valid,
            invalid_lines=self.invalid,
            level_counts=dict(sorted(self.levels.items())),
            component_counts=dict(sorted(self.components.items())),
            mean_latency_ms=self.latency_sum / self.valid if self.valid else None,
            max_latency_ms=self.latency_max,
            invalid_examples=self.issues,
            elapsed_seconds=elapsed,
        )


async def analyze_file(path: Path, workers: int = 2, batch_size: int = 1000) -> AnalysisReport:
    if workers < 1 or batch_size < 1:
        raise ValueError("workers and batch_size must be positive")
    started = time.perf_counter()
    queue: asyncio.Queue[Batch | None] = asyncio.Queue(maxsize=workers * 2)
    statistics = Statistics()
    handle = await asyncio.to_thread(path.open, "r", encoding="utf-8")

    async def produce() -> None:
        number = 1
        while True:
            batch = await asyncio.to_thread(read_batch, handle, number, batch_size)
            if not batch:
                break
            number += len(batch)
            await queue.put(batch)
        for _ in range(workers):
            await queue.put(None)

    async def consume() -> None:
        while True:
            batch = await queue.get()
            if batch is None:
                return
            entries, invalid, issues = await asyncio.to_thread(parse_batch, batch)
            # No await during aggregation: only the event-loop thread mutates statistics.
            statistics.add(entries, invalid, issues)

    try:
        async with asyncio.TaskGroup() as group:
            group.create_task(produce())
            for _ in range(workers):
                group.create_task(consume())
    finally:
        # to_thread cancellation does not kill an already-running OS thread.
        # This local-file implementation targets normal completion; remote/blocking
        # streams need a cancellable reader and explicit shutdown coordination.
        await asyncio.to_thread(handle.close)
    return statistics.report(time.perf_counter() - started)
