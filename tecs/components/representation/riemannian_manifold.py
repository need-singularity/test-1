# tecs/components/representation/riemannian_manifold.py
from __future__ import annotations
import numpy as np
import networkx as nx
from scipy.spatial import KDTree
from tecs.types import TopologyState


class RiemannianManifoldComponent:
    name = "riemannian_manifold"
    layer = "representation"
    compatible_types = ["graph"]

    def __init__(self):
        self._params = {"k_neighbors": 5}

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        points = state.metadata.get("points")
        if points is None:
            raise ValueError("No 'points' in state.metadata")
        k = state.metadata.get("k_neighbors", self._params["k_neighbors"])
        tree = KDTree(points)
        G = nx.Graph()
        for i in range(len(points)):
            G.add_node(i, pos=points[i])
        distances, indices = tree.query(points, k=k + 1)
        for i in range(len(points)):
            for j_idx in range(1, k + 1):
                j = indices[i][j_idx]
                d = distances[i][j_idx]
                if not G.has_edge(i, j):
                    G.add_edge(i, j, weight=d)
        curvatures = np.array([1.0 - G.degree(n) / (2 * k) for n in G.nodes])
        return TopologyState(
            complex=G,
            complex_type="graph",
            curvature=curvatures,
            metrics=state.metrics.copy(),
            history=state.history + [
                {"action": "build_knn_graph", "n_nodes": len(G.nodes), "n_edges": len(G.edges)}
            ],
            metadata=state.metadata.copy(),
        )

    def measure(self, state: TopologyState) -> dict[str, float]:
        c = state.curvature
        return {
            "mean_curvature": float(np.mean(c)) if len(c) > 0 else 0.0,
            "max_curvature": float(np.max(np.abs(c))) if len(c) > 0 else 0.0,
            "std_curvature": float(np.std(c)) if len(c) > 0 else 0.0,
        }

    def cost(self) -> float:
        return 0.2
