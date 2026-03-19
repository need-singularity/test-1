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
