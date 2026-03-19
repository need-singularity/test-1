# tecs/orchestrator.py
"""Central Orchestrator controlling the full autonomous TECS loop."""
from __future__ import annotations

import json
import os
import random
from concurrent.futures import ThreadPoolExecutor
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
        """Run one generation: evaluate all candidates in parallel, evolve."""
        # Parallel evaluation using threads (safe with unpicklable objects;
        # NumPy/SciPy release the GIL for C-level computation)
        n_workers = min(os.cpu_count() or 1, len(self.population))
        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            futures = {executor.submit(self._simulate_candidate, c): c for c in self.population}
            for future in futures:
                future.result()  # wait; fitness is set in-place on each candidate

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

        # Checkpoint for crash recovery
        self._save_checkpoint()

    def _save_checkpoint(self):
        """Save full state for crash recovery. Called every generation."""
        import base64, pickle
        self._logger.save_checkpoint({
            "phase": self.current_phase,
            "generation": self.generation,
            "population": [
                {"id": c.id, "components": c.components, "parent_ids": c.parent_ids,
                 "generation": c.generation, "phase": c.phase, "fitness": c.fitness,
                 "mutation_layer": c.mutation_layer, "metrics": c.metrics}
                for c in self.population
            ],
            "best_fitness": self._best_fitness,
            "fitness_history": self._fitness_history,
            "causal_history": self._causal_history,
            "loop_count": self._loop_count,
            "prev_loop_best": self._prev_loop_best,
            "rng_state": base64.b64encode(pickle.dumps(self._rng.getstate())).decode(),
        })

    @classmethod
    def from_checkpoint(cls, run_dir: str, config: TECSConfig) -> Orchestrator:
        """Restore Orchestrator from a checkpoint."""
        import base64, pickle
        cp_path = Path(run_dir) / "checkpoint.json"
        with open(cp_path) as f:
            cp = json.load(f)

        orch = cls.__new__(cls)
        orch._cfg = config
        orch._rng = random.Random()
        orch._rng.setstate(pickle.loads(base64.b64decode(cp["rng_state"])))
        orch._run_dir = Path(run_dir)

        # Rebuild modules
        orch._registry = orch._build_registry()
        orch._simulator = TopologySimulator(orch._registry)
        orch._evaluator = FitnessEvaluator(
            config.fitness.w_emergence, config.fitness.w_benchmark, config.fitness.w_efficiency
        )
        orch._evolution = EvolutionEngine(config.search, config.search.seed)
        orch._emergence = EmergenceDetector(config.emergence)
        orch._causal = CausalTracer(
            config.causal.min_generations_for_significance, config.causal.p_value_threshold
        )
        orch._data_manager = DataManager(config.data.cache_dir, config.data.use_external)
        orch._benchmark = BenchmarkRunner(orch._data_manager)
        orch._scale = ScaleController(config.scaling)
        orch._logger = ResultLogger(str(orch._run_dir))
        orch._reporter = ClaudeReporter(config.reporting.claude_cli)

        # Restore state
        orch.current_phase = cp["phase"]
        orch.generation = cp["generation"]
        orch._best_fitness = cp["best_fitness"]
        orch._fitness_history = cp.get("fitness_history", [])
        orch._causal_history = cp.get("causal_history", [])
        orch._loop_count = cp.get("loop_count", 0)
        orch._prev_loop_best = cp.get("prev_loop_best", 0.0)
        orch._start_time = datetime.now()
        orch._current_metrics = {}

        # Restore population
        orch.population = []
        for cd in cp["population"]:
            orch.population.append(Candidate(
                id=cd["id"], components=cd["components"], parent_ids=cd["parent_ids"],
                generation=cd["generation"], phase=cd["phase"], fitness=cd["fitness"],
                mutation_layer=cd.get("mutation_layer"), metrics=cd.get("metrics", {}),
            ))

        return orch

    def _on_emergence_spike(self, event: dict, candidate: Candidate):
        """Handle emergence spike event."""
        event["candidate_id"] = candidate.id
        event["candidate_components"] = candidate.components
        self._logger.log_emergence_event(event)

        # Update hall of fame
        hof_dir = self._run_dir.parent.parent / "hall_of_fame"
        hof_dir.mkdir(parents=True, exist_ok=True)
        hof_file = hof_dir / "best_candidates.jsonl"
        with open(hof_file, "a") as f:
            f.write(json.dumps({
                "id": candidate.id, "components": candidate.components,
                "fitness": candidate.fitness, "event": event,
                "timestamp": datetime.now().isoformat(),
            }, default=str) + "\n")

        # Generate emergence report
        if self._cfg.reporting.report_on_emergence:
            report = self._reporter.generate_report(event,
                prompt_prefix="이 창발 급등 이벤트를 분석해:")
            if report:
                (self._run_dir / f"emergence_event_{event['generation']}.md").write_text(report)

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
