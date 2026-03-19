from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime


class ResultLogger:
    def __init__(self, run_dir: str):
        self._dir = Path(run_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _append_jsonl(self, filename: str, data: dict) -> None:
        data["timestamp"] = datetime.now().isoformat()
        with open(self._dir / filename, "a") as f:
            f.write(json.dumps(data, default=str) + "\n")

    def log_generation(self, data: dict) -> None:
        self._append_jsonl("evolution.jsonl", data)

    def log_emergence_event(self, data: dict) -> None:
        self._append_jsonl("emergence_events.jsonl", data)

    def log_benchmark(self, data: dict) -> None:
        self._append_jsonl("benchmarks.jsonl", data)

    def log_phase(self, data: dict) -> None:
        self._append_jsonl("phase_log.jsonl", data)

    def save_checkpoint(self, data: dict) -> None:
        with open(self._dir / "checkpoint.json", "w") as f:
            json.dump(data, f, indent=2, default=str)

    def save_causal_graph(self, data: dict) -> None:
        with open(self._dir / "causal_graph.json", "w") as f:
            json.dump(data, f, indent=2, default=str)

    @property
    def run_dir(self) -> Path:
        return self._dir
