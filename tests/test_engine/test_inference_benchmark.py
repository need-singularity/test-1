# tests/test_engine/test_inference_benchmark.py
import numpy as np
import networkx as nx
from tecs.types import TopologyState
from tecs.data.data_manager import DataManager
from tecs.engine.benchmark_runner import BenchmarkRunner

def test_inference_benchmark_returns_scores():
    dm = DataManager(use_external=False)
    runner = BenchmarkRunner(dm)
    BenchmarkRunner._inference_cache = None  # reset cache
    G = nx.karate_club_graph()
    state = TopologyState(complex=G, complex_type="graph", curvature=np.zeros(len(G.nodes)))
    scores = runner.run_inference_benchmark(state)
    assert "query_accuracy" in scores
    assert "analogy_score" in scores
    assert "multihop_accuracy" in scores
    assert "verification_rate" in scores
    assert "inference_combined" in scores
    assert 0.0 <= scores["inference_combined"] <= 1.0

def test_inference_cache_works():
    dm = DataManager(use_external=False)
    runner = BenchmarkRunner(dm)
    BenchmarkRunner._inference_cache = None
    G = nx.karate_club_graph()
    state = TopologyState(complex=G, complex_type="graph", curvature=np.zeros(len(G.nodes)))
    scores1 = runner.run_inference_benchmark(state)
    assert BenchmarkRunner._inference_cache is not None
    # Second call should use cache (same scores)
    scores2 = runner.run_inference_benchmark(state)
    assert scores1["query_accuracy"] == scores2["query_accuracy"]

def test_eval_set_completeness():
    from tecs.inference.eval_set import EVAL_QUERIES, EVAL_ANALOGIES, EVAL_KNOWLEDGE
    assert len(EVAL_QUERIES) >= 15
    assert len(EVAL_ANALOGIES) >= 5
    assert len(EVAL_KNOWLEDGE) >= 30
