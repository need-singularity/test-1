# tecs/components/verification/shadow_manifold_audit.py
from __future__ import annotations
import numpy as np
import networkx as nx
from tecs.types import TopologyState


def _mean_curvature(G: nx.Graph) -> float:
    """
    Approximate mean curvature of the graph manifold as the mean of
    node-level Ollivier-Ricci-style curvature (based on degree and weights).
    Uses: for each node, curvature = (1 - mean_weight_neighbours / degree_weighted_sum).
    A simpler stable proxy: variance of normalised edge weights divided by mean.
    Falls back to 1.0 when the graph has no edges to avoid division by zero.
    """
    edges = list(G.edges(data=True))
    if not edges:
        return 1.0
    weights = np.array([d.get("weight", 1.0) for _, _, d in edges], dtype=float)
    mean_w = float(np.mean(weights))
    if mean_w == 0.0:
        return 1.0
    # Coefficient of variation as a curvature proxy
    return float(np.std(weights) / mean_w + 1.0)


def _build_shadow_manifold(G: nx.Graph, confidence: float, rng_seed: int = 0) -> nx.Graph:
    """
    Build shadow manifold M* by perturbing edge weights with noise scaled by (1 - confidence).
    """
    rng = np.random.default_rng(seed=rng_seed)
    M_star = G.copy()
    noise_scale = 1.0 - confidence
    for u, v in M_star.edges():
        w = M_star[u][v].get("weight", 1.0)
        perturb = rng.normal(0.0, max(noise_scale, 1e-9))
        M_star[u][v]["weight"] = max(1e-6, w + perturb)
    return M_star


class ShadowManifoldAuditComponent:
    name = "shadow_manifold_audit"
    layer = "verification"
    compatible_types = ["graph"]

    def __init__(self):
        self._params: dict = {"confidence": 0.8}
        self._last_hallucination_score: float = 0.0

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        """
        Build shadow manifold M* (perturbed weights = confidence proxy),
        then compute hallucination_score between M and M*.
        """
        G: nx.Graph = state.complex
        if G is None:
            raise ValueError("state.complex must be a NetworkX graph (not None)")

        confidence = float(self._params.get("confidence", 0.8))
        M_star = _build_shadow_manifold(G, confidence)

        kappa_M = _mean_curvature(G)
        kappa_Mstar = _mean_curvature(M_star)

        hallucination_score = float(
            abs(kappa_M) * confidence / max(abs(kappa_Mstar), 1e-9)
        )
        self._last_hallucination_score = hallucination_score

        new_metrics = state.metrics.copy()
        new_metrics["hallucination_score"] = hallucination_score
        new_metrics["confidence"] = confidence

        return TopologyState(
            complex=state.complex,
            complex_type=state.complex_type,
            curvature=state.curvature.copy() if len(state.curvature) > 0 else np.array([]),
            metrics=new_metrics,
            history=state.history + [
                {
                    "action": "shadow_manifold_audit",
                    "hallucination_score": hallucination_score,
                    "confidence": confidence,
                }
            ],
            metadata=state.metadata.copy(),
        )

    def verify(self, state: TopologyState, reference: TopologyState) -> dict[str, float]:
        """
        hallucination_score = |mean_curvature(M)| * confidence / |mean_curvature(M*)|
        where M = state.complex, M* = reference.complex (acting as shadow manifold).
        """
        G: nx.Graph = state.complex
        G_ref: nx.Graph = reference.complex

        confidence = float(self._params.get("confidence", 0.8))
        kappa_M = _mean_curvature(G)
        kappa_Mstar = _mean_curvature(G_ref)

        hallucination_score = float(
            abs(kappa_M) * confidence / max(abs(kappa_Mstar), 1e-9)
        )
        return {
            "hallucination_score": hallucination_score,
            "confidence": confidence,
        }

    def measure(self, state: TopologyState) -> dict[str, float]:
        hallucination_score = state.metrics.get(
            "hallucination_score", self._last_hallucination_score
        )
        confidence = state.metrics.get("confidence", float(self._params.get("confidence", 0.8)))
        return {
            "hallucination_score": hallucination_score,
            "confidence": confidence,
        }

    def cost(self) -> float:
        return 0.4
