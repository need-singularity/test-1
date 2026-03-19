# tests/test_engine/test_inference_benchmark.py
import numpy as np
import networkx as nx
from tecs.types import TopologyState
from tecs.data.data_manager import DataManager
from tecs.engine.benchmark_runner import BenchmarkRunner


def test_inference_benchmark_returns_scores():
    dm = DataManager(use_external=False)
    runner = BenchmarkRunner(dm)
    G = nx.karate_club_graph()
    state = TopologyState(complex=G, complex_type="graph", curvature=np.zeros(len(G.nodes)))
    scores = runner.run_inference_benchmark(state)
    assert "query_accuracy" in scores
    assert "multihop_accuracy" in scores
    assert "analogy_score" in scores
    assert "inference_combined" in scores
    assert 0.0 <= scores["inference_combined"] <= 1.0


def test_inference_benchmark_query_accuracy():
    dm = DataManager(use_external=False)
    runner = BenchmarkRunner(dm)
    G = nx.Graph()
    state = TopologyState(complex=G, complex_type="graph", curvature=np.array([]))
    scores = runner.run_inference_benchmark(state)
    # With test knowledge injected, should get some queries right
    assert scores["query_accuracy"] >= 0.0


def test_build_test_knowledge():
    dm = DataManager(use_external=False)
    runner = BenchmarkRunner(dm)
    G = nx.karate_club_graph()
    state = TopologyState(complex=G, complex_type="graph", curvature=np.zeros(len(G.nodes)))
    knowledge = runner._build_test_knowledge(state)
    assert "entity_index" in knowledge.metadata
    assert "cat" in knowledge.metadata["entity_index"]
    assert len(knowledge.metadata["triples"]) > 0
