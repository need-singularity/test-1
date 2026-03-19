import json
import tempfile
from pathlib import Path
from tecs.reporting.result_logger import ResultLogger


def test_log_generation():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ResultLogger(run_dir=tmpdir)
        logger.log_generation({"generation": 1, "best_fitness": 0.5, "betti_0": 3})
        evo_file = Path(tmpdir) / "evolution.jsonl"
        assert evo_file.exists()
        lines = evo_file.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["generation"] == 1


def test_log_emergence_event():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ResultLogger(run_dir=tmpdir)
        logger.log_emergence_event({"generation": 12, "metric": "betti_1", "delta": 3})
        assert (Path(tmpdir) / "emergence_events.jsonl").exists()


def test_log_phase():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ResultLogger(run_dir=tmpdir)
        logger.log_phase({"phase": 1, "action": "transition", "top_candidates": 5})
        assert (Path(tmpdir) / "phase_log.jsonl").exists()


def test_save_checkpoint():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ResultLogger(run_dir=tmpdir)
        logger.save_checkpoint({"phase": 2, "generation": 34})
        cp = Path(tmpdir) / "checkpoint.json"
        assert cp.exists()
        data = json.loads(cp.read_text())
        assert data["phase"] == 2
