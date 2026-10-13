import argparse
import asyncio
import sys
from pathlib import Path

from log_analyzer.analyzer import analyze_file
from log_analyzer.generate import generate_log


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and analyze device logs")
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("path", type=Path)
    generate.add_argument("--lines", type=int, default=10000)
    generate.add_argument("--seed", type=int, default=42)
    generate.add_argument("--invalid-every", type=int, default=97)
    analyze = sub.add_parser("analyze")
    analyze.add_argument("path", type=Path)
    analyze.add_argument("--workers", type=int, default=2)
    analyze.add_argument("--batch-size", type=int, default=1000)
    analyze.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "generate":
            generate_log(args.path, args.lines, args.seed, args.invalid_every)
            print(f"generated {args.lines} lines: {args.path}")
            return
        report = asyncio.run(analyze_file(args.path, args.workers, args.batch_size))
        text = report.model_dump_json(indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text + "\n", encoding="utf-8")
        print(text)
    except (OSError, ValueError, ExceptionGroup) as exc:
        print(f"analysis failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
