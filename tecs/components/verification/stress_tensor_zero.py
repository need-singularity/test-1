# tecs/components/verification/stress_tensor_zero.py
from __future__ import annotations
import numpy as np
import networkx as nx
from tecs.types import TopologyState


def _compute_stress_tensor(G: nx.Graph) -> np.ndarray:
    """
    Compute the stress tensor as the difference between edge weights and
    approximate geodesic distances (shortest-path distances weighted by
    edge weights).

    Returns a flat array of per-edge stress values: stress_e = w_e - d_geo(u,v)
    If the graph is disconnected or a pair is unreachable, the geodesic distance
    defaults to the edge weight (zero stress for that edge).
    """
    edges = list(G.edges(data=True))
    if not edges:
        return np.array([])

    # Compute all-pairs shortest paths (weighted)
    try:
        lengths = dict(nx.all_pairs_dijkstra_path_length(G, weight="weight"))
    except Exception:
        lengths = {}

    stresses = []
    for u, v, data in edges:
        w = float(data.get("weight", 1.0))
        try:
            d_geo = float(lengths[u][v])
        except (KeyError, TypeError):
            d_geo = w  # unreachable: zero stress
        stresses.append(w - d_geo)

    return np.array(stresses, dtype=float)


class StressTensorZeroComponent:
    name = "stress_tensor_zero"
    layer = "verification"
    compatible_types = ["graph"]

    def __init__(self):
        self._params: dict = {}
        self._last_stress_magnitude: float = 0.0
        self._last_max_stress: float = 0.0

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        """
        Compute stress tensor as difference between edge weights and geodesic
        distances; store stress_magnitude and max_stress in metrics.
        """
        G: nx.Graph = state.complex
        if G is None:
            raise ValueError("state.complex must be a NetworkX graph (not None)")

        stresses = _compute_stress_tensor(G)

        if len(stresses) == 0:
            stress_magnitude = 0.0
            max_stress = 0.0
        else:
            stress_magnitude = float(np.sqrt(np.sum(stresses ** 2)))
            max_stress = float(np.max(np.abs(stresses)))

        self._last_stress_magnitude = stress_magnitude
        self._last_max_stress = max_stress

        new_metrics = state.metrics.copy()
        new_metrics["stress_magnitude"] = stress_magnitude
        new_metrics["max_stress"] = max_stress

        return TopologyState(
            complex=state.complex,
            complex_type=state.complex_type,
            curvature=state.curvature.copy() if len(state.curvature) > 0 else np.array([]),
            metrics=new_metrics,
            history=state.history + [
                {
                    "action": "stress_tensor_zero",
                    "stress_magnitude": stress_magnitude,
                    "max_stress": max_stress,
                }
            ],
            metadata=state.metadata.copy(),
        )

    def verify(self, state: TopologyState, reference: TopologyState) -> dict[str, float]:
        """
        Compare stress tensors of state and reference.
        Returns stress_magnitude for state, reference, and the delta.
        """
        G_s: nx.Graph = state.complex
        G_r: nx.Graph = reference.complex

        stress_s = _compute_stress_tensor(G_s)
        stress_r = _compute_stress_tensor(G_r)

        mag_s = float(np.sqrt(np.sum(stress_s ** 2))) if len(stress_s) > 0 else 0.0
        mag_r = float(np.sqrt(np.sum(stress_r ** 2))) if len(stress_r) > 0 else 0.0
        delta = float(abs(mag_s - mag_r))

        return {
            "stress_magnitude": mag_s,
            "stress_magnitude_reference": mag_r,
            "stress_delta": delta,
        }

    def measure(self, state: TopologyState) -> dict[str, float]:
        stress_magnitude = state.metrics.get("stress_magnitude", self._last_stress_magnitude)
        max_stress = state.metrics.get("max_stress", self._last_max_stress)
        return {
            "stress_magnitude": stress_magnitude,
            "max_stress": max_stress,
        }

    def cost(self) -> float:
        return 0.45
