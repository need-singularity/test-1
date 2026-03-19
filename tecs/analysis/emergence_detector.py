"""EmergenceDetector: tracks emergence metrics and detects spikes."""
from __future__ import annotations

import numpy as np

from tecs.config import EmergenceConfig


class EmergenceDetector:
    """Tracks emergence metrics every generation and detects spikes."""

    def __init__(self, config: EmergenceConfig) -> None:
        self._cfg = config
        self._history: list[dict[str, float]] = []
        self._window_size = config.window_size

    def check(self, generation: int, metrics: dict[str, float]) -> dict | None:
        """Record metrics and check for spikes.

        Returns an event dict if a spike is detected, None otherwise.
        """
        self._history.append({"generation": generation, **metrics})

        # Don't check until min_generations reached
        if generation < self._cfg.min_generations:
            return None

        # Check each metric for spikes
        for key, value in metrics.items():
            spike = self._check_spike(key, value, generation)
            if spike:
                return spike
        return None

    def _check_spike(self, key: str, value: float, generation: int) -> dict | None:
        # Get recent window
        window = self._history[-self._window_size:] if len(self._history) > 1 else self._history
        recent_values = [h.get(key, 0.0) for h in window[:-1]]  # exclude current

        if not recent_values:
            return None

        if key == "lyapunov_exponent":
            # Spike = sign change from negative to positive
            if len(recent_values) >= 1 and recent_values[-1] < 0 and value > 0:
                return {
                    "generation": generation,
                    "metric": key,
                    "value": value,
                    "type": "sign_change",
                    "previous": recent_values[-1],
                }

        elif key == "order_parameter_r":
            # Spike = change rate > r_threshold per generation
            if len(recent_values) >= 1:
                delta = abs(value - recent_values[-1])
                if delta > self._cfg.r_threshold:
                    return {
                        "generation": generation,
                        "metric": key,
                        "value": value,
                        "type": "rate_spike",
                        "delta": delta,
                    }

        elif key in ("phi", "integrated_information"):
            # Spike = exceeds critical threshold
            if value > self._cfg.phi_critical:
                return {
                    "generation": generation,
                    "metric": key,
                    "value": value,
                    "type": "threshold_exceeded",
                }

        else:
            # Default: sigma-based detection (betti, euler, etc.)
            mean = np.mean(recent_values)
            std = np.std(recent_values)
            if std > 0:
                if abs(value - mean) > self._cfg.sigma_threshold * std:
                    return {
                        "generation": generation,
                        "metric": key,
                        "value": value,
                        "type": "sigma_spike",
                        "sigma": float(abs(value - mean) / std),
                    }
            elif abs(value - mean) > 0:
                # Zero variance history: report with capped sigma instead
                # of inf to avoid numerical artifacts in downstream analysis.
                return {
                    "generation": generation,
                    "metric": key,
                    "value": value,
                    "type": "sigma_spike",
                    "sigma": min(abs(value - mean), 1e6),
                }

        return None
