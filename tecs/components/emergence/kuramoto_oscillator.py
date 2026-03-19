# tecs/components/emergence/kuramoto_oscillator.py
from __future__ import annotations
import numpy as np
from scipy.integrate import solve_ivp
import networkx as nx
from tecs.types import TopologyState
from tecs.utils.mps_utils import to_tensor, to_numpy, is_gpu_available


def _extract_graph(state: TopologyState) -> nx.Graph:
    """Extract a NetworkX graph from a graph or simplicial state."""
    if state.complex_type == "graph":
        return state.complex
    # simplicial: extract 1-skeleton as a graph
    stree = state.complex
    G = nx.Graph()
    # Support both gudhi SimplexTree and _FallbackSimplexTree
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


class KuramotoOscillatorComponent:
    name = "kuramoto_oscillator"
    layer = "emergence"
    compatible_types = ["graph", "simplicial"]

    def __init__(self):
        self._params = {"n_steps": 50, "K": 2.0, "dt": 0.1}

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        G = _extract_graph(state)
        nodes = list(G.nodes())
        N = len(nodes)
        if N == 0:
            return TopologyState(
                complex=state.complex,
                complex_type=state.complex_type,
                curvature=state.curvature.copy(),
                metrics=state.metrics.copy(),
                history=state.history + [{"action": "kuramoto_oscillator", "n_nodes": 0}],
                metadata={**state.metadata, "phases": np.array([])},
            )

        node_idx = {n: i for i, n in enumerate(nodes)}
        rng = np.random.default_rng(seed=0)
        omega = rng.normal(0.0, 1.0, size=N)          # natural frequencies
        theta0 = rng.uniform(0.0, 2 * np.pi, size=N)  # initial phases

        K = float(self._params["K"])
        dt = float(self._params["dt"])
        n_steps = int(self._params["n_steps"])
        t_end = n_steps * dt

        # Build adjacency list and matrix for ODE evaluation
        adj = [[] for _ in range(N)]
        adj_matrix = np.zeros((N, N), dtype=np.float32)
        for u, v in G.edges():
            i, j = node_idx[u], node_idx[v]
            adj[i].append(j)
            adj[j].append(i)
            adj_matrix[i, j] = 1.0
            adj_matrix[j, i] = 1.0

        use_gpu = is_gpu_available() and N > 200

        if use_gpu:
            import torch
            omega_tensor = to_tensor(omega)
            adj_tensor = to_tensor(adj_matrix)

            def kuramoto_rhs(t, theta):
                theta_t = to_tensor(theta)  # (N,)
                # Compute all pairwise differences: theta_j - theta_i
                diff = theta_t.unsqueeze(1) - theta_t.unsqueeze(0)  # (N, N)
                # Apply adjacency mask and sin
                coupling = (K / N) * (adj_tensor * torch.sin(diff)).sum(dim=1)  # (N,)
                dtheta = omega_tensor + to_numpy(coupling)
                return dtheta
        else:
            def kuramoto_rhs(t, theta):
                dtheta = omega.copy()
                for i in range(N):
                    if adj[i]:
                        coupling = np.sum(np.sin(theta[adj[i]] - theta[i]))
                        dtheta[i] += K / N * coupling
                return dtheta

        sol = solve_ivp(
            kuramoto_rhs,
            (0.0, t_end),
            theta0,
            method="RK45",
            max_step=dt,
            dense_output=False,
        )
        phases = sol.y[:, -1] if sol.success and sol.y.shape[1] > 0 else theta0

        # Order parameter r = |1/N * sum(e^{i*theta})|
        z = np.mean(np.exp(1j * phases))
        order_r = float(np.abs(z))

        new_metadata = state.metadata.copy()
        new_metadata["phases"] = phases

        return TopologyState(
            complex=state.complex,
            complex_type=state.complex_type,
            curvature=state.curvature.copy() if len(state.curvature) > 0 else np.zeros(N),
            metrics=state.metrics.copy(),
            history=state.history + [
                {
                    "action": "kuramoto_oscillator",
                    "n_nodes": N,
                    "order_parameter_r": order_r,
                    "K": K,
                }
            ],
            metadata=new_metadata,
        )

    def measure(self, state: TopologyState) -> dict[str, float]:
        phases = state.metadata.get("phases", np.array([]))
        if len(phases) == 0:
            return {"order_parameter_r": 0.0, "mean_frequency": 0.0}

        z = np.mean(np.exp(1j * phases))
        order_r = float(np.abs(z))

        # Estimate instantaneous mean frequency from history if available
        mean_freq = 0.0
        for entry in reversed(state.history):
            if entry.get("action") == "kuramoto_oscillator":
                # Use natural-frequency proxy: mean phase / time not directly accessible;
                # report the order parameter from history as a proxy, and 0 as mean_freq.
                break

        # Mean frequency ~ mean of phases (proxy; proper estimate requires time derivative)
        mean_freq = float(np.mean(np.unwrap(phases))) if len(phases) > 0 else 0.0

        return {
            "order_parameter_r": order_r,
            "mean_frequency": mean_freq,
        }

    def cost(self) -> float:
        return 0.5
