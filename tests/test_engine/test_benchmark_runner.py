# tests/test_engine/test_benchmark_runner.py
import numpy as np
import networkx as nx

from tecs.types import TopologyState
from tecs.data.data_manager import DataManager
from tecs.engine.benchmark_runner import BenchmarkRunner


def _graph_state() -> TopologyState:
    G = nx.karate_club_graph()
    return TopologyState(
        complex=G,
        complex_type="graph",
        curvature=np.zeros(len(G.nodes)),
    )


def test_concept_relation_returns_score():
    dm = DataManager(use_external=False)
    runner = BenchmarkRunner(dm)
    state = _graph_state()
    score = runner.run_concept_relation(state)
    assert 0.0 <= score <= 1.0


def test_contradiction_returns_score():
    dm = DataManager(use_external=False)
    runner = BenchmarkRunner(dm)
    state = _graph_state()
    score = runner.run_contradiction(state)
    assert 0.0 <= score <= 1.0


def test_analogy_returns_score():
    dm = DataManager(use_external=False)
    runner = BenchmarkRunner(dm)
    state = _graph_state()
    score = runner.run_analogy(state)
    assert 0.0 <= score <= 1.0


def test_run_all_combined():
    dm = DataManager(use_external=False)
    runner = BenchmarkRunner(dm)
    state = _graph_state()
    scores = runner.run_all(state)
    assert "combined" in scores
    assert abs(
        scores["combined"]
        - (scores["concept"] + scores["contradiction"] + scores["analogy"]) / 3
    ) < 0.001


def test_run_all_keys():
    dm = DataManager(use_external=False)
    runner = BenchmarkRunner(dm)
    state = _graph_state()
    scores = runner.run_all(state)
    for key in ("concept", "contradiction", "analogy", "combined"):
        assert key in scores
        assert 0.0 <= scores[key] <= 1.0


def test_empty_graph_returns_zero():
    dm = DataManager(use_external=False)
    runner = BenchmarkRunner(dm)
    G = nx.Graph()
    state = TopologyState(complex=G, complex_type="graph", curvature=np.array([]))
    assert runner.run_concept_relation(state) == 0.0
    assert runner.run_contradiction(state) == 0.0
    assert runner.run_analogy(state) == 0.0
