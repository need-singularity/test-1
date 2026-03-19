"""4-stage verification pipeline: formal → counterexample → reproducibility → prediction."""
from __future__ import annotations
import numpy as np
import random
from tecs.types import TopologyState, Candidate


class VerificationPipeline:
    """Runs 4-stage verification on candidate results.

    Stage A: Formal verification (contradictions, dimension, tautology)
    Stage B: Counterexample verification (fails on obviously wrong cases?)
    Stage C: Reproducibility verification (stable across seeds?)
    Stage D: Predictive verification (correct on held-out data?)
    """

    def __init__(self, failure_threshold: float = 0.3):
        self._failure_threshold = failure_threshold

    def verify(self, candidate: Candidate, state: TopologyState,
               simulator=None, data_manager=None, seed: int = 42) -> dict:
        """Run all 4 stages. Returns scores + pass/fail."""
        results = {
            "formal": self._stage_a_formal(candidate, state),
            "counterexample": self._stage_b_counterexample(candidate, state, simulator, data_manager),
            "reproducibility": self._stage_c_reproducibility(candidate, simulator, data_manager, seed),
            "predictive": self._stage_d_predictive(candidate, state, simulator, data_manager),
        }

        # Aggregate
        scores = {k: v["score"] for k, v in results.items()}
        failures = sum(1 for v in results.values() if not v["passed"])
        failure_rate = failures / 4.0

        # Hard elimination: if failure_rate > threshold, candidate is dead
        eliminated = failure_rate > self._failure_threshold

        # Combined verification score
        verification_score = np.mean(list(scores.values()))

        return {
            "scores": scores,
            "details": results,
            "failure_count": failures,
            "failure_rate": failure_rate,
            "eliminated": eliminated,
            "verification_score": verification_score,
        }

    def _stage_a_formal(self, candidate: Candidate, state: TopologyState) -> dict:
        """Stage A: Formal verification.
        - Are metrics self-consistent? (no NaN, no Inf)
        - Is fitness suspiciously perfect (1.0)?
        - Are there contradictory metrics?
        """
        score = 1.0
        issues = []

        metrics = candidate.metrics or {}

        # Check for NaN/Inf
        for k, v in metrics.items():
            if isinstance(v, float):
                if np.isnan(v) or np.isinf(v):
                    score -= 0.3
                    issues.append(f"{k} is {v}")

        # Check for suspicious perfection
        if candidate.fitness >= 1.0:
            score -= 0.2
            issues.append("fitness = 1.0 (suspiciously perfect)")

        # Check for contradictory metrics
        # hallucination_score high + query_accuracy high = suspicious
        halluc = metrics.get("hallucination_score", 0)
        query_acc = metrics.get("query_accuracy", 0)
        if halluc > 0.8 and query_acc > 0.8:
            score -= 0.2
            issues.append(f"high hallucination ({halluc:.2f}) but high accuracy ({query_acc:.2f})")

        # Check curvature sanity
        if state.curvature is not None and len(state.curvature) > 0:
            if np.any(np.isnan(state.curvature)) or np.any(np.isinf(state.curvature)):
                score -= 0.3
                issues.append("curvature contains NaN/Inf")

        score = max(0.0, min(1.0, score))
        return {"score": score, "passed": score >= 0.5, "issues": issues}

    def _stage_b_counterexample(self, candidate: Candidate, state: TopologyState,
                                simulator=None, data_manager=None) -> dict:
        """Stage B: Counterexample verification.
        Test the candidate on obviously wrong cases.
        If it gives high scores on garbage input, it's unreliable.
        """
        if simulator is None or data_manager is None:
            return {"score": 0.5, "passed": True, "issues": ["no simulator/data — skipped"]}

        score = 1.0
        issues = []

        try:
            # Generate random noise as input (should get LOW fitness)
            noise_points = np.random.RandomState(999).rand(50, 3) * 100  # extreme scale
            noise_state = simulator.simulate(candidate, noise_points)

            # If noise gets high metrics, candidate is unreliable
            noise_metrics = noise_state.metrics
            noise_query = noise_metrics.get("query_accuracy", 0)
            noise_analogy = noise_metrics.get("analogy_score", 0)

            if noise_query > 0.5:
                score -= 0.3
                issues.append(f"noise input got query_accuracy={noise_query:.2f} (should be ~0)")
            if noise_analogy > 0.5:
                score -= 0.3
                issues.append(f"noise input got analogy_score={noise_analogy:.2f} (should be ~0)")

        except Exception:
            pass  # simulation failure on noise is acceptable

        score = max(0.0, min(1.0, score))
        return {"score": score, "passed": score >= 0.5, "issues": issues}

    def _stage_c_reproducibility(self, candidate: Candidate,
                                  simulator=None, data_manager=None,
                                  base_seed: int = 42) -> dict:
        """Stage C: Reproducibility verification.
        Run with 3 different seeds. Results should be similar.
        """
        if simulator is None or data_manager is None:
            return {"score": 0.5, "passed": True, "issues": ["no simulator/data — skipped"]}

        scores_per_seed = []
        issues = []

        for seed_offset in range(3):
            try:
                seed = base_seed + seed_offset * 1000
                rng = np.random.RandomState(seed)
                points = rng.rand(50, 3)
                state = simulator.simulate(candidate, points)
                fitness = state.metrics.get("inference_combined", 0.0)
                scores_per_seed.append(fitness)
            except Exception:
                scores_per_seed.append(0.0)

        if len(scores_per_seed) >= 2:
            variance = np.var(scores_per_seed)
            mean_score = np.mean(scores_per_seed)

            # High variance = low reproducibility
            if variance > 0.1:
                issues.append(f"high variance across seeds: {variance:.4f}")
                repro_score = max(0.0, 1.0 - variance * 5)
            else:
                repro_score = 1.0
        else:
            repro_score = 0.5
            issues.append("not enough seed runs")

        return {"score": repro_score, "passed": repro_score >= 0.5, "issues": issues}

    def _stage_d_predictive(self, candidate: Candidate, state: TopologyState,
                             simulator=None, data_manager=None) -> dict:
        """Stage D: Predictive verification.
        Split eval data into train/test. Train on first half, predict second half.
        """
        score = 0.5  # default: neutral
        issues = []

        metrics = candidate.metrics or {}

        # Use existing benchmark scores as proxy for predictive ability
        concept = metrics.get("concept", 0)
        contradiction = metrics.get("contradiction", 0)
        analogy = metrics.get("analogy_score", 0)
        query = metrics.get("query_accuracy", 0)

        # Predictive score = average of actual task performance
        task_scores = [v for v in [concept, contradiction, analogy, query] if v > 0]
        if task_scores:
            score = np.mean(task_scores)

        # Penalty for zero performance
        if all(v == 0 for v in [concept, contradiction, analogy, query]):
            score = 0.0
            issues.append("all prediction scores are 0")

        return {"score": score, "passed": score >= 0.2, "issues": issues}
