# tecs/engine/fitness_evaluator.py
from __future__ import annotations

import numpy as np


class FitnessEvaluator:
    def __init__(self, w_e: float = 0.4, w_b: float = 0.4, w_f: float = 0.2):
        self.w_e = w_e
        self.w_b = w_b
        self.w_f = w_f
        self._history: list[dict] = []  # for normalization

    def compute(self, emergence: dict, benchmark: dict, cost: float) -> float:
        """Compute weighted fitness. All inputs should have values in [0, 1] range."""
        e_vals = [v for v in emergence.values() if isinstance(v, (int, float))]
        emergence_score = np.mean(e_vals) if e_vals else 0.0

        b_vals = [v for v in benchmark.values() if isinstance(v, (int, float))]
        benchmark_score = np.mean(b_vals) if b_vals else 0.0

        efficiency_score = 1.0 - min(1.0, max(0.0, cost))

        fitness = self.w_e * emergence_score + self.w_b * benchmark_score + self.w_f * efficiency_score
        return float(np.clip(fitness, 0.0, 1.0))

    def update_history(self, metrics: dict) -> None:
        self._history.append(metrics)

    def normalize_metric(self, value: float, key: str, window: int = 10) -> float:
        recent = [h.get(key, 0.0) for h in self._history[-window:]]
        if not recent or max(recent) == min(recent):
            return 0.5
        return (value - min(recent)) / (max(recent) - min(recent))
