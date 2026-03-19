# tecs/components/reasoning/ricci_flow.py
from __future__ import annotations
import numpy as np
import networkx as nx
from tecs.types import TopologyState
from tecs.utils.mps_utils import to_tensor, to_numpy, is_gpu_available

class RicciFlowComponent:
    name = "ricci_flow"
    layer = "reasoning"
    compatible_types = ["graph"]

    def __init__(self):
        self._params = {"n_steps": 10, "step_size": 0.1}

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        G = state.complex.copy()
        n_steps = self._params["n_steps"]
        dt = self._params["step_size"]
        curvatures = {}
        for _ in range(n_steps):
            curvatures = self._compute_ollivier_ricci(G)
            if is_gpu_available():
                import torch
                edges = list(G.edges)
                weights = np.array([G[u][v].get("weight", 1.0) for u, v in edges])
                curvs = np.array([curvatures.get((min(u, v), max(u, v)), 0.0) for u, v in edges])

                w_tensor = to_tensor(weights)
                c_tensor = to_tensor(curvs)

                # Vectorized update on GPU
                w_tensor = torch.clamp(w_tensor - dt * c_tensor * w_tensor, min=0.01)

                new_weights = to_numpy(w_tensor)
                for idx, (u, v) in enumerate(edges):
                    G[u][v]["weight"] = float(new_weights[idx])
            else:
                # Original CPU path
                for (u, v), curv in curvatures.items():
                    w = G[u][v].get("weight", 1.0)
                    G[u][v]["weight"] = max(0.01, w - dt * curv * w)
        node_curv = np.zeros(len(G.nodes))
        nodes_list = list(G.nodes)
        for i, n in enumerate(nodes_list):
            neighbor_curvs = [curvatures.get((min(n, nb), max(n, nb)), 0.0) for nb in G.neighbors(n)]
            node_curv[i] = np.mean(neighbor_curvs) if neighbor_curvs else 0.0
        return TopologyState(
            complex=G, complex_type="graph", curvature=node_curv,
            metrics=state.metrics.copy(),
            history=state.history + [{"action": "ricci_flow", "n_steps": n_steps}],
            metadata=state.metadata.copy(),
        )

    def _compute_ollivier_ricci(self, G: nx.Graph) -> dict[tuple, float]:
        curvatures = {}
        for u, v in G.edges:
            nu = set(G.neighbors(u))
            nv = set(G.neighbors(v))
            overlap = len(nu & nv)
            total = len(nu | nv)
            curvatures[(min(u, v), max(u, v))] = (overlap / total) if total > 0 else 0.0
        return curvatures

    def measure(self, state: TopologyState) -> dict[str, float]:
        c = state.curvature
        return {
            "mean_ricci_curvature": float(np.mean(c)) if len(c) > 0 else 0.0,
            "std_ricci_curvature": float(np.std(c)) if len(c) > 0 else 0.0,
        }

    def cost(self) -> float:
        return 0.5
