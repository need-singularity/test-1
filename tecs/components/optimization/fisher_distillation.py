# tecs/components/optimization/fisher_distillation.py
from __future__ import annotations
import numpy as np
import networkx as nx
from tecs.types import TopologyState


class FisherDistillationComponent:
    name = "fisher_distillation"
    layer = "optimization"
    compatible_types = ["graph"]

    def __init__(self):
        self._params = {"alpha": 0.5, "k_eigenvalues": 5}
        self._compression_ratio: float = 1.0
        self._mean_weight: float = 0.0
        self._info_retained: float = 1.0

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        G = state.complex
        if G is None or not isinstance(G, nx.Graph):
            raise ValueError("state.complex must be a networkx Graph")

        alpha = float(self._params.get("alpha", 0.5))
        k = int(self._params.get("k_eigenvalues", 5))

        G_new = G.copy()
        nodes = list(G_new.nodes())
        n_nodes = len(nodes)

        if n_nodes == 0 or G_new.number_of_edges() == 0:
            self._compression_ratio = 1.0
            self._mean_weight = 0.0
            self._info_retained = 1.0
            return TopologyState(
                complex=G_new,
                complex_type="graph",
                curvature=state.curvature.copy() if len(state.curvature) > 0 else np.array([]),
                metrics=state.metrics.copy(),
                history=state.history + [{"action": "fisher_distillation", "k": k, "alpha": alpha}],
                metadata=state.metadata.copy(),
            )

        # Build a weight matrix W where W[i,j] = edge weight or 0
        node_idx = {n: i for i, n in enumerate(nodes)}
        W = np.zeros((n_nodes, n_nodes))
        for u, v, data in G_new.edges(data=True):
            w = float(data.get("weight", 1.0))
            i, j = node_idx[u], node_idx[v]
            W[i, j] = w
            W[j, i] = w

        # Compute per-node covariance of edge weights (Fisher-information proxy)
        # For each node, gather neighbor weights and compute covariance matrix
        # of shape (degree, degree). Summarize by eigendecomposition.

        # Build global covariance matrix of weight rows
        # Each row of W is a "weight feature vector" for that node
        W_centered = W - W.mean(axis=1, keepdims=True)
        cov = W_centered.T @ W_centered / max(n_nodes - 1, 1)  # (n_nodes x n_nodes)

        # Eigen-decomposition
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        # Sort descending
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        # Keep only positive eigenvalues
        positive_mask = eigenvalues > 0
        if not np.any(positive_mask):
            total_variance = 1.0
            info_retained = 1.0
        else:
            total_variance = float(np.sum(eigenvalues[positive_mask]))
            k_actual = min(k, int(np.sum(positive_mask)))
            retained_variance = float(np.sum(eigenvalues[:k_actual][positive_mask[:k_actual]]))
            info_retained = retained_variance / total_variance if total_variance > 0 else 1.0

        # Project weights onto top-k eigenvectors to get a compressed representation
        k_actual = min(k, n_nodes)
        V_k = eigenvectors[:, :k_actual]  # (n_nodes x k)
        # Compressed representation of W
        W_compressed = W @ V_k @ V_k.T  # (n_nodes x n_nodes)

        # Adjust edge weights: blend original with compressed
        weights_before = []
        weights_after = []
        for u, v, data in G_new.edges(data=True):
            i, j = node_idx[u], node_idx[v]
            w_orig = float(data.get("weight", 1.0))
            w_new = float((1 - alpha) * w_orig + alpha * abs(W_compressed[i, j]))
            w_new = max(1e-6, w_new)
            G_new[u][v]["weight"] = w_new
            weights_before.append(w_orig)
            weights_after.append(w_new)

        mean_weight = float(np.mean(weights_after)) if weights_after else 0.0
        compression_ratio = float(k_actual) / float(n_nodes) if n_nodes > 0 else 1.0

        self._compression_ratio = compression_ratio
        self._mean_weight = mean_weight
        self._info_retained = info_retained

        new_metrics = state.metrics.copy()
        new_metrics["compression_ratio"] = compression_ratio
        new_metrics["mean_weight"] = mean_weight
        new_metrics["info_retained"] = info_retained

        return TopologyState(
            complex=G_new,
            complex_type="graph",
            curvature=state.curvature.copy() if len(state.curvature) > 0 else np.array([]),
            metrics=new_metrics,
            history=state.history + [
                {
                    "action": "fisher_distillation",
                    "k": k_actual,
                    "alpha": alpha,
                    "compression_ratio": compression_ratio,
                    "info_retained": info_retained,
                }
            ],
            metadata=state.metadata.copy(),
        )

    def measure(self, state: TopologyState) -> dict[str, float]:
        compression_ratio = state.metrics.get("compression_ratio", self._compression_ratio)
        mean_weight = state.metrics.get("mean_weight", self._mean_weight)
        info_retained = state.metrics.get("info_retained", self._info_retained)
        return {
            "compression_ratio": compression_ratio,
            "mean_weight": mean_weight,
            "info_retained": info_retained,
        }

    def cost(self) -> float:
        return 0.5
