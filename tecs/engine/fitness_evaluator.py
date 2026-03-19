# tecs/engine/fitness_evaluator.py
from __future__ import annotations

import numpy as np


class FitnessEvaluator:
    # ── Occam's Razor constants ──
    EDGE_THRESHOLD = 150    # hyperedges below this are free (allows creative emergence)
    LAMBDA_BLOAT = 0.05     # structural bloat penalty weight
    LAMBDA_HALLUC = 0.4     # hallucination penalty weight (harsh — intentional)
    MIN_FITNESS = 0.001     # floor to keep selection probability nonzero

    def __init__(self, w_e: float = 0.4, w_b: float = 0.4, w_f: float = 0.2):
        self.w_e = w_e
        self.w_b = w_b
        self.w_f = w_f
        self._history: list[dict] = []  # for normalization

    # Metrics that are meaningful for emergence scoring
    # NOTE: hallucination_score REMOVED — it is now a penalty, not a positive signal
    MEANINGFUL_EMERGENCE_KEYS = {
        "betti_0", "betti_1", "euler_characteristic", "order_parameter_r",
        "magnetization", "lyapunov_exponent", "is_chaotic",
        "defect_score", "stress_magnitude",
        "compression_ratio", "info_retained", "free_energy",
        "mean_ricci_curvature", "branch_stability",
    }

    # Benchmark keys used for scoring
    BENCHMARK_KEYS = {
        "concept", "contradiction", "analogy",
        "query_accuracy", "multihop_accuracy", "analogy_score",
        "inference_combined",
    }

    def _occam_penalty(self, emergence: dict) -> float:
        """Occam's Razor: penalize structural bloat + hallucination.

        Returns total penalty >= 0.
        """
        # 1. Hyperedge bloat: soft penalty kicks in above EDGE_THRESHOLD
        n_edges = emergence.get("n_hyperedges", 0)
        if n_edges > self.EDGE_THRESHOLD:
            bloat = (n_edges - self.EDGE_THRESHOLD) / self.EDGE_THRESHOLD
        else:
            bloat = 0.0
        penalty_bloat = self.LAMBDA_BLOAT * bloat

        # 2. Hallucination: direct hard penalty
        halluc = float(emergence.get("hallucination_score", 0.0))
        penalty_halluc = self.LAMBDA_HALLUC * halluc

        return penalty_bloat + penalty_halluc

    def compute(self, emergence: dict, benchmark: dict, cost: float) -> float:
        """Compute absolute weighted fitness with Occam penalty."""
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

        base = self.w_e * emergence_score + self.w_b * benchmark_score + self.w_f * efficiency_score
        fitness = base - self._occam_penalty(emergence)
        return float(max(self.MIN_FITNESS, np.clip(fitness, 0.0, 1.0)))

    def compute_verified(self, emergence: dict, benchmark: dict, cost: float,
                         verification: dict) -> float:
        """Compute fitness WITH verification + Occam penalty.

        F = α·novelty + β·coherence + γ·predictive - δ·failures - occam_penalty
        """
        # If eliminated by verification, fitness = 0
        if verification.get("eliminated", False):
            return 0.0

        # Base scores
        e_vals = [v for k, v in emergence.items()
                  if isinstance(v, (int, float)) and k in self.MEANINGFUL_EMERGENCE_KEYS]
        emergence_score = np.mean([min(1.0, max(0.0, abs(v))) for v in e_vals]) if e_vals else 0.0

        b_vals = [v for k, v in benchmark.items()
                  if isinstance(v, (int, float)) and k in self.BENCHMARK_KEYS]
        benchmark_score = np.mean(b_vals) if b_vals else 0.0

        efficiency_score = max(0.0, 1.0 - min(1.0, cost))

        # Verification scores
        v_scores = verification.get("scores", {})
        verification_score = verification.get("verification_score", 0.5)
        failure_penalty = verification.get("failure_count", 0) * 0.15

        predictive = v_scores.get("predictive", 0.5)

        base = (
            0.2 * emergence_score +      # novelty
            0.2 * benchmark_score +       # coherence (task ability)
            0.1 * efficiency_score +      # efficiency
            0.3 * predictive +            # predictive success (HIGHEST WEIGHT)
            0.2 * verification_score -    # overall verification
            failure_penalty               # penalty for failures
        )

        fitness = base - self._occam_penalty(emergence)
        return float(max(self.MIN_FITNESS, np.clip(fitness, 0.0, 1.0)))

    def update_history(self, metrics: dict) -> None:
        self._history.append(metrics)

    def normalize_metric(self, value: float, key: str, window: int = 10) -> float:
        recent = [h.get(key, 0.0) for h in self._history[-window:]]
        if not recent or max(recent) == min(recent):
            return 0.5
        return (value - min(recent)) / (max(recent) - min(recent))
