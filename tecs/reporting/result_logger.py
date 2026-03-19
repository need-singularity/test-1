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

    def generate_markdown_report(self, data: dict) -> str:
        """Generate REPORT.md from data using Jinja2 template."""
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        import os
        template_dir = os.path.join(os.path.dirname(__file__))
        env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape([]))
        template = env.get_template("report_template.md.j2")
        return template.render(**data)

    def save_report(self, data: dict) -> None:
        """Generate and save REPORT.md."""
        content = self.generate_markdown_report(data)
        (self._dir / "REPORT.md").write_text(content)

    @property
    def run_dir(self) -> Path:
        return self._dir
