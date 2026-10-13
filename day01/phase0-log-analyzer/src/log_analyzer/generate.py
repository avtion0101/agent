import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


def generate_log(path: Path, lines: int = 10000, seed: int = 42, invalid_every: int = 97) -> None:
    if lines < 0 or invalid_every < 0:
        raise ValueError("lines and invalid_every must be non-negative")
    rng = random.Random(seed)
    start = datetime(2026, 10, 13, tzinfo=timezone.utc)
    levels = ("DEBUG", "INFO", "WARNING", "ERROR")
    components = ("serial", "modbus", "sensor", "agent-tool")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for index in range(lines):
            if invalid_every and (index + 1) % invalid_every == 0:
                handle.write("BROKEN LINE: simulated protocol corruption\n")
                continue
            timestamp = (start + timedelta(milliseconds=index * 10)).isoformat()
            level = rng.choices(levels, weights=(10, 75, 10, 5), k=1)[0]
            latency = round(rng.uniform(0.1, 100.0), 3)
            handle.write(
                f"{timestamp} | {level} | {rng.choice(components)} | {latency} | sample {index}\n"
            )
