from datetime import datetime

from pydantic import ValidationError

from log_analyzer.models import LogEntry, ParseIssue


def parse_line(line: str) -> LogEntry:
    # Keep delimiters in the message: only split the first four pipes.
    fields = [field.strip() for field in line.rstrip("\n").split("|", 4)]
    if len(fields) != 5:
        raise ValueError("expected timestamp | level | component | latency_ms | message")
    timestamp, level, component, latency, message = fields
    return LogEntry.model_validate(
        {
            "timestamp": datetime.fromisoformat(timestamp),
            "level": level,
            "component": component,
            "latency_ms": float(latency),
            "message": message,
        }
    )


def parse_batch(
    lines: list[tuple[int, str]],
) -> tuple[list[LogEntry], int, list[ParseIssue]]:
    entries: list[LogEntry] = []
    issues: list[ParseIssue] = []
    invalid_count = 0
    for number, line in lines:
        try:
            entries.append(parse_line(line))
        except (ValueError, ValidationError) as exc:
            invalid_count += 1
            if len(issues) < 5:
                issues.append(ParseIssue(line_number=number, reason=str(exc)[:300]))
    return entries, invalid_count, issues
