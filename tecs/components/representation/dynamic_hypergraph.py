# tecs/components/representation/dynamic_hypergraph.py
from __future__ import annotations
import numpy as np
from scipy.spatial.distance import pdist, squareform
from tecs.types import TopologyState

try:
    import hypernetx as hnx
except ImportError:
    hnx = None


class DynamicHypergraphComponent:
    name = "dynamic_hypergraph"
    layer = "representation"
    compatible_types = ["hypergraph"]

    def __init__(self):
        self._params = {"cluster_threshold": 1.0, "min_cluster_size": 2}

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        if hnx is None:
            raise ImportError("hypernetx is required for DynamicHypergraphComponent")
        points = state.metadata.get("points")
        if points is None:
            raise ValueError("No 'points' in state.metadata")
        threshold = state.metadata.get("cluster_threshold", self._params["cluster_threshold"])
        dist_matrix = squareform(pdist(points))
        hyperedges: dict[str, tuple] = {}
        for i in range(len(points)):
            neighbors = tuple(sorted(np.where(dist_matrix[i] < threshold)[0]))
            if len(neighbors) >= self._params["min_cluster_size"]:
                key = f"he_{i}"
                hyperedges[key] = neighbors
        H = hnx.Hypergraph(hyperedges)
        return TopologyState(
            complex=H,
            complex_type="hypergraph",
            curvature=np.array([]),
            metrics=state.metrics.copy(),
            history=state.history + [{"action": "build_hypergraph", "n_hyperedges": len(hyperedges)}],
            metadata=state.metadata.copy(),
        )

    def measure(self, state: TopologyState) -> dict[str, float]:
        H = state.complex
        edges = list(H.edges)
        sizes = [len(H.edges[e]) for e in edges] if edges else [0]
        return {
            "n_hyperedges": float(len(edges)),
            "mean_hyperedge_size": float(np.mean(sizes)),
            "max_hyperedge_size": float(max(sizes)),
        }

    def cost(self) -> float:
        return 0.25
