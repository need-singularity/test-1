# tests/test_orchestrator.py
import tempfile
from unittest.mock import patch
from tecs.orchestrator import Orchestrator
from tecs.config import load_config


def test_init_creates_run_dir():
    cfg = load_config("config.yaml", overrides={"search.population_size": 3})
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        assert orch._run_dir.exists()


def test_init_population():
    cfg = load_config("config.yaml", overrides={"search.population_size": 5})
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch._init_population()
        assert len(orch.population) == 5


def test_run_generation():
    cfg = load_config("config.yaml", overrides={"search.population_size": 3, "scaling.phase1_nodes": 10})
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch._init_population()
        orch._run_generation()
        assert orch.generation == 1
        assert len(orch._fitness_history) == 1


def test_run_phase():
    cfg = load_config("config.yaml", overrides={
        "search.population_size": 3, "scaling.phase1_nodes": 10, "scaling.phase1_max_gen": 2
    })
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch.run_phase(1)
        assert orch.current_phase == 1
        assert orch.generation >= 1
        assert len(orch.population) > 0


def test_logger_property():
    cfg = load_config("config.yaml", overrides={"search.population_size": 3})
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        assert orch.logger is orch._logger


def test_simulate_candidate_handles_errors():
    """Incompatible candidates get fitness 0.0 instead of crashing."""
    cfg = load_config("config.yaml", overrides={"search.population_size": 3, "scaling.phase1_nodes": 10})
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch._init_population()
        candidate = orch.population[0]
        # Should not raise even if simulation fails
        fitness = orch._simulate_candidate(candidate)
        assert isinstance(fitness, float)
        assert fitness >= 0.0


def test_best_fitness_tracked():
    cfg = load_config("config.yaml", overrides={
        "search.population_size": 3, "scaling.phase1_nodes": 10, "scaling.phase1_max_gen": 2
    })
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch.run_phase(1)
        assert orch._best_fitness >= 0.0
        assert len(orch._fitness_history) >= 1
