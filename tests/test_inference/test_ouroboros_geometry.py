import numpy as np
import pytest
from tecs.inference.ouroboros_geometry import FuchsianGroup
from tecs.inference.poincare_utils import poincare_distance


class TestFuchsianGroupInit:
    def test_dim2_has_2_generators(self):
        fg = FuchsianGroup(dim=2)
        assert len(fg.generators()) == 2

    def test_dim3_has_6_generators(self):
        fg = FuchsianGroup(dim=3)
        assert len(fg.generators()) == 6

    def test_dim_d_has_2d_generators(self):
        fg = FuchsianGroup(dim=5)
        assert len(fg.generators()) == 10

    def test_dim_below_2_raises(self):
        with pytest.raises(ValueError):
            FuchsianGroup(dim=1)

    def test_fallback_mode_returns_legacy(self):
        fg = FuchsianGroup(dim=2, use_fuchsian=False)
        v = np.array([0.5, 0.3])
        orbit = fg.orbit(v, max_depth=2)
        assert len(orbit) == 2


class TestMoebiusTransforms:
    def test_generators_preserve_disk(self):
        fg = FuchsianGroup(dim=2)
        v = np.array([0.5, 0.3])
        for gen in fg.generators():
            w = gen(v)
            assert np.linalg.norm(w) < 1.0

    def test_generators_are_isometries(self):
        fg = FuchsianGroup(dim=2)
        u = np.array([0.3, 0.2])
        v = np.array([0.6, -0.1])
        d_orig = poincare_distance(u, v)
        for gen in fg.generators():
            d_mapped = poincare_distance(gen(u), gen(v))
            assert abs(d_mapped - d_orig) < 1e-6

    def test_dim3_generators_preserve_ball(self):
        fg = FuchsianGroup(dim=3)
        v = np.array([0.4, 0.3, 0.2])
        for gen in fg.generators():
            w = gen(v)
            assert np.linalg.norm(w) < 1.0


class TestOrbit:
    def test_orbit_includes_identity(self):
        fg = FuchsianGroup(dim=2)
        v = np.array([0.5, 0.3])
        orbit = fg.orbit(v, max_depth=1)
        assert any(np.allclose(o, v, atol=1e-6) for o in orbit)

    def test_orbit_depth0_is_just_v(self):
        fg = FuchsianGroup(dim=2)
        v = np.array([0.5, 0.3])
        orbit = fg.orbit(v, max_depth=0)
        assert len(orbit) == 1
        assert np.allclose(orbit[0], v)

    def test_orbit_depth1_more_than_depth0(self):
        fg = FuchsianGroup(dim=2)
        v = np.array([0.5, 0.3])
        o0 = fg.orbit(v, max_depth=0)
        o1 = fg.orbit(v, max_depth=1)
        assert len(o1) > len(o0)

    def test_orbit_capped_at_50(self):
        fg = FuchsianGroup(dim=2)
        v = np.array([0.5, 0.3])
        orbit = fg.orbit(v, max_depth=10)
        assert len(orbit) <= 50

    def test_orbit_deduplication(self):
        fg = FuchsianGroup(dim=2)
        v = np.array([0.5, 0.3])
        orbit = fg.orbit(v, max_depth=2)
        for i in range(len(orbit)):
            for j in range(i + 1, len(orbit)):
                d = poincare_distance(orbit[i], orbit[j])
                assert d > 0.005


class TestQuotientDistance:
    def test_quotient_leq_direct(self):
        fg = FuchsianGroup(dim=2)
        u = np.array([0.3, 0.2])
        v = np.array([-0.6, 0.1])
        d_direct = poincare_distance(u, v)
        d_quot = fg.quotient_distance(u, v)
        assert d_quot <= d_direct + 1e-6

    def test_quotient_symmetric(self):
        fg = FuchsianGroup(dim=2)
        u = np.array([0.3, 0.2])
        v = np.array([-0.6, 0.1])
        assert abs(fg.quotient_distance(u, v) - fg.quotient_distance(v, u)) < 1e-6

    def test_quotient_zero_for_same_point(self):
        fg = FuchsianGroup(dim=2)
        u = np.array([0.3, 0.2])
        assert fg.quotient_distance(u, u) < 1e-6

    def test_fallback_matches_legacy(self):
        fg = FuchsianGroup(dim=2, use_fuchsian=False)
        u = np.array([0.3, 0.2])
        v = np.array([0.8, -0.1])
        d_quot = fg.quotient_distance(u, v)
        d_legacy = min(poincare_distance(u, v), poincare_distance(u, -v))
        assert abs(d_quot - d_legacy) < 1e-6

    def test_triangle_inequality(self):
        fg = FuchsianGroup(dim=2)
        x = np.array([0.2, 0.1])
        y = np.array([-0.3, 0.4])
        z = np.array([0.5, -0.2])
        d_xz = fg.quotient_distance(x, z)
        d_xy = fg.quotient_distance(x, y)
        d_yz = fg.quotient_distance(y, z)
        assert d_xz <= d_xy + d_yz + 1e-6
