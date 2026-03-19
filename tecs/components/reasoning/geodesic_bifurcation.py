# tecs/components/reasoning/geodesic_bifurcation.py
from __future__ import annotations
import numpy as np
import networkx as nx
from scipy.integrate import solve_ivp
from tecs.types import TopologyState


class GeodesicBifurcationComponent:
    name = "geodesic_bifurcation"
    layer = "reasoning"
    compatible_types = ["graph"]

    def __init__(self):
        self._params = {"n_branches": 3, "perturbation_scale": 0.05}

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        G = state.complex.copy()
        n_branches = self._params["n_branches"]
        perturb = self._params["perturbation_scale"]

        # Step 1: Identify bifurcation points (nodes with high curvature variance among neighbors)
        bifurcation_nodes = self._find_bifurcation_points(G, state.curvature)

        # Step 2: Extract weight vector for ODE-based perturbation
        nodes_list = list(G.nodes)
        edges_list = list(G.edges)
        weights = np.array([G[u][v].get("weight", 1.0) for u, v in edges_list])

        # Step 3: Generate branch candidates via ODE perturbation
        rng = np.random.default_rng(seed=42)
        branches: list[tuple[np.ndarray, float]] = []
        for b in range(n_branches):
            perturbation = rng.normal(0.0, perturb, size=len(weights))
            perturbed_weights = self._ode_perturb(weights, perturbation)
            variance = float(np.var(perturbed_weights))
            branches.append((perturbed_weights, variance))

        # Step 4: Select best branch (lowest curvature variance = most stable)
        best_weights, best_variance = min(branches, key=lambda x: x[1])

        # Step 5: Apply best branch weights to graph
        G_best = G.copy()
        for i, (u, v) in enumerate(edges_list):
            G_best[u][v]["weight"] = max(0.01, float(best_weights[i]))

        # Step 6: Recompute node curvature from updated graph
        node_curv = self._compute_node_curvature(G_best, nodes_list)

        branch_stability = 1.0 / (1.0 + best_variance)

        return TopologyState(
            complex=G_best,
            complex_type="graph",
            curvature=node_curv,
            metrics=state.metrics.copy(),
            history=state.history + [
                {
                    "action": "geodesic_bifurcation",
                    "n_bifurcation_points": len(bifurcation_nodes),
                    "n_branches": n_branches,
                    "branch_stability": branch_stability,
                }
            ],
            metadata=state.metadata.copy(),
        )

    def _find_bifurcation_points(self, G: nx.Graph, curvature: np.ndarray) -> list:
        """Find nodes with high curvature variance among their neighbors."""
        if len(curvature) == 0:
            return []
        nodes_list = list(G.nodes)
        curv_map = {n: curvature[i] for i, n in enumerate(nodes_list) if i < len(curvature)}
        bifurcation_nodes = []
        variances = []
        for n in nodes_list:
            neighbors = list(G.neighbors(n))
            if len(neighbors) < 2:
                variances.append(0.0)
                continue
            neighbor_curvs = [curv_map.get(nb, 0.0) for nb in neighbors]
            variances.append(float(np.var(neighbor_curvs)))
        if not variances:
            return []
        threshold = float(np.mean(variances)) + float(np.std(variances))
        for i, n in enumerate(nodes_list):
            if i < len(variances) and variances[i] > threshold:
                bifurcation_nodes.append(n)
        return bifurcation_nodes

    def _ode_perturb(self, weights: np.ndarray, perturbation: np.ndarray) -> np.ndarray:
        """Use a simple ODE to smoothly apply perturbation to weights."""
        def dydt(t, y):
            return perturbation * np.exp(-t)

        t_span = (0.0, 1.0)
        result = solve_ivp(dydt, t_span, weights.copy(), method="RK45", dense_output=False)
        if result.success and result.y.shape[1] > 0:
            return result.y[:, -1]
        return weights + perturbation

    def _compute_node_curvature(self, G: nx.Graph, nodes_list: list) -> np.ndarray:
        """Compute simplified node curvature from edge weight variance per node."""
        node_curv = np.zeros(len(nodes_list))
        for i, n in enumerate(nodes_list):
            neighbor_weights = [G[n][nb].get("weight", 1.0) for nb in G.neighbors(n)]
            node_curv[i] = float(np.var(neighbor_weights)) if neighbor_weights else 0.0
        return node_curv

    def measure(self, state: TopologyState) -> dict[str, float]:
        history = state.history
        n_bifurcation_points = 0.0
        branch_stability = 1.0
        for entry in reversed(history):
            if entry.get("action") == "geodesic_bifurcation":
                n_bifurcation_points = float(entry.get("n_bifurcation_points", 0))
                branch_stability = float(entry.get("branch_stability", 1.0))
                break
        return {
            "n_bifurcation_points": n_bifurcation_points,
            "branch_stability": branch_stability,
        }

    def cost(self) -> float:
        return 0.6
