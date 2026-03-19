# tests/test_engine/test_verification_pipeline.py
import numpy as np
from tecs.types import TopologyState, Candidate
from tecs.engine.verification_pipeline import VerificationPipeline


def _make_candidate(fitness=0.5, metrics=None):
    c = Candidate.random(generation=0, phase=1)
    c.fitness = fitness
    c.metrics = metrics or {}
    return c


def test_formal_pass():
    vp = VerificationPipeline()
    c = _make_candidate(fitness=0.7, metrics={"query_accuracy": 0.6})
    state = TopologyState.empty("graph")
    result = vp._stage_a_formal(c, state)
    assert result["passed"] is True


def test_formal_fail_nan():
    vp = VerificationPipeline()
    c = _make_candidate(fitness=0.5, metrics={"test": float("nan")})
    state = TopologyState.empty("graph")
    result = vp._stage_a_formal(c, state)
    assert result["score"] < 1.0


def test_formal_fail_perfect():
    vp = VerificationPipeline()
    c = _make_candidate(fitness=1.0)
    state = TopologyState.empty("graph")
    result = vp._stage_a_formal(c, state)
    assert "suspiciously perfect" in str(result["issues"])


def test_predictive_zero():
    vp = VerificationPipeline()
    c = _make_candidate(metrics={"concept": 0, "contradiction": 0, "analogy_score": 0, "query_accuracy": 0})
    state = TopologyState.empty("graph")
    result = vp._stage_d_predictive(c, state)
    assert result["score"] == 0.0
    assert not result["passed"]


def test_full_verify():
    vp = VerificationPipeline(failure_threshold=0.5)
    c = _make_candidate(fitness=0.6, metrics={"query_accuracy": 0.5, "concept": 0.3})
    state = TopologyState.empty("graph")
    result = vp.verify(c, state)
    assert "scores" in result
    assert "eliminated" in result
    assert isinstance(result["verification_score"], float)


def test_elimination():
    vp = VerificationPipeline(failure_threshold=0.0)  # any failure = eliminate
    c = _make_candidate(fitness=1.0, metrics={"test": float("nan")})
    state = TopologyState.empty("graph")
    result = vp.verify(c, state)
    assert result["eliminated"] is True


def test_no_simulator_stages_skip():
    """Stages B and C should pass (skipped) when simulator/data_manager are None."""
    vp = VerificationPipeline()
    c = _make_candidate(fitness=0.5, metrics={"query_accuracy": 0.4})
    state = TopologyState.empty("graph")
    b = vp._stage_b_counterexample(c, state, simulator=None, data_manager=None)
    assert b["passed"] is True
    assert "skipped" in b["issues"][0]

    r = vp._stage_c_reproducibility(c, simulator=None, data_manager=None)
    assert r["passed"] is True
    assert "skipped" in r["issues"][0]


def test_verify_returns_all_keys():
    vp = VerificationPipeline()
    c = _make_candidate(fitness=0.5)
    state = TopologyState.empty("graph")
    result = vp.verify(c, state)
    for key in ("scores", "details", "failure_count", "failure_rate", "eliminated", "verification_score"):
        assert key in result


def test_failure_rate_range():
    vp = VerificationPipeline()
    c = _make_candidate(fitness=0.5)
    state = TopologyState.empty("graph")
    result = vp.verify(c, state)
    assert 0.0 <= result["failure_rate"] <= 1.0


def test_contradictory_metrics_penalised():
    vp = VerificationPipeline()
    c = _make_candidate(fitness=0.5, metrics={"hallucination_score": 0.9, "query_accuracy": 0.9})
    state = TopologyState.empty("graph")
    result = vp._stage_a_formal(c, state)
    # Should have a penalty for contradictory metrics
    assert result["score"] < 1.0
    assert any("hallucination" in issue for issue in result["issues"])
