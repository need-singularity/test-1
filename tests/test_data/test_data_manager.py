# tests/test_data/test_data_manager.py
"""Tests for DataManager and its underlying generators."""
from __future__ import annotations

import numpy as np
import pytest

from tecs.data.data_manager import DataManager
from tecs.data.synthetic_generator import SyntheticGenerator


# ---------------------------------------------------------------------------
# DataManager — synthetic mode (use_external=False)
# ---------------------------------------------------------------------------


def _dm() -> DataManager:
    return DataManager(cache_dir="data/", use_external=False, seed=42)


def test_get_points_returns_array():
    dm = _dm()
    points = dm.get_points(n=50, dim=3)
    assert isinstance(points, np.ndarray)
    assert points.shape == (50, 3)


def test_get_points_correct_dim():
    dm = _dm()
    points = dm.get_points(n=10, dim=5)
    assert points.shape == (10, 5)


def test_get_concept_relations():
    dm = _dm()
    relations = dm.get_concept_relations(n=100)
    assert len(relations) > 0
    assert all("head" in r and "relation" in r and "tail" in r for r in relations)


def test_get_concept_relations_count():
    dm = _dm()
    relations = dm.get_concept_relations(n=30)
    assert len(relations) == 30


def test_get_contradictions():
    dm = _dm()
    pairs = dm.get_contradictions(n=50)
    assert len(pairs) > 0
    assert all("positive" in p and "negative" in p for p in pairs)


def test_get_contradictions_structure():
    dm = _dm()
    pairs = dm.get_contradictions(n=10)
    for pair in pairs:
        pos = pair["positive"]
        neg = pair["negative"]
        assert pos["head"] == neg["head"]
        assert pos["tail"] == neg["tail"]
        assert pos["relation"] != neg["relation"]


def test_get_analogies():
    dm = _dm()
    analogies = dm.get_analogies(n=50)
    assert len(analogies) > 0


def test_get_analogies_structure():
    dm = _dm()
    analogies = dm.get_analogies(n=20)
    for a in analogies:
        assert "a" in a and "b" in a and "c" in a and "d" in a
        assert "relation" in a


# ---------------------------------------------------------------------------
# SyntheticGenerator — direct tests
# ---------------------------------------------------------------------------


def test_synthetic_points_shape():
    gen = SyntheticGenerator(seed=0)
    pts = gen.get_points(n=20, dim=4)
    assert pts.shape == (20, 4)


def test_synthetic_relations_not_empty():
    gen = SyntheticGenerator(seed=0)
    rels = gen.get_concept_relations(n=10)
    assert len(rels) == 10


def test_synthetic_contradictions_count():
    gen = SyntheticGenerator(seed=0)
    pairs = gen.get_contradictions(n=15)
    assert len(pairs) == 15


def test_synthetic_analogies_count():
    gen = SyntheticGenerator(seed=0)
    analogies = gen.get_analogies(n=25)
    assert len(analogies) == 25


# ---------------------------------------------------------------------------
# DataManager — use_external=True falls back to synthetic when unavailable
# ---------------------------------------------------------------------------


def test_use_external_fallback_returns_data():
    """With use_external=True but no cached data/network, should fall back."""
    dm = DataManager(cache_dir="/tmp/tecs_test_cache_nonexistent/", use_external=True, seed=7)
    relations = dm.get_concept_relations(n=20)
    assert len(relations) > 0
    assert all("head" in r and "relation" in r and "tail" in r for r in relations)


# ---------------------------------------------------------------------------
# CLI __main__ smoke test
# ---------------------------------------------------------------------------


def test_main_no_args_exits_zero():
    from tecs.data.__main__ import main

    rc = main([])
    assert rc == 0
