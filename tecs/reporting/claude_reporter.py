from __future__ import annotations
import json
import subprocess


class ClaudeReporter:
    def __init__(self, enabled: bool = True):
        self._enabled = enabled

    def generate_report(self, data: dict, prompt_prefix: str = "이 결과를 분석해서 한국어 리포트를 작성해:") -> str:
        if not self._enabled:
            return ""
        try:
            data_str = json.dumps(data, indent=2, default=str, ensure_ascii=False)
            prompt = f"{prompt_prefix}\n\n{data_str}"
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return ""
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return ""
