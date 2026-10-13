from datetime import datetime, timezone

from pydantic import ValidationError

from log_analyzer.models import LogEntry

if __name__ == "__main__":
    try:
        LogEntry.model_validate({
            "timestamp": datetime.now(timezone.utc),
            "level": "TRACE",
            "component": "sensor",
            "latency_ms": "fast",
            "message": "sample",
            "unknown_field": 123,
        })
    except ValidationError as exc:
        print(exc)
        print("\nRead each location, error type, and rejected input:")
        for error in exc.errors():
            print(error["loc"], error["type"], error["msg"])
