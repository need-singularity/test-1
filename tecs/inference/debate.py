"""Adversarial hypothesis verification — Agent A (creator) vs Agent B (critic)."""
from __future__ import annotations
import subprocess
import json


class DebateProtocol:
    """Run adversarial debate between creator and critic agents via claude CLI."""

    def __init__(self, max_rounds: int = 3, enabled: bool = True):
        self._max_rounds = max_rounds
        self._enabled = enabled

    def debate(self, hypothesis: dict) -> dict:
        """Run debate on a hypothesis. Returns verdict."""
        if not self._enabled:
            return {"verdict": "SKIP", "reason": "debate disabled"}

        history = []
        current = hypothesis

        for round_num in range(1, self._max_rounds + 1):
            # Agent B (Critic) attacks
            critique = self._critic_attack(current, history)
            if not critique:
                return {"verdict": "PASS", "round": round_num, "reason": "critic found no issues", "history": history}

            history.append({"round": round_num, "critique": critique})

            # Check if critique is fatal
            if "FATAL" in critique.upper() or "REJECT" in critique.upper():
                return {"verdict": "REJECT", "round": round_num, "reason": critique, "history": history}

            # Agent A (Creator) defends/revises
            revision = self._creator_defend(current, critique, history)
            if not revision:
                return {"verdict": "REJECT", "round": round_num, "reason": f"creator could not defend: {critique}", "history": history}

            history.append({"round": round_num, "revision": revision})
            current = {**current, "revision": revision}

        return {"verdict": "PASS_WITH_REVISIONS", "rounds": self._max_rounds, "history": history}

    def _critic_attack(self, hypothesis: dict, history: list) -> str:
        """Agent B: ruthlessly critique the hypothesis."""
        try:
            data = json.dumps(hypothesis, default=str, ensure_ascii=False)
            prompt = (
                "너는 무자비한 과학 리뷰어야. 아래 가설을 공격해. "
                "1) 차원 분석이 맞는지 2) 반증 가능한지 3) 동어반복이 아닌지 4) 수학적 비약이 없는지. "
                "문제가 있으면 구체적으로 지적하고, 문제 없으면 'NO ISSUES'라고만 써. "
                "마크다운 없이 평문으로 2-3문장.\n\n" + data
            )
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True, text=True, timeout=60,
            )
            output = result.stdout.strip() if result.returncode == 0 else ""
            output = "".join(c for c in output if c.isprintable() or c in "\n ")
            if "NO ISSUES" in output.upper():
                return ""
            return output
        except Exception:
            return ""

    def _creator_defend(self, hypothesis: dict, critique: str, history: list) -> str:
        """Agent A: defend or revise the hypothesis."""
        try:
            data = json.dumps(hypothesis, default=str, ensure_ascii=False)
            prompt = (
                "너는 가설의 창시자야. 리뷰어가 아래 비판을 했어. "
                "수식을 수정하거나 반박해. 수정한다면 구체적 수식을 포함해. "
                "마크다운 없이 평문으로 2-3문장.\n\n"
                f"가설: {data}\n\n비판: {critique}"
            )
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True, text=True, timeout=60,
            )
            output = result.stdout.strip() if result.returncode == 0 else ""
            output = "".join(c for c in output if c.isprintable() or c in "\n ")
            return output
        except Exception:
            return ""
