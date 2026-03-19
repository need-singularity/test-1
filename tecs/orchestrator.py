# tecs/orchestrator.py
"""Central Orchestrator controlling the full autonomous TECS loop."""
from __future__ import annotations

import random
from datetime import datetime
from pathlib import Path

from tecs.config import TECSConfig
from tecs.types import Candidate
from tecs.components.registry import ComponentRegistry
from tecs.engine.topology_simulator import TopologySimulator
from tecs.engine.fitness_evaluator import FitnessEvaluator
from tecs.engine.evolution_engine import EvolutionEngine
from tecs.engine.benchmark_runner import BenchmarkRunner
from tecs.engine.scale_controller import ScaleController
from tecs.analysis.emergence_detector import EmergenceDetector
from tecs.analysis.causal_tracer import CausalTracer
from tecs.data.data_manager import DataManager
from tecs.reporting.result_logger import ResultLogger
from tecs.reporting.claude_reporter import ClaudeReporter


class Orchestrator:
    def __init__(self, config: TECSConfig, results_dir: str = "results"):
        self._cfg = config
        self._rng = random.Random(config.search.seed)

        # Create run directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._run_dir = Path(results_dir) / "runs" / f"run_{timestamp}"

        # Initialize modules
        self._registry = self._build_registry()
        self._simulator = TopologySimulator(self._registry)
        self._evaluator = FitnessEvaluator(
            config.fitness.w_emergence,
            config.fitness.w_benchmark,
            config.fitness.w_efficiency,
        )
        self._evolution = EvolutionEngine(config.search, config.search.seed)
        self._emergence = EmergenceDetector(config.emergence)
        self._causal = CausalTracer(
            config.causal.min_generations_for_significance,
            config.causal.p_value_threshold,
        )
        self._data_manager = DataManager(config.data.cache_dir, False)
        self._benchmark = BenchmarkRunner(self._data_manager)
        self._scale = ScaleController(config.scaling)
        self._logger = ResultLogger(str(self._run_dir))
        self._reporter = ClaudeReporter(config.reporting.claude_cli)

        # State
        self.population: list[Candidate] = []
        self.current_phase: int = 1
        self.generation: int = 0
        self._fitness_history: list[float] = []
        self._causal_history: list[dict] = []
        self._best_fitness: float = 0.0
        self._start_time: datetime = datetime.now()
        self._loop_count: int = 0
        self._prev_loop_best: float = 0.0
        self._current_metrics: dict = {}

    def _build_registry(self) -> ComponentRegistry:
        """Register all 15 components."""
        reg = ComponentRegistry()
        from tecs.components.representation.simplicial_complex import SimplicialComplexComponent
        from tecs.components.representation.riemannian_manifold import RiemannianManifoldComponent
        from tecs.components.representation.dynamic_hypergraph import DynamicHypergraphComponent
        from tecs.components.reasoning.ricci_flow import RicciFlowComponent
        from tecs.components.reasoning.homotopy_deformation import HomotopyDeformationComponent
        from tecs.components.reasoning.geodesic_bifurcation import GeodesicBifurcationComponent
        from tecs.components.emergence.kuramoto_oscillator import KuramotoOscillatorComponent
        from tecs.components.emergence.ising_phase_transition import IsingPhaseTransitionComponent
        from tecs.components.emergence.lyapunov_bifurcation import LyapunovBifurcationComponent
        from tecs.components.verification.persistent_homology_dual import PersistentHomologyDualComponent
        from tecs.components.verification.shadow_manifold_audit import ShadowManifoldAuditComponent
        from tecs.components.verification.stress_tensor_zero import StressTensorZeroComponent
        from tecs.components.optimization.min_description_topology import MinDescriptionTopologyComponent
        from tecs.components.optimization.fisher_distillation import FisherDistillationComponent
        from tecs.components.optimization.free_energy_annealing import FreeEnergyAnnealingComponent

        for cls in [
            SimplicialComplexComponent, RiemannianManifoldComponent, DynamicHypergraphComponent,
            RicciFlowComponent, HomotopyDeformationComponent, GeodesicBifurcationComponent,
            KuramotoOscillatorComponent, IsingPhaseTransitionComponent, LyapunovBifurcationComponent,
            PersistentHomologyDualComponent, ShadowManifoldAuditComponent, StressTensorZeroComponent,
            MinDescriptionTopologyComponent, FisherDistillationComponent, FreeEnergyAnnealingComponent,
        ]:
            reg.register(cls())
        return reg

    def _init_population(self):
        """Generate initial random population."""
        self.population = self._evolution._generator.random_population(
            n=self._cfg.search.population_size,
            generation=0,
            phase=self.current_phase,
        )

    def _simulate_candidate(self, candidate: Candidate) -> float:
        """Run 5-layer pipeline for one candidate. Returns fitness.

        Handles incompatible combos gracefully by returning 0.0.
        """
        try:
            points = self._data_manager.get_points(
                n=self._scale.current_nodes, dim=3
            )
            state = self._simulator.simulate(candidate, points)
            benchmark_scores = self._benchmark.run_all(state)
            emergence_metrics = {k: v for k, v in state.metrics.items()}
            total_cost = sum(
                self._registry.get(layer, candidate.components[layer]).cost()
                for layer in candidate.components
            )
            fitness = self._evaluator.compute(
                emergence_metrics, benchmark_scores, total_cost / 5.0
            )
            candidate.fitness = fitness
            candidate.metrics = {**emergence_metrics, **benchmark_scores}
            return fitness
        except Exception:
            candidate.fitness = 0.0
            return 0.0

    def _run_generation(self):
        """Run one generation: evaluate all candidates, evolve."""
        # Evaluate
        for candidate in self.population:
            self._simulate_candidate(candidate)

        # Track best
        best = max(self.population, key=lambda c: c.fitness)
        self._best_fitness = best.fitness
        self._fitness_history.append(best.fitness)

        # Log
        self._logger.log_generation({
            "generation": self.generation,
            "phase": self.current_phase,
            "best_fitness": best.fitness,
            "mean_fitness": sum(c.fitness for c in self.population) / len(self.population),
            "best_components": best.components,
            "best_metrics": best.metrics,
        })

        # Check emergence
        if best.metrics:
            event = self._emergence.check(self.generation, best.metrics)
            if event:
                self._on_emergence_spike(event, best)

        # Track causal history
        self._causal_history.append({
            "generation": self.generation,
            "components": best.components,
            "metrics": best.metrics,
            "mutation_layer": best.mutation_layer,
        })

        # Evolve
        causal_info = (
            self._causal.analyze(self._causal_history)
            if len(self._causal_history) > 5
            else None
        )
        self.population = self._evolution.next_generation(self.population, causal_info)
        self.generation += 1

    def _on_emergence_spike(self, event: dict, candidate: Candidate):
        """Handle emergence spike event."""
        event["candidate_id"] = candidate.id
        event["candidate_components"] = candidate.components
        self._logger.log_emergence_event(event)

    def run_phase(self, phase: int):
        """Run all generations for a given phase."""
        self.current_phase = phase
        self._scale.on_phase_change(phase)
        max_gen = self._scale.max_generations(phase)

        if not self.population:
            self._init_population()

        for _ in range(max_gen):
            self._run_generation()
            # Check plateau convergence
            if len(self._fitness_history) >= self._cfg.termination.plateau_generations:
                recent = self._fitness_history[-self._cfg.termination.plateau_generations:]
                if max(recent) - min(recent) < self._cfg.termination.plateau_epsilon:
                    break

    def decide_next_phase(self) -> int:
        """Determine the next phase based on current state."""
        if self.current_phase == 1:
            return 2
        elif self.current_phase == 2:
            return 3
        elif self.current_phase == 3:
            return 4
        elif self.current_phase == 4:
            # Loop back to 2 if improvement > threshold, else go to 5
            if self._loop_count >= self._cfg.termination.max_loops:
                return 5
            if hasattr(self, '_prev_loop_best'):
                improvement = self._best_fitness - self._prev_loop_best
                if improvement <= self._cfg.termination.plateau_epsilon:
                    return 5
            self._loop_count += 1
            self._prev_loop_best = self._best_fitness
            return 2
        elif self.current_phase == 5:
            return -1  # done
        return -1

    def should_terminate(self) -> str | None:
        """Check all 4 termination conditions. Returns reason string or None."""
        # 1. Success
        metrics = getattr(self, '_current_metrics', {})
        if (metrics.get("hallucination_rate", 1.0) < self._cfg.termination.target_hallucination and
            metrics.get("emergence_rate", 0.0) > self._cfg.termination.target_emergence and
            metrics.get("benchmark_avg", 0.0) > self._cfg.termination.target_benchmark):
            return "success"

        # 2. Plateau
        n = self._cfg.termination.plateau_generations
        if len(self._fitness_history) >= n:
            recent = self._fitness_history[-n:]
            if max(recent) - min(recent) < self._cfg.termination.plateau_epsilon:
                return "plateau"

        # 3. Time limit
        elapsed = (datetime.now() - self._start_time).total_seconds() / 3600
        if elapsed > self._cfg.termination.max_hours:
            return "time_limit"

        # 4. Memory
        if not self._scale.check_memory_ok(self._cfg.termination.max_memory_pct):
            return "memory_limit"

        return None

    def run(self):
        """Full autonomous loop. No human intervention."""
        self._start_time = datetime.now()
        self._loop_count = 0
        self._prev_loop_best = 0.0

        # Phase 1
        self.run_phase(1)
        self._select_top_candidates(5)
        self._on_phase_complete(1)

        while True:
            next_phase = self.decide_next_phase()
            if next_phase == -1:
                break

            term = self.should_terminate()
            if term:
                self._logger.log_phase({"phase": self.current_phase, "terminated": term})
                break

            if next_phase == 3:
                # Benchmark phase - run benchmarks on top candidates
                self.current_phase = 3
                self._run_benchmarks()
                self._on_phase_complete(3)
            else:
                self.run_phase(next_phase)
                if next_phase == 2:
                    self._select_top_candidates(2)
                self._on_phase_complete(next_phase)

        # Final report
        self._on_run_complete()

    def _select_top_candidates(self, n: int):
        """Keep only top n candidates by fitness."""
        self.population.sort(key=lambda c: c.fitness, reverse=True)
        self.population = self.population[:n]

    def _run_benchmarks(self):
        """Run full benchmarks on current population."""
        for candidate in self.population:
            try:
                points = DataManager(self._cfg.data.cache_dir, False).get_points(
                    n=self._scale.current_nodes, dim=3)
                state = self._simulator.simulate(candidate, points)
                scores = self._benchmark.run_all(state)
                candidate.metrics.update(scores)
                self._logger.log_benchmark({
                    "candidate_id": candidate.id, "components": candidate.components, **scores
                })
            except Exception:
                pass

    def _on_phase_complete(self, phase: int):
        """Log phase completion and generate report."""
        self._logger.log_phase({
            "phase": phase, "generation": self.generation,
            "best_fitness": self._best_fitness,
            "population_size": len(self.population),
        })
        if self._cfg.reporting.report_on_phase:
            report = self._reporter.generate_report({
                "phase": phase, "best_fitness": self._best_fitness,
                "generation": self.generation,
            })
            if report:
                report_path = self._run_dir / f"phase{phase}_report.md"
                report_path.write_text(report)

    def _on_run_complete(self):
        """Final report generation."""
        report = self._reporter.generate_report({
            "total_generations": self.generation,
            "best_fitness": self._best_fitness,
            "phases_completed": self.current_phase,
        }, prompt_prefix="전체 실행 결과를 종합 분석해서 한국어 리포트를 작성해:")
        if report:
            (self._run_dir / "REPORT.md").write_text(report)

    @property
    def logger(self):
        return self._logger
