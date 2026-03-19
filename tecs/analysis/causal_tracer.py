"""CausalTracer: observational causal analysis of evolutionary history."""
from __future__ import annotations

import numpy as np


class CausalTracer:
    """Analyzes evolutionary history to identify which component changes
    correlate with metric improvements or degradations."""

    LAYERS = ["representation", "reasoning", "emergence", "verification", "optimization"]

    def __init__(self, min_generations: int = 20, p_value_threshold: float = 0.05) -> None:
        self._min_gen = min_generations
        self._p_threshold = p_value_threshold

    def analyze(self, history: list[dict]) -> dict:
        """Analyze evolutionary history.

        Each entry should have:
            {"generation": int, "components": dict, "metrics": dict, "mutation_layer": str|None}

        Returns:
            {
                "confidence": "sufficient" | "insufficient_data",
                "weakest_layer": str | None,
                "causal_matrix": np.ndarray (5 layers x N metrics),
                "layer_scores": dict[str, float],
            }
        """
        if len(history) < self._min_gen:
            return {
                "confidence": "insufficient_data",
                "weakest_layer": None,
                "causal_matrix": np.zeros((5, 5)),
                "layer_scores": {},
            }

        layers = self.LAYERS
        metric_keys = self._get_metric_keys(history)
        n_metrics = len(metric_keys) if metric_keys else 1
        matrix = np.zeros((len(layers), n_metrics))

        # Count observations per layer
        counts = np.zeros(len(layers))

        for i in range(1, len(history)):
            prev, curr = history[i - 1], history[i]
            mut_layer = curr.get("mutation_layer")
            if mut_layer and mut_layer in layers:
                layer_idx = layers.index(mut_layer)
                counts[layer_idx] += 1
                for j, mk in enumerate(metric_keys):
                    delta = curr["metrics"].get(mk, 0.0) - prev["metrics"].get(mk, 0.0)
                    matrix[layer_idx][j] += delta

        # Average by observation count
        for i in range(len(layers)):
            if counts[i] > 0:
                matrix[i] /= counts[i]

        # Identify weakest layer: the one whose mutations cause the least improvement
        layer_scores: dict[str, float] = {}
        for i, layer in enumerate(layers):
            layer_scores[layer] = float(np.mean(matrix[i])) if counts[i] > 0 else 0.0

        weakest = (
            min(layer_scores, key=layer_scores.get)
            if any(counts > 0)
            else None
        )

        return {
            "confidence": "sufficient",
            "weakest_layer": weakest,
            "causal_matrix": matrix,
            "layer_scores": layer_scores,
        }

    def _get_metric_keys(self, history: list[dict]) -> list[str]:
        """Collect all metric keys present across the history."""
        keys: list[str] = []
        seen: set[str] = set()
        for entry in history:
            for k in entry.get("metrics", {}).keys():
                if k not in seen:
                    seen.add(k)
                    keys.append(k)
        return keys
