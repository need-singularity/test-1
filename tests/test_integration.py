# tests/test_integration.py
import sys
import tempfile
from pathlib import Path
from tecs.config import load_config
from tecs.orchestrator import Orchestrator


def test_full_run_tiny():
    """Tiny end-to-end: 3 candidates, 1 gen/phase, fast termination."""
    cfg = load_config("config.yaml", overrides={
        "search.population_size": 3,
        "scaling.phase1_max_gen": 1,
        "scaling.phase2_max_gen": 1,
        "scaling.phase1_nodes": 10,
        "scaling.phase2_nodes": 10,
        "scaling.phase5_nodes": 10,
        "termination.max_hours": 0.001,
        "termination.max_loops": 1,
        "reporting.claude_cli": False,
    })
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch.run()
        run_dirs = list(Path(tmpdir).glob("runs/run_*"))
        assert len(run_dirs) == 1
        run_dir = run_dirs[0]
        assert (run_dir / "evolution.jsonl").exists()
        assert (run_dir / "phase_log.jsonl").exists()
        assert (run_dir / "checkpoint.json").exists()


def test_checkpoint_resume_continues():
    """Run, checkpoint, resume, verify generation incremented."""
    cfg = load_config("config.yaml", overrides={
        "search.population_size": 3,
        "scaling.phase1_max_gen": 2,
        "scaling.phase1_nodes": 10,
        "termination.max_hours": 0.001,
        "reporting.claude_cli": False,
    })
    with tempfile.TemporaryDirectory() as tmpdir:
        orch1 = Orchestrator(cfg, results_dir=tmpdir)
        orch1.run_phase(1)
        gen_after_phase1 = orch1.generation
        orch1._save_checkpoint()

        orch2 = Orchestrator.from_checkpoint(str(orch1._run_dir), cfg)
        assert orch2.generation == gen_after_phase1
        assert len(orch2.population) == 3


def test_run_py_cli():
    """Test that run.py can be invoked."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "run.py", "--help"],
        capture_output=True, text=True, cwd="/Users/ghost/Dev/test-1"
    )
    assert result.returncode == 0
    assert "TECS" in result.stdout
