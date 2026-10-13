import asyncio
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from log_analyzer.analyzer import analyze_file
from log_analyzer.generate import generate_log
from log_analyzer.parser import parse_line

VALID = "2026-10-13T10:00:00+00:00 | INFO | serial | 2.5 | device ready"


def test_parser_accepts_valid_record() -> None:
    entry = parse_line(VALID)
    assert entry.level == "INFO"
    assert entry.latency_ms == 2.5
    assert entry.timestamp.utcoffset() is not None


def test_parser_keeps_delimiter_in_message() -> None:
    assert parse_line(VALID + " | extra field").message == "device ready | extra field"


@pytest.mark.parametrize(
    "line",
    [
        "broken",
        VALID.replace("2026-10-13T10:00:00+00:00", "bad timestamp"),
        VALID.replace("INFO", "TRACE"),
        VALID.replace("serial", ""),
        VALID.replace("2.5", "-1"),
        VALID.replace("2.5", "nan"),
        VALID.replace("2.5", "inf"),
        VALID.replace("2.5", "many"),
        VALID.replace("device ready", ""),
    ],
)
def test_parser_rejects_invalid_record(line: str) -> None:
    with pytest.raises((ValueError, ValidationError)):
        parse_line(line)


def test_empty_file_has_no_mean(tmp_path: Path) -> None:
    path = tmp_path / "empty.log"
    path.write_text("", encoding="utf-8")
    report = asyncio.run(analyze_file(path))
    assert report.total_lines == 0
    assert report.mean_latency_ms is None
    assert report.max_latency_ms is None


def test_known_statistics_and_bad_line_numbers(tmp_path: Path) -> None:
    path = tmp_path / "sample.log"
    path.write_text(
        VALID + "\nBAD\n" + VALID.replace("INFO", "ERROR").replace("2.5", "7.5") + "\n",
        encoding="utf-8",
    )
    report = asyncio.run(analyze_file(path, workers=3, batch_size=1))
    assert (report.total_lines, report.valid_lines, report.invalid_lines) == (3, 2, 1)
    assert report.level_counts == {"ERROR": 1, "INFO": 1}
    assert report.component_counts == {"serial": 2}
    assert report.mean_latency_ms == 5.0
    assert report.max_latency_ms == 7.5
    assert report.invalid_examples[0].line_number == 2


def test_worker_counts_do_not_change_statistics(tmp_path: Path) -> None:
    path = tmp_path / "many.log"
    generate_log(path, lines=2000)
    reports = [asyncio.run(analyze_file(path, workers=n, batch_size=7)) for n in (1, 4)]
    assert reports[0].level_counts == reports[1].level_counts
    assert reports[0].component_counts == reports[1].component_counts
    assert reports[0].valid_lines == reports[1].valid_lines
    assert reports[0].mean_latency_ms == pytest.approx(reports[1].mean_latency_ms)
    assert reports[0].invalid_examples == reports[1].invalid_examples


def test_invalid_examples_are_bounded_and_ordered(tmp_path: Path) -> None:
    path = tmp_path / "bad.log"
    path.write_text("BAD\n" * 101, encoding="utf-8")
    report = asyncio.run(analyze_file(path, workers=4, batch_size=3))
    assert report.invalid_lines == 101
    assert [issue.line_number for issue in report.invalid_examples] == [1, 2, 3, 4, 5]


def test_missing_file_fails(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        asyncio.run(analyze_file(tmp_path / "missing.log"))


@pytest.mark.parametrize("workers,batch", [(0, 10), (-1, 10), (1, 0)])
def test_bad_configuration_rejected(tmp_path: Path, workers: int, batch: int) -> None:
    with pytest.raises(ValueError, match="positive"):
        asyncio.run(analyze_file(tmp_path / "irrelevant.log", workers, batch))


def test_blank_line_is_invalid(tmp_path: Path) -> None:
    path = tmp_path / "blank.log"
    path.write_text(VALID + "\n\n", encoding="utf-8")
    report = asyncio.run(analyze_file(path))
    assert (report.valid_lines, report.invalid_lines) == (1, 1)


def test_consumer_failure_does_not_deadlock_producer(tmp_path: Path) -> None:
    path = tmp_path / "many.log"
    generate_log(path, lines=100)

    async def run() -> None:
        await asyncio.wait_for(analyze_file(path, workers=1, batch_size=1), timeout=5)

    with patch("log_analyzer.analyzer.parse_batch", side_effect=RuntimeError("worker failed")):
        with pytest.raises(ExceptionGroup, match="TaskGroup"):
            asyncio.run(run())


def test_generator_is_reproducible(tmp_path: Path) -> None:
    first, second = tmp_path / "a.log", tmp_path / "b.log"
    generate_log(first, lines=100, seed=123)
    generate_log(second, lines=100, seed=123)
    assert first.read_bytes() == second.read_bytes()


def test_cli_report_and_failure_exit(tmp_path: Path) -> None:
    source, output = tmp_path / "input.log", tmp_path / "report.json"
    generate_log(source, lines=194)
    completed = subprocess.run(
        [sys.executable, "-m", "log_analyzer.cli", "analyze", str(source), "--output", str(output)],
        capture_output=True, text=True, check=True,
    )
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["invalid_lines"] == 2
    assert json.loads(completed.stdout) == document
    failed = subprocess.run(
        [sys.executable, "-m", "log_analyzer.cli", "analyze", str(tmp_path / "missing.log")],
        capture_output=True, text=True, check=False,
    )
    assert failed.returncode == 1
    assert "analysis failed" in failed.stderr
