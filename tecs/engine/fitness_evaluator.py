# tecs/engine/fitness_evaluator.py
from __future__ import annotations

import numpy as np


class FitnessEvaluator:
    def __init__(self, w_e: float = 0.4, w_b: float = 0.4, w_f: float = 0.2):
        self.w_e = w_e
        self.w_b = w_b
        self.w_f = w_f
        self._history: list[dict] = []  # for normalization

    # Metrics that are meaningful for emergence scoring
    MEANINGFUL_EMERGENCE_KEYS = {
        "betti_0", "betti_1", "euler_characteristic", "order_parameter_r",
        "magnetization", "lyapunov_exponent", "is_chaotic",
        "defect_score", "hallucination_score", "stress_magnitude",
        "compression_ratio", "info_retained", "free_energy",
        "mean_ricci_curvature", "branch_stability",
    }

    # Benchmark keys used for scoring
    BENCHMARK_KEYS = {"concept", "contradiction", "analogy"}

    def compute(self, emergence: dict, benchmark: dict, cost: float) -> float:
        """Compute absolute weighted fitness (no relative normalization)."""
        # Emergence score: average of meaningful metrics, capped at 1.0
        meaningful_emergence = {}
        for k, v in emergence.items():
            if isinstance(v, (int, float)) and k in self.MEANINGFUL_EMERGENCE_KEYS:
                meaningful_emergence[k] = min(1.0, max(0.0, abs(float(v))))

        emergence_score = float(np.mean(list(meaningful_emergence.values()))) if meaningful_emergence else 0.0

        # Benchmark score: direct average (already 0-1)
        b_vals = [float(v) for k, v in benchmark.items()
                  if isinstance(v, (int, float)) and k in self.BENCHMARK_KEYS]
        benchmark_score = float(np.mean(b_vals)) if b_vals else 0.0

        # Efficiency: inverse of normalized cost
        efficiency_score = max(0.0, 1.0 - min(1.0, float(cost)))

        fitness = self.w_e * emergence_score + self.w_b * benchmark_score + self.w_f * efficiency_score
        return float(np.clip(fitness, 0.0, 1.0))

    def update_history(self, metrics: dict) -> None:
        self._history.append(metrics)

    def normalize_metric(self, value: float, key: str, window: int = 10) -> float:
        recent = [h.get(key, 0.0) for h in self._history[-window:]]
        if not recent or max(recent) == min(recent):
            return 0.5
        return (value - min(recent)) / (max(recent) - min(recent))
