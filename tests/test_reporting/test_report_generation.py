# tests/test_reporting/test_report_generation.py
import tempfile
from pathlib import Path
from tecs.reporting.result_logger import ResultLogger

def test_generate_markdown_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ResultLogger(run_dir=tmpdir)
        data = {
            "run_id": "run_20260319_143022",
            "timestamp": "2026-03-19T14:30:22",
            "termination_reason": "plateau",
            "total_generations": 47,
            "final_phase": 5,
            "best_fitness": 0.7234,
            "population_size": 50,
            "best_components": {
                "representation": "simplicial_complex",
                "reasoning": "homotopy_deformation",
                "emergence": "ising_phase_transition",
                "verification": "persistent_homology_dual",
                "optimization": "min_description_topology",
            },
            "emergence_events": [
                {"generation": 12, "metric": "betti_1", "value": 4.0, "type": "sigma_spike"},
            ],
            "benchmark_scores": {"concept": 0.74, "contradiction": 0.81, "analogy": 0.68, "combined": 0.743},
            "phase_history": [
                {"phase": 1, "generation": 28, "best_fitness": 0.52},
                {"phase": 2, "generation": 40, "best_fitness": 0.68},
            ],
            "fitness_history": [0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
        }
        report = logger.generate_markdown_report(data)
        assert "TECS Run Report" in report
        assert "simplicial_complex" in report
        assert "betti_1" in report
        assert "0.7234" in report

def test_save_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ResultLogger(run_dir=tmpdir)
        data = {
            "run_id": "test", "timestamp": "now", "termination_reason": "test",
            "total_generations": 1, "final_phase": 1, "best_fitness": 0.5,
            "population_size": 3, "best_components": {}, "emergence_events": [],
            "benchmark_scores": {}, "phase_history": [], "fitness_history": [0.5],
        }
        logger.save_report(data)
        assert (Path(tmpdir) / "REPORT.md").exists()
        content = (Path(tmpdir) / "REPORT.md").read_text()
        assert "TECS Run Report" in content
