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

    @property
    def logger(self):
        return self._logger
