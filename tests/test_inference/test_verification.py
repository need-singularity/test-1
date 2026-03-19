# tests/test_inference/test_verification.py
import numpy as np
import networkx as nx
import pytest

from tecs.inference.verification import (
    check_group_invariance, check_triangle_inequality, compute_injectivity_radii,
)
from tecs.inference.ouroboros_geometry import FuchsianGroup
from tecs.inference.poincare_utils import generate_poincare_embeddings


class TestVerificationMetrics:
    def _make_fg_and_emb(self):
        G = nx.cycle_graph(20)
        emb = generate_poincare_embeddings(G)
        fg = FuchsianGroup(dim=2)
        return fg, emb

    def test_group_invariance_metric(self):
        fg, emb = self._make_fg_and_emb()
        violation_rate = check_group_invariance(fg, emb, n_samples=50)
        # With finite orbit depth, small violation rates are expected
        assert violation_rate < 0.20

    def test_triangle_inequality_metric(self):
        fg, emb = self._make_fg_and_emb()
        violation_rate = check_triangle_inequality(fg, emb, n_samples=50)
        # With finite orbit depth, small violation rates are expected
        assert violation_rate < 0.10

    def test_injectivity_radius(self):
        fg, emb = self._make_fg_and_emb()
        radii = compute_injectivity_radii(fg, emb)
        assert len(radii) > 0
        assert all(r > 0 for r in radii)
