# tests/test_orchestrator.py
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from tecs.orchestrator import Orchestrator
from tecs.config import load_config
from tecs.types import Candidate


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


def test_phase_1_to_2_transition():
    cfg = load_config("config.yaml", overrides={"scaling.phase1_max_gen": 1, "search.population_size": 3})
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch.run_phase(1)
        assert orch.decide_next_phase() == 2


def test_phase_4_to_2_loop():
    cfg = load_config("config.yaml")
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch.current_phase = 4
        orch._loop_count = 0
        orch._prev_loop_best = 0.5
        orch._best_fitness = 0.55  # improvement > 0.01
        assert orch.decide_next_phase() == 2


def test_phase_4_to_5_max_loops():
    cfg = load_config("config.yaml", overrides={"termination.max_loops": 3})
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch.current_phase = 4
        orch._loop_count = 3
        assert orch.decide_next_phase() == 5


def test_phase_4_to_5_no_improvement():
    cfg = load_config("config.yaml")
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch.current_phase = 4
        orch._loop_count = 0
        orch._prev_loop_best = 0.5
        orch._best_fitness = 0.505
        assert orch.decide_next_phase() == 5


def test_termination_plateau():
    cfg = load_config("config.yaml", overrides={"termination.plateau_generations": 2})
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch._fitness_history = [0.5, 0.5, 0.5]
        assert orch.should_terminate() == "plateau"


def test_no_termination_improving():
    cfg = load_config("config.yaml")
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch._fitness_history = [0.3, 0.4, 0.5, 0.6]
        assert orch.should_terminate() is None


def test_full_run_tiny():
    """Tiny run: 3 candidates, 1 gen per phase, terminates quickly."""
    cfg = load_config("config.yaml", overrides={
        "search.population_size": 3, "scaling.phase1_nodes": 10,
        "scaling.phase2_nodes": 10, "scaling.phase5_nodes": 10,
        "scaling.phase1_max_gen": 1, "scaling.phase2_max_gen": 1,
        "termination.max_loops": 1, "termination.max_hours": 0.001,
        "reporting.claude_cli": False,
    })
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch.run()
        assert orch.generation >= 1
        assert (orch._run_dir / "evolution.jsonl").exists()
        assert (orch._run_dir / "phase_log.jsonl").exists()


def test_checkpoint_saves_state():
    cfg = load_config("config.yaml", overrides={"search.population_size": 3, "search.seed": 42})
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch._init_population()
        orch._save_checkpoint()
        cp_path = orch._run_dir / "checkpoint.json"
        assert cp_path.exists()
        cp = json.loads(cp_path.read_text())
        assert cp["phase"] == orch.current_phase
        assert cp["generation"] == orch.generation
        assert len(cp["population"]) == 3
        assert "rng_state" in cp


def test_resume_from_checkpoint():
    cfg = load_config("config.yaml", overrides={"search.population_size": 3, "search.seed": 42})
    with tempfile.TemporaryDirectory() as tmpdir:
        orch1 = Orchestrator(cfg, results_dir=tmpdir)
        orch1._init_population()
        orch1.generation = 5
        orch1._best_fitness = 0.7
        orch1._save_checkpoint()

        orch2 = Orchestrator.from_checkpoint(str(orch1._run_dir), cfg)
        assert orch2.generation == 5
        assert orch2._best_fitness == 0.7
        assert len(orch2.population) == 3


def test_rng_state_restored():
    cfg = load_config("config.yaml", overrides={"search.population_size": 3, "search.seed": 42})
    with tempfile.TemporaryDirectory() as tmpdir:
        orch1 = Orchestrator(cfg, results_dir=tmpdir)
        orch1._init_population()
        orch1._save_checkpoint()

        orch2 = Orchestrator.from_checkpoint(str(orch1._run_dir), cfg)
        r1 = orch1._rng.random()
        r2 = orch2._rng.random()
        assert r1 == r2


def test_emergence_spike_creates_hall_of_fame():
    cfg = load_config("config.yaml", overrides={"reporting.claude_cli": False, "search.population_size": 3})
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        candidate = Candidate(id="test", components={"representation": "a", "reasoning": "b",
            "emergence": "c", "verification": "d", "optimization": "e"},
            parent_ids=[], generation=0, phase=1, fitness=0.9)
        event = {"generation": 12, "metric": "betti_1", "delta": 3.0}
        orch._on_emergence_spike(event, candidate)

        hof = Path(tmpdir) / "hall_of_fame" / "best_candidates.jsonl"
        assert hof.exists()
        data = json.loads(hof.read_text().strip())
        assert data["id"] == "test"
