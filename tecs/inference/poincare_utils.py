"""Poincare disk utilities: embedding generation + hyperbolic distance."""
from __future__ import annotations

import numpy as np
import networkx as nx


def poincare_distance(u: np.ndarray, v: np.ndarray, eps: float = 1e-7) -> float:
    """Compute distance between two points in the Poincare disk.

    d(u,v) = arccosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
    """
    diff_sq = float(np.sum((u - v) ** 2))
    norm_u_sq = float(np.sum(u ** 2))
    norm_v_sq = float(np.sum(v ** 2))
    denom = (1.0 - norm_u_sq) * (1.0 - norm_v_sq)
    if denom < eps:
        return 30.0  # boundary → effectively infinite
    arg = 1.0 + 2.0 * diff_sq / max(denom, eps)
    return float(np.arccosh(max(arg, 1.0 + eps)))


# -- Ouroboros constants --
OUROBOROS_THETA = 0.85   # boundary norm threshold for wormhole activation
OUROBOROS_SIGMA = 0.15   # distance compression ratio through wormhole

# Module-level config: set to False to revert to legacy -v behavior
USE_FUCHSIAN = True

_default_group = None


def _get_default_group(dim: int = 2):
    from tecs.inference.ouroboros_geometry import FuchsianGroup
    global _default_group
    if _default_group is None or _default_group._dim != dim:
        _default_group = FuchsianGroup(dim=dim, use_fuchsian=USE_FUCHSIAN)
    return _default_group


def ouroboros_distance(
    u: np.ndarray, v: np.ndarray,
    analogy_mode: bool = False,
    theta: float = OUROBOROS_THETA,
    sigma: float = OUROBOROS_SIGMA,
    eps: float = 1e-7,
) -> tuple[float, bool]:
    """Compute Ouroboros-aware distance between two points.

    The wormhole only activates when *analogy_mode=True* AND both
    points lie near the boundary (||u||, ||v|| > theta).  This
    prevents indiscriminate compression that would hurt entailment
    and contradiction tasks.

    Returns (distance, used_wormhole).
    """
    raw = poincare_distance(u, v, eps)

    if analogy_mode:
        norm_u = float(np.linalg.norm(u))
        norm_v = float(np.linalg.norm(v))
        if norm_u > theta and norm_v > theta:
            # Both at the periphery → Fuchsian boundary identification
            dim = len(u)
            group = _get_default_group(dim)
            quotient_raw = group.quotient_distance(u, v)
            wormhole_dist = quotient_raw * sigma
            return wormhole_dist, True

    return raw, False


def adaptive_sigma(
    embeddings: dict[int, np.ndarray], theta: float = OUROBOROS_THETA,
) -> float:
    """Compute a data-driven wormhole compression ratio.

    Finds all boundary nodes (||emb|| > theta), computes pairwise
    Poincare distances among them, and returns sigma = 1/median_dist
    clamped to [0.05, 0.30].  Falls back to OUROBOROS_SIGMA when fewer
    than 2 boundary nodes exist.
    """
    boundary = [emb for emb in embeddings.values() if np.linalg.norm(emb) > theta]
    if len(boundary) < 2:
        return OUROBOROS_SIGMA
    dists = []
    for i in range(len(boundary)):
        for j in range(i + 1, len(boundary)):
            dists.append(poincare_distance(boundary[i], boundary[j]))
    if not dists:
        return OUROBOROS_SIGMA
    median_dist = float(np.median(dists))
    if median_dist < 1e-6:
        return 0.30
    sigma = 1.0 / median_dist
    return float(np.clip(sigma, 0.05, 0.30))


def generate_poincare_embeddings(
    G: nx.Graph, dim: int = 2, max_radius: float = 0.95, seed: int = 42,
) -> dict[int, np.ndarray]:
    """Generate Poincare disk embeddings from graph structure.

    Strategy: spectral layout → project into Poincare disk.
    Nodes with high centrality (abstract/general concepts) map near the center,
    peripheral nodes map near the boundary.
    """
    rng = np.random.default_rng(seed)
    nodes = list(G.nodes())
    n = len(nodes)
    if n == 0:
        return {}

    # 1. Compute graph-based centrality (closeness) → determines radial position
    try:
        centrality = nx.closeness_centrality(G)
    except Exception:
        centrality = {node: 0.5 for node in nodes}

    # 2. Spectral layout for angular coordinates
    try:
        if n > 2 and nx.is_connected(G):
            layout = nx.spectral_layout(G, dim=dim)
        else:
            layout = nx.spring_layout(G, dim=dim, seed=seed, iterations=50)
    except Exception:
        layout = nx.spring_layout(G, dim=dim, seed=seed)

    # 3. Map to Poincare disk:
    #    - centrality → radial distance (high centrality = near center)
    #    - spectral coords → angular direction
    #
    # Use rank-based (quantile) mapping to ensure the full disk radius
    # is utilized regardless of how clustered the raw centrality values are.
    cent_values = np.array([centrality.get(node, 0.5) for node in nodes])
    # Rank-based normalization: each node's position in the centrality ranking
    # determines its radius, uniformly spreading nodes from center to boundary.
    ranks = np.argsort(np.argsort(cent_values)).astype(float)  # 0 = lowest centrality
    if n > 1:
        cent_quantile = ranks / (n - 1)  # 0.0 (least central) to 1.0 (most central)
    else:
        cent_quantile = np.array([0.5])

    embeddings = {}
    for i, node in enumerate(nodes):
        # High centrality (rank=1.0) → center (radius ≈ 0)
        # Low centrality (rank=0.0) → boundary (radius ≈ max_radius)
        radius = max_radius * (1.0 - cent_quantile[i])

        # Get angular direction from layout
        pos = layout.get(node)
        if pos is not None:
            pos = np.array(pos, dtype=np.float64)
            norm = np.linalg.norm(pos)
            if norm > 1e-8:
                direction = pos / norm
            else:
                angle = rng.uniform(0, 2 * np.pi)
                direction = np.array([np.cos(angle), np.sin(angle)])
        else:
            angle = rng.uniform(0, 2 * np.pi)
            direction = np.array([np.cos(angle), np.sin(angle)])

        # Ensure we stay strictly inside the disk
        radius = min(radius, max_radius)
        embeddings[node] = direction[:dim] * radius

    return embeddings
