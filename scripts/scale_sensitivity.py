#!/usr/bin/env python3
"""Scale sensitivity diagnostic for Phase 1 champion architecture.

Tests the champion at multiple node scales (100, 300, 600, 1000) with 10
repetitions each to determine whether the Phase 1->2 fitness drop
(0.659->0.560, -15%) is overfitting or intrinsic scale sensitivity.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from tecs.types import Candidate
from tecs.components.registry import ComponentRegistry
from tecs.engine.topology_simulator import TopologySimulator
from tecs.engine.fitness_evaluator import FitnessEvaluator
from tecs.engine.benchmark_runner import BenchmarkRunner
from tecs.data.data_manager import DataManager

# Phase 1 champion architecture
CHAMPION = {
    "representation": "riemannian_manifold",
    "reasoning": "geodesic_bifurcation",
    "emergence": "lyapunov_bifurcation",
    "verification": "stress_tensor_zero",
    "optimization": "free_energy_annealing",
}

SCALES = [100, 300, 600, 1000]
REPS = 10


def build_registry() -> ComponentRegistry:
    """Build component registry with all 15 components."""
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

    reg = ComponentRegistry()
    for cls in [
        SimplicialComplexComponent, RiemannianManifoldComponent, DynamicHypergraphComponent,
        RicciFlowComponent, HomotopyDeformationComponent, GeodesicBifurcationComponent,
        KuramotoOscillatorComponent, IsingPhaseTransitionComponent, LyapunovBifurcationComponent,
        PersistentHomologyDualComponent, ShadowManifoldAuditComponent, StressTensorZeroComponent,
        MinDescriptionTopologyComponent, FisherDistillationComponent, FreeEnergyAnnealingComponent,
    ]:
        reg.register(cls())
    return reg


def main():
    print("=" * 64)
    print("  Scale Sensitivity Diagnostic — Phase 1 Champion")
    print("=" * 64)
    print(f"  Components: {CHAMPION}")
    print(f"  Scales: {SCALES}  |  Repetitions: {REPS}")
    print()

    registry = build_registry()
    simulator = TopologySimulator(registry)
    evaluator = FitnessEvaluator()
    dm = DataManager(cache_dir=".cache/data", use_external=False)
    benchmark = BenchmarkRunner(dm)

    # Compute total cost once (same for all runs)
    total_cost = sum(
        registry.get(layer, CHAMPION[layer]).cost()
        for layer in CHAMPION
    )
    norm_cost = total_cost / 5.0

    results: dict[int, list[float]] = {}

    for n_nodes in SCALES:
        fitnesses: list[float] = []
        t0 = time.time()

        for seed in range(REPS):
            candidate = Candidate(
                id=f"champion_n{n_nodes}_s{seed}",
                components=dict(CHAMPION),
                parent_ids=[],
                generation=0,
                phase=1,
            )
            points = np.random.default_rng(seed).uniform(-1, 1, (n_nodes, 3))

            # Clear simulator cache between runs to avoid stale state
            simulator.clear_cache()

            try:
                state = simulator.simulate(candidate, points)
                benchmark_scores = benchmark.run_all(state)
                emergence_metrics = {k: v for k, v in state.metrics.items()}
                fitness = evaluator.compute(emergence_metrics, benchmark_scores, norm_cost)
            except Exception as exc:
                print(f"    [WARN] N={n_nodes} seed={seed} failed: {exc}")
                fitness = 0.0

            fitnesses.append(fitness)
            sys.stdout.write(f"\r  N={n_nodes:>5d} | seed {seed + 1:>2d}/{REPS} | fitness={fitness:.4f}")
            sys.stdout.flush()

        elapsed = time.time() - t0
        results[n_nodes] = fitnesses
        arr = np.array(fitnesses)
        sys.stdout.write(
            f"\r  N={n_nodes:>5d} | mean={arr.mean():.4f}  std={arr.std():.4f}  "
            f"min={arr.min():.4f}  max={arr.max():.4f}  ({elapsed:.1f}s)\n"
        )
        sys.stdout.flush()

    # Summary table
    print()
    print("-" * 64)
    print(f"  {'N':>6s} | {'mean':>8s} | {'std':>8s} | {'min':>8s} | {'max':>8s}")
    print("-" * 64)
    for n_nodes in SCALES:
        arr = np.array(results[n_nodes])
        print(f"  {n_nodes:>6d} | {arr.mean():>8.4f} | {arr.std():>8.4f} | {arr.min():>8.4f} | {arr.max():>8.4f}")
    print("-" * 64)

    # Diagnosis
    means = [np.mean(results[n]) for n in SCALES]
    if len(means) >= 2:
        drop = means[0] - means[-1]
        pct = (drop / means[0]) * 100 if means[0] > 0 else 0
        print()
        if abs(pct) > 10:
            print(f"  DIAGNOSIS: Fitness drops {pct:.1f}% from N={SCALES[0]} to N={SCALES[-1]}.")
            print("  -> Likely SCALE SENSITIVITY (not just overfitting).")
        else:
            print(f"  DIAGNOSIS: Fitness change is {pct:.1f}% from N={SCALES[0]} to N={SCALES[-1]}.")
            print("  -> Architecture appears SCALE-ROBUST; Phase 1->2 drop is likely overfitting.")

    # Save results
    out_dir = Path("results")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "scale_sensitivity.json"

    payload = {
        "champion": CHAMPION,
        "scales": SCALES,
        "reps": REPS,
        "results": {str(k): v for k, v in results.items()},
        "summary": {
            str(n): {
                "mean": float(np.mean(results[n])),
                "std": float(np.std(results[n])),
                "min": float(np.min(results[n])),
                "max": float(np.max(results[n])),
            }
            for n in SCALES
        },
    }
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    main()
