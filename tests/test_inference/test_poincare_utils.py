# tests/test_inference/test_poincare_utils.py
import numpy as np
import pytest
from tecs.inference.poincare_utils import (
    poincare_distance, ouroboros_distance, adaptive_sigma,
)


class TestOuroborosWithFuchsian:
    def test_ouroboros_boundary_pair_shorter_than_direct(self):
        u = np.array([0.90, 0.15])
        v = np.array([-0.85, 0.20])
        d_raw = poincare_distance(u, v)
        d_ouro, wh = ouroboros_distance(u, v, analogy_mode=True)
        assert wh is True
        assert d_ouro < d_raw

    def test_ouroboros_center_pair_unchanged(self):
        u = np.array([0.1, 0.2])
        v = np.array([0.3, 0.1])
        d_raw = poincare_distance(u, v)
        d_ouro, wh = ouroboros_distance(u, v, analogy_mode=True)
        assert wh is False
        assert abs(d_ouro - d_raw) < 1e-6

    def test_ouroboros_analogy_mode_false(self):
        u = np.array([0.90, 0.15])
        v = np.array([-0.85, 0.20])
        d_ouro, wh = ouroboros_distance(u, v, analogy_mode=False)
        assert wh is False

    def test_ouroboros_quotient_better_than_antipodal(self):
        u = np.array([0.90, 0.15])
        v = np.array([-0.85, 0.20])
        d_old_antipodal = min(poincare_distance(u, v), poincare_distance(u, -v))
        from tecs.inference.ouroboros_geometry import FuchsianGroup
        fg = FuchsianGroup(dim=2)
        d_quotient = fg.quotient_distance(u, v)
        assert d_quotient <= d_old_antipodal + 1e-6


class TestAdaptiveSigma:
    def test_returns_float(self):
        embeddings = {
            0: np.array([0.90, 0.10]),
            1: np.array([-0.88, 0.15]),
            2: np.array([0.30, 0.20]),
            3: np.array([0.92, -0.10]),
        }
        sigma = adaptive_sigma(embeddings, theta=0.85)
        assert isinstance(sigma, float)

    def test_clamped_range(self):
        embeddings = {i: np.array([0.90, 0.01 * i]) for i in range(20)}
        sigma = adaptive_sigma(embeddings, theta=0.85)
        assert 0.05 <= sigma <= 0.30

    def test_no_boundary_nodes_returns_default(self):
        embeddings = {
            0: np.array([0.10, 0.10]),
            1: np.array([0.20, 0.15]),
        }
        sigma = adaptive_sigma(embeddings, theta=0.85)
        assert sigma == 0.15  # default fallback


import networkx as nx
from tecs.inference.poincare_utils import (
    ollivier_ricci_curvature, compute_ricci_flow, detect_neck_pinch,
    generate_poincare_embeddings,
)


class TestOllivierRicci:
    def _make_graph_and_embeddings(self):
        G = nx.karate_club_graph()
        emb = generate_poincare_embeddings(G)
        return G, emb

    def test_curvature_returns_float(self):
        G, emb = self._make_graph_and_embeddings()
        edge = list(G.edges())[0]
        k = ollivier_ricci_curvature(G, edge[0], edge[1], embeddings=emb)
        assert isinstance(k, float)

    def test_curvature_range(self):
        G, emb = self._make_graph_and_embeddings()
        for u, v in list(G.edges())[:10]:
            k = ollivier_ricci_curvature(G, u, v, embeddings=emb)
            assert np.isfinite(k), f"Curvature not finite: {k}"

    def test_curvature_unequal_degree(self):
        G = nx.star_graph(5)
        emb = generate_poincare_embeddings(G)
        k = ollivier_ricci_curvature(G, 0, 1, embeddings=emb)
        assert isinstance(k, float)


class TestRicciFlow:
    def test_returns_curvature_history(self):
        G = nx.karate_club_graph()
        emb = generate_poincare_embeddings(G)
        result = compute_ricci_flow(G, emb, iterations=3)
        assert isinstance(result, dict)
        for edge, history in result.items():
            assert len(history) == 3
            assert all(isinstance(h, float) for h in history)

    def test_flow_reduces_variance(self):
        G = nx.karate_club_graph()
        emb = generate_poincare_embeddings(G)
        result = compute_ricci_flow(G, emb, iterations=5)
        first_curvatures = [h[0] for h in result.values()]
        last_curvatures = [h[-1] for h in result.values()]
        var_first = np.var(first_curvatures)
        var_last = np.var(last_curvatures)
        assert var_last <= var_first * 2.0


class TestNeckPinch:
    def test_returns_list_of_tuples(self):
        curvature_map = {(0, 1): 0.3, (1, 2): 0.8, (2, 3): -0.1, (3, 4): 1.5}
        result = detect_neck_pinch(curvature_map)
        assert isinstance(result, list)
        for item in result:
            assert len(item) == 3

    def test_data_driven_threshold(self):
        curvature_map = {
            (0, 1): 0.0, (1, 2): 0.2, (2, 3): 0.4,
            (3, 4): 0.5, (4, 5): 0.7, (5, 6): 2.0,
        }
        result = detect_neck_pinch(curvature_map)
        assert len(result) >= 1
        assert all(k > 0 for _, _, k in result)

    def test_custom_threshold(self):
        curvature_map = {(0, 1): 0.3, (1, 2): 0.8, (2, 3): 1.5}
        result = detect_neck_pinch(curvature_map, threshold=0.5)
        assert len(result) == 2
