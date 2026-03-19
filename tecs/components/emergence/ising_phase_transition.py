# tecs/components/emergence/ising_phase_transition.py
from __future__ import annotations
import numpy as np
import networkx as nx
from tecs.types import TopologyState


def _extract_graph(state: TopologyState) -> nx.Graph:
    """Extract a NetworkX graph from a graph or simplicial state."""
    if state.complex_type == "graph":
        return state.complex
    # simplicial: extract 1-skeleton
    stree = state.complex
    G = nx.Graph()
    if hasattr(stree, "get_simplices"):
        # gudhi SimplexTree
        for simplex, _ in stree.get_simplices():
            if len(simplex) == 1:
                G.add_node(simplex[0])
            elif len(simplex) == 2:
                G.add_edge(simplex[0], simplex[1])
    elif hasattr(stree, "_simplices"):
        # _FallbackSimplexTree
        for simplex in stree._simplices:
            if len(simplex) == 1:
                G.add_node(simplex[0])
            elif len(simplex) == 2:
                G.add_edge(simplex[0], simplex[1])
    return G


class IsingPhaseTransitionComponent:
    name = "ising_phase_transition"
    layer = "emergence"
    compatible_types = ["graph", "simplicial"]

    def __init__(self):
        self._params = {"n_sweeps": 100, "temperature": 2.269}  # ~critical T for 2D Ising

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        G = _extract_graph(state)
        nodes = list(G.nodes())
        N = len(nodes)

        if N == 0:
            new_meta = state.metadata.copy()
            new_meta["spins"] = np.array([])
            return TopologyState(
                complex=state.complex,
                complex_type=state.complex_type,
                curvature=state.curvature.copy(),
                metrics=state.metrics.copy(),
                history=state.history + [{"action": "ising_phase_transition", "n_nodes": 0}],
                metadata=new_meta,
            )

        node_idx = {n: i for i, n in enumerate(nodes)}
        T = float(self._params["temperature"])
        n_sweeps = int(self._params["n_sweeps"])
        J = 1.0  # ferromagnetic coupling

        rng = np.random.default_rng(seed=42)
        spins = rng.choice([-1, 1], size=N).astype(float)

        # Build adjacency list
        adj = [[] for _ in range(N)]
        for u, v in G.edges():
            i, j = node_idx[u], node_idx[v]
            adj[i].append(j)
            adj[j].append(i)

        beta = 1.0 / max(T, 1e-10)

        # Metropolis sweeps
        for _ in range(n_sweeps):
            order = rng.permutation(N)
            for i in order:
                neighbor_sum = sum(spins[j] for j in adj[i])
                delta_E = 2.0 * J * spins[i] * neighbor_sum
                if delta_E <= 0.0 or rng.random() < np.exp(-beta * delta_E):
                    spins[i] = -spins[i]

        magnetization = float(np.abs(np.mean(spins)))
        energy = -J * sum(
            spins[node_idx[u]] * spins[node_idx[v]] for u, v in G.edges()
        )

        new_meta = state.metadata.copy()
        new_meta["spins"] = spins

        return TopologyState(
            complex=state.complex,
            complex_type=state.complex_type,
            curvature=state.curvature.copy() if len(state.curvature) > 0 else np.zeros(N),
            metrics=state.metrics.copy(),
            history=state.history + [
                {
                    "action": "ising_phase_transition",
                    "n_nodes": N,
                    "magnetization": magnetization,
                    "energy": energy,
                    "temperature": T,
                }
            ],
            metadata=new_meta,
        )

    def measure(self, state: TopologyState) -> dict[str, float]:
        spins = state.metadata.get("spins", np.array([]))
        if len(spins) == 0:
            return {"magnetization": 0.0, "energy": 0.0}

        G = _extract_graph(state)
        nodes = list(G.nodes())
        node_idx = {n: i for i, n in enumerate(nodes)}
        J = 1.0

        magnetization = float(np.abs(np.mean(spins)))
        energy = -J * sum(
            spins[node_idx[u]] * spins[node_idx[v]]
            for u, v in G.edges()
            if u in node_idx and v in node_idx
        )

        return {
            "magnetization": magnetization,
            "energy": float(energy),
        }

    def cost(self) -> float:
        return 0.6
