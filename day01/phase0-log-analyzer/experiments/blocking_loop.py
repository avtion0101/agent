"""Observe loop stalls. Timings are observations, not deterministic assertions."""
import argparse
import asyncio
import time
from typing import Literal

Mode = Literal["blocking", "async-sleep", "thread"]


async def scenario(mode: Mode, seconds: float) -> None:
    gaps: list[float] = []
    started = time.perf_counter()

    async def heartbeat() -> None:
        previous = time.perf_counter()
        while time.perf_counter() - started < seconds + 0.2:
            await asyncio.sleep(0.05)
            now = time.perf_counter()
            gaps.append(now - previous)
            previous = now

    async def work() -> None:
        if mode == "blocking":
            time.sleep(seconds)  # Intentional failure: blocks the event-loop thread.
        elif mode == "async-sleep":
            await asyncio.sleep(seconds)
        else:
            await asyncio.to_thread(time.sleep, seconds)

    await asyncio.gather(heartbeat(), work())
    print(f"{mode:12s} heartbeat_count={len(gaps):3d} max_gap={max(gaps):.3f}s")


async def main(seconds: float) -> None:
    for mode in ("blocking", "async-sleep", "thread"):
        await scenario(mode, seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=0.5)
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    asyncio.run(main(args.seconds))
