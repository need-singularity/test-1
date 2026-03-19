# tecs/components/emergence/lyapunov_bifurcation.py
from __future__ import annotations
import numpy as np
from tecs.types import TopologyState


def _simple_dynamics(x: np.ndarray) -> np.ndarray:
    """A simple nonlinear map: x_{n+1} = tanh(x_n) + 0.1 * x_n^2."""
    return np.tanh(x) + 0.1 * x ** 2


class LyapunovBifurcationComponent:
    name = "lyapunov_bifurcation"
    layer = "emergence"
    compatible_types = ["graph"]

    def __init__(self):
        self._params = {"perturbation_scale": 1e-5, "n_steps": 100}

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        curvature = state.curvature
        if len(curvature) == 0:
            return TopologyState(
                complex=state.complex,
                complex_type=state.complex_type,
                curvature=state.curvature.copy(),
                metrics=state.metrics.copy(),
                history=state.history + [
                    {
                        "action": "lyapunov_bifurcation",
                        "lyapunov_exponent": 0.0,
                        "is_chaotic": False,
                    }
                ],
                metadata=state.metadata.copy(),
            )

        eps = float(self._params["perturbation_scale"])
        n_steps = int(self._params["n_steps"])

        rng = np.random.default_rng(seed=7)
        trajectory = curvature.copy().astype(float)
        delta0 = rng.normal(0.0, eps, size=len(trajectory))
        perturbed = trajectory + delta0

        delta_norm_0 = float(np.linalg.norm(delta0))
        if delta_norm_0 == 0.0:
            delta_norm_0 = eps

        for _ in range(n_steps):
            trajectory = _simple_dynamics(trajectory)
            perturbed = _simple_dynamics(perturbed)

        delta_t = perturbed - trajectory
        delta_norm_t = float(np.linalg.norm(delta_t))
        if delta_norm_t == 0.0:
            delta_norm_t = 1e-300

        lyapunov_exp = float(np.log(delta_norm_t / delta_norm_0) / n_steps)
        is_chaotic = lyapunov_exp > 0.0

        return TopologyState(
            complex=state.complex,
            complex_type=state.complex_type,
            curvature=state.curvature.copy(),
            metrics=state.metrics.copy(),
            history=state.history + [
                {
                    "action": "lyapunov_bifurcation",
                    "lyapunov_exponent": lyapunov_exp,
                    "is_chaotic": is_chaotic,
                    "n_steps": n_steps,
                }
            ],
            metadata=state.metadata.copy(),
        )

    def measure(self, state: TopologyState) -> dict[str, float]:
        lyapunov_exp = 0.0
        is_chaotic = False
        for entry in reversed(state.history):
            if entry.get("action") == "lyapunov_bifurcation":
                lyapunov_exp = float(entry.get("lyapunov_exponent", 0.0))
                is_chaotic = bool(entry.get("is_chaotic", False))
                break
        return {
            "lyapunov_exponent": lyapunov_exp,
            "is_chaotic": float(is_chaotic),
        }

    def cost(self) -> float:
        return 0.4
