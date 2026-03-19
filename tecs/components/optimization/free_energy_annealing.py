# tecs/components/optimization/free_energy_annealing.py
from __future__ import annotations
import math
import numpy as np
import networkx as nx
from tecs.types import TopologyState

try:
    import gudhi
    _GUDHI_AVAILABLE = True
except ImportError:
    _GUDHI_AVAILABLE = False


def _complexity_graph(G: nx.Graph) -> float:
    """Total curvature proxy: sum of absolute edge weight deviations from mean."""
    weights = [d.get("weight", 1.0) for _, _, d in G.edges(data=True)]
    if not weights:
        return 0.0
    arr = np.array(weights, dtype=float)
    return float(np.sum(np.abs(arr - arr.mean())))


def _entropy_graph(G: nx.Graph) -> float:
    """Approximate log of automorphism count via degree sequence entropy."""
    degrees = [d for _, d in G.degree()]
    if not degrees:
        return 0.0
    total = sum(degrees)
    if total == 0:
        return 0.0
    probs = np.array(degrees, dtype=float) / total
    # Shannon entropy of degree distribution as automorphism proxy
    probs = probs[probs > 0]
    return float(-np.sum(probs * np.log(probs + 1e-12)))


def _complexity_simplicial(stree) -> float:
    """Complexity = sum of Betti numbers."""
    stree.compute_persistence()
    betti = stree.betti_numbers()
    return float(sum(betti))


def _entropy_simplicial(stree) -> float:
    """Entropy approximation based on number of simplices."""
    if _GUDHI_AVAILABLE and isinstance(stree, gudhi.SimplexTree):
        n = stree.num_simplices()
    else:
        n = len(stree._simplices)
    return math.log(n + 1)


def _free_energy(state: TopologyState, temperature: float) -> float:
    """F = C(K) - T * H(K)"""
    if state.complex_type == "graph":
        G = state.complex
        C = _complexity_graph(G)
        H = _entropy_graph(G)
    else:
        stree = state.complex
        C = _complexity_simplicial(stree)
        H = _entropy_simplicial(stree)
    return C - temperature * H


def _perturb_graph(G: nx.Graph, rng: np.random.Generator) -> nx.Graph:
    """Randomly perturb one edge weight in the graph."""
    G_new = G.copy()
    edges = list(G_new.edges())
    if not edges:
        return G_new
    idx = int(rng.integers(0, len(edges)))
    u, v = edges[idx]
    w = float(G_new[u][v].get("weight", 1.0))
    delta = float(rng.normal(0, 0.1 * max(w, 0.1)))
    G_new[u][v]["weight"] = max(1e-6, w + delta)
    return G_new


def _perturb_simplicial_fallback(stree, rng: np.random.Generator):
    """For fallback simplex tree, return the same (no-op perturbation)."""
    return stree


def _perturb_simplicial_gudhi(stree, rng: np.random.Generator):
    """Randomly perturb a filtration value in a gudhi SimplexTree."""
    pairs = list(stree.get_filtration())
    if not pairs:
        return stree
    new_st = gudhi.SimplexTree()
    idx = int(rng.integers(0, len(pairs)))
    for i, (simplex, filt) in enumerate(pairs):
        if i == idx:
            delta = float(rng.normal(0, 0.05))
            filt = max(0.0, filt + delta)
        new_st.insert(simplex, filtration=filt)
    new_st.make_filtration_non_decreasing()
    return new_st


class FreeEnergyAnnealingComponent:
    name = "free_energy_annealing"
    layer = "optimization"
    compatible_types = ["graph", "simplicial"]

    def __init__(self):
        self._params = {"initial_temp": 1.0, "cooling_rate": 0.95, "n_steps": 50}
        self._last_free_energy: float = 0.0
        self._last_temperature: float = 1.0
        self._last_acceptance_rate: float = 0.0

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        if state.complex is None:
            raise ValueError("state.complex must not be None")

        initial_temp = float(self._params.get("initial_temp", 1.0))
        cooling_rate = float(self._params.get("cooling_rate", 0.95))
        n_steps = int(self._params.get("n_steps", 50))

        rng = np.random.default_rng(seed=42)

        current_state = state
        T = initial_temp
        current_F = _free_energy(current_state, T)
        initial_F = current_F

        accepted = 0
        total = 0

        for step in range(n_steps):
            # Perturb
            if current_state.complex_type == "graph":
                new_complex = _perturb_graph(current_state.complex, rng)
            else:
                if _GUDHI_AVAILABLE and isinstance(current_state.complex, gudhi.SimplexTree):
                    new_complex = _perturb_simplicial_gudhi(current_state.complex, rng)
                else:
                    new_complex = _perturb_simplicial_fallback(current_state.complex, rng)

            candidate_state = TopologyState(
                complex=new_complex,
                complex_type=current_state.complex_type,
                curvature=current_state.curvature.copy() if len(current_state.curvature) > 0 else np.array([]),
                metrics=current_state.metrics.copy(),
                history=current_state.history,
                metadata=current_state.metadata.copy(),
            )

            new_F = _free_energy(candidate_state, T)
            delta_F = new_F - current_F

            total += 1
            if delta_F < 0:
                # Accept improvement
                current_state = candidate_state
                current_F = new_F
                accepted += 1
            else:
                # Accept with Metropolis probability
                if T > 1e-10:
                    prob = math.exp(-delta_F / T)
                    if float(rng.random()) < prob:
                        current_state = candidate_state
                        current_F = new_F
                        accepted += 1

            T = T * cooling_rate

        acceptance_rate = accepted / total if total > 0 else 0.0
        self._last_free_energy = current_F
        self._last_temperature = T
        self._last_acceptance_rate = acceptance_rate

        new_metrics = current_state.metrics.copy()
        new_metrics["free_energy"] = current_F
        new_metrics["temperature"] = T
        new_metrics["acceptance_rate"] = acceptance_rate
        new_metrics["initial_free_energy"] = initial_F

        return TopologyState(
            complex=current_state.complex,
            complex_type=current_state.complex_type,
            curvature=current_state.curvature.copy() if len(current_state.curvature) > 0 else np.array([]),
            metrics=new_metrics,
            history=state.history + [
                {
                    "action": "free_energy_annealing",
                    "n_steps": n_steps,
                    "initial_temp": initial_temp,
                    "final_temp": T,
                    "initial_free_energy": initial_F,
                    "final_free_energy": current_F,
                    "acceptance_rate": acceptance_rate,
                }
            ],
            metadata=state.metadata.copy(),
        )

    def measure(self, state: TopologyState) -> dict[str, float]:
        free_energy = state.metrics.get("free_energy", self._last_free_energy)
        temperature = state.metrics.get("temperature", self._last_temperature)
        acceptance_rate = state.metrics.get("acceptance_rate", self._last_acceptance_rate)
        return {
            "free_energy": free_energy,
            "temperature": temperature,
            "acceptance_rate": acceptance_rate,
        }

    def cost(self) -> float:
        return 0.6
