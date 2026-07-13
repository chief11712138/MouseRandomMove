from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from threading import Lock


class EventLogger:
    FIELDNAMES = ("timestamp", "event", "details")

    def __init__(self) -> None:
        local_app_data = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
        self.log_dir = local_app_data / "MouseRandomMove" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        suffix = datetime.now().strftime("%Y%m%d")
        self.path = self.log_dir / f"events-{suffix}.csv"
        self._lock = Lock()

    def write(self, event: str, details: dict[str, object]) -> None:
        row = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "event": event,
            "details": json.dumps(details, ensure_ascii=False, sort_keys=True),
        }
        with self._lock:
            is_new = not self.path.exists()
            with self.path.open("a", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=self.FIELDNAMES)
                if is_new:
                    writer.writeheader()
                writer.writerow(row)

