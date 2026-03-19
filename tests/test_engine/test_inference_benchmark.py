# tests/test_engine/test_inference_benchmark.py
import numpy as np
import networkx as nx
from tecs.types import TopologyState
from tecs.data.data_manager import DataManager
from tecs.engine.benchmark_runner import BenchmarkRunner


def test_inference_benchmark_returns_all_scores():
    dm = DataManager(use_external=False)
    runner = BenchmarkRunner(dm)
    G = nx.karate_club_graph()
    state = TopologyState(complex=G, complex_type="graph", curvature=np.zeros(len(G.nodes)))
    scores = runner.run_inference_benchmark(state)
    expected_keys = ["query_accuracy", "multihop_accuracy", "analogy_score",
                     "verification_working", "inference_combined"]
    for key in expected_keys:
        assert key in scores, f"Missing key: {key}"
        assert 0.0 <= scores[key] <= 1.0, f"{key}={scores[key]} out of range"


def test_eval_knowledge_cached():
    dm = DataManager(use_external=False)
    runner = BenchmarkRunner(dm)
    # Clear cache
    BenchmarkRunner._cached_inference_knowledge = None

    G = nx.karate_club_graph()
    state = TopologyState(complex=G, complex_type="graph", curvature=np.zeros(len(G.nodes)))

    # First call builds cache
    scores1 = runner.run_inference_benchmark(state)
    assert BenchmarkRunner._cached_inference_knowledge is not None

    # Second call uses cache (should be same object)
    cached = BenchmarkRunner._cached_inference_knowledge
    scores2 = runner.run_inference_benchmark(state)
    assert BenchmarkRunner._cached_inference_knowledge is cached  # same object


def test_query_accuracy_with_known_answers():
    dm = DataManager(use_external=False)
    runner = BenchmarkRunner(dm)
    BenchmarkRunner._cached_inference_knowledge = None

    G = nx.Graph()
    state = TopologyState(complex=G, complex_type="graph", curvature=np.array([]))
    scores = runner.run_inference_benchmark(state)
    # With injected test knowledge, direct queries should get high accuracy
    assert scores["query_accuracy"] > 0.5, f"Query accuracy too low: {scores['query_accuracy']}"
