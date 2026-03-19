# TECS Meta-Research Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Post-LLM 아키텍처를 자율적으로 탐색, 검증, 변형, 확장하는 연구 가속 엔진 구현

**Architecture:** 10개 모듈(메인 파이프라인 6 + 횡단 2 + 인프라 2)이 Orchestrator의 제어 하에 5-Phase 순환 루프를 자율 실행. 15개 수학적 구성요소(5계층×3)를 진화 알고리즘 + 인과 분석으로 조합 탐색.

**Tech Stack:** Python 3.12+, GUDHI, NetworkX, HyperNetX, SciPy, NumPy, JAX-Metal, PyTorch(MPS), GraphRicciCurvature, NLTK, Jinja2, Claude CLI

**Spec:** `docs/superpowers/specs/2026-03-19-tecs-meta-research-engine-design.md`

---

## File Map

```
tecs-engine/
├── run.py                                    # CLI 진입점
├── config.yaml                               # 전체 설정
├── requirements.txt                          # 의존성
├── tecs/
│   ├── __init__.py
│   ├── types.py                              # TopologyState, Candidate, ComplexType
│   ├── config.py                             # YAML 설정 로더
│   ├── orchestrator.py                       # Phase 전환, 종료 조건, 전체 루프
│   ├── components/
│   │   ├── __init__.py
│   │   ├── base.py                           # Component, VerificationComponent protocols
│   │   ├── registry.py                       # 구성요소 등록/조회
│   │   ├── representation/
│   │   │   ├── __init__.py
│   │   │   ├── simplicial_complex.py
│   │   │   ├── riemannian_manifold.py
│   │   │   └── dynamic_hypergraph.py
│   │   ├── reasoning/
│   │   │   ├── __init__.py
│   │   │   ├── ricci_flow.py
│   │   │   ├── homotopy_deformation.py
│   │   │   └── geodesic_bifurcation.py
│   │   ├── emergence/
│   │   │   ├── __init__.py
│   │   │   ├── kuramoto_oscillator.py
│   │   │   ├── ising_phase_transition.py
│   │   │   └── lyapunov_bifurcation.py
│   │   ├── verification/
│   │   │   ├── __init__.py
│   │   │   ├── persistent_homology_dual.py
│   │   │   ├── shadow_manifold_audit.py
│   │   │   └── stress_tensor_zero.py
│   │   └── optimization/
│   │       ├── __init__.py
│   │       ├── min_description_topology.py
│   │       ├── fisher_distillation.py
│   │       └── free_energy_annealing.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── architecture_generator.py
│   │   ├── topology_simulator.py
│   │   ├── fitness_evaluator.py
│   │   ├── evolution_engine.py
│   │   ├── benchmark_runner.py
│   │   └── scale_controller.py
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── emergence_detector.py
│   │   └── causal_tracer.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── data_manager.py
│   │   ├── conceptnet_loader.py
│   │   ├── wordnet_loader.py
│   │   └── synthetic_generator.py
│   └── reporting/
│       ├── __init__.py
│       ├── result_logger.py
│       └── claude_reporter.py
├── tests/
│   ├── __init__.py
│   ├── test_types.py
│   ├── test_config.py
│   ├── test_components/
│   │   ├── __init__.py
│   │   ├── test_registry.py
│   │   ├── test_simplicial_complex.py
│   │   ├── test_riemannian_manifold.py
│   │   ├── test_dynamic_hypergraph.py
│   │   ├── test_ricci_flow.py
│   │   ├── test_homotopy_deformation.py
│   │   ├── test_geodesic_bifurcation.py
│   │   ├── test_kuramoto_oscillator.py
│   │   ├── test_ising_phase_transition.py
│   │   ├── test_lyapunov_bifurcation.py
│   │   ├── test_persistent_homology_dual.py
│   │   ├── test_shadow_manifold_audit.py
│   │   ├── test_stress_tensor_zero.py
│   │   ├── test_min_description_topology.py
│   │   ├── test_fisher_distillation.py
│   │   └── test_free_energy_annealing.py
│   ├── test_engine/
│   │   ├── __init__.py
│   │   ├── test_architecture_generator.py
│   │   ├── test_topology_simulator.py
│   │   ├── test_fitness_evaluator.py
│   │   ├── test_evolution_engine.py
│   │   ├── test_benchmark_runner.py
│   │   └── test_scale_controller.py
│   ├── test_analysis/
│   │   ├── __init__.py
│   │   ├── test_emergence_detector.py
│   │   └── test_causal_tracer.py
│   ├── test_data/
│   │   ├── __init__.py
│   │   └── test_data_manager.py
│   ├── test_reporting/
│   │   ├── __init__.py
│   │   ├── test_result_logger.py
│   │   └── test_claude_reporter.py
│   ├── test_orchestrator.py
│   └── test_integration.py
├── data/                                      # .gitignore (large files)
├── results/                                   # GitHub에 push
│   ├── hall_of_fame/
│   │   └── best_candidates.jsonl
│   └── README.md
└── docs/
```

---

## Task 1: Project Scaffold + Core Types

**Files:**
- Create: `requirements.txt`
- Create: `config.yaml`
- Create: `tecs/__init__.py`
- Create: `tecs/types.py`
- Create: `tecs/config.py`
- Create: `run.py`
- Create: `tests/__init__.py`
- Create: `tests/test_types.py`
- Create: `tests/test_config.py`
- Create: `.gitignore`

- [ ] **Step 1: Write requirements.txt**

```txt
gudhi>=3.9
giotto-tda>=0.6
numpy>=1.26
scipy>=1.12
networkx>=3.2
hypernetx>=2.3
GraphRicciCurvature>=0.5
nltk>=3.8
requests>=2.31
pyyaml>=6.0
jinja2>=3.1
pytest>=8.0
# Apple Silicon acceleration (optional)
# jax[metal]
# torch>=2.2
```

- [ ] **Step 2: Write .gitignore**

```
__pycache__/
*.pyc
.venv/
data/conceptnet/
data/wordnet/
data/benchmarks/
.superpowers/
checkpoint.json
```

- [ ] **Step 3: Write config.yaml**

```yaml
search:
  population_size: 50
  elite_ratio: 0.2
  tournament_size: 3
  mutation_rate: 0.3
  crossover_rate: 0.7
  diversity_threshold: 0.3
  seed: 42

scaling:
  phase1_nodes: 100
  phase2_nodes: 1000
  phase5_nodes: 10000
  phase1_max_gen: 30
  phase2_max_gen: 50

fitness:
  w_emergence: 0.4
  w_benchmark: 0.4
  w_efficiency: 0.2

emergence:
  sigma_threshold: 2.0
  r_threshold: 0.2
  phi_critical: 1.0
  window_size: 10
  min_generations: 3

termination:
  target_hallucination: 0.01
  target_emergence: 0.8
  target_benchmark: 0.7
  plateau_generations: 5
  plateau_epsilon: 0.01
  max_hours: 48
  max_loops: 10
  max_memory_pct: 80

reporting:
  claude_cli: true
  report_on_phase: true
  report_on_emergence: true

causal:
  p_value_threshold: 0.05
  min_generations_for_significance: 20

data:
  cache_dir: data/
  use_external: true
  conceptnet_url: "https://api.conceptnet.io"
  conceptnet_cache: data/conceptnet/
  wordnet_auto_download: true
```

- [ ] **Step 4: Write failing test for TopologyState and Candidate**

```python
# tests/test_types.py
import numpy as np
from tecs.types import TopologyState, Candidate, LAYERS, COMPONENT_POOL

def test_topology_state_creation():
    state = TopologyState.empty("simplicial")
    assert state.complex_type == "simplicial"
    assert state.complex is None
    assert state.metrics == {}
    assert state.history == []

def test_topology_state_rejects_invalid_type():
    import pytest
    with pytest.raises(ValueError):
        TopologyState.empty("invalid_type")

def test_candidate_creation():
    c = Candidate.random(generation=0, phase=1)
    assert len(c.components) == 5
    assert all(layer in c.components for layer in LAYERS)
    assert c.generation == 0
    assert c.parent_ids == []
    assert c.id  # uuid assigned

def test_candidate_hamming_distance():
    c1 = Candidate.random(generation=0, phase=1)
    c2 = Candidate.random(generation=0, phase=1)
    d = c1.hamming_distance(c2)
    assert 0 <= d <= 5

def test_component_pool_completeness():
    assert len(LAYERS) == 5
    for layer in LAYERS:
        assert len(COMPONENT_POOL[layer]) == 3
```

- [ ] **Step 5: Run test to verify it fails**

Run: `cd /Users/ghost/Dev/test-1 && python -m pytest tests/test_types.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tecs'`

- [ ] **Step 6: Implement tecs/types.py**

```python
# tecs/types.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Union
import uuid
import random
import numpy as np

LAYERS = ["representation", "reasoning", "emergence", "verification", "optimization"]

COMPONENT_POOL: dict[str, list[str]] = {
    "representation": ["simplicial_complex", "riemannian_manifold", "dynamic_hypergraph"],
    "reasoning": ["ricci_flow", "homotopy_deformation", "geodesic_bifurcation"],
    "emergence": ["kuramoto_oscillator", "ising_phase_transition", "lyapunov_bifurcation"],
    "verification": ["persistent_homology_dual", "shadow_manifold_audit", "stress_tensor_zero"],
    "optimization": ["min_description_topology", "fisher_distillation", "free_energy_annealing"],
}

VALID_COMPLEX_TYPES = {"simplicial", "graph", "hypergraph"}


@dataclass
class TopologyState:
    complex: Any
    complex_type: str
    curvature: np.ndarray
    metrics: dict[str, float] = field(default_factory=dict)
    history: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def empty(cls, complex_type: str) -> TopologyState:
        if complex_type not in VALID_COMPLEX_TYPES:
            raise ValueError(f"Invalid complex_type: {complex_type}. Must be one of {VALID_COMPLEX_TYPES}")
        return cls(
            complex=None,
            complex_type=complex_type,
            curvature=np.array([]),
            metrics={},
            history=[],
            metadata={},
        )


@dataclass
class Candidate:
    id: str
    components: dict[str, str]
    parent_ids: list[str]
    generation: int
    phase: int
    fitness: float = 0.0
    mutation_layer: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)

    @classmethod
    def random(cls, generation: int, phase: int, rng: random.Random | None = None) -> Candidate:
        r = rng or random.Random()
        components = {layer: r.choice(options) for layer, options in COMPONENT_POOL.items()}
        return cls(
            id=str(uuid.uuid4()),
            components=components,
            parent_ids=[],
            generation=generation,
            phase=phase,
        )

    def hamming_distance(self, other: Candidate) -> int:
        return sum(1 for layer in LAYERS if self.components[layer] != other.components[layer])
```

- [ ] **Step 7: Create tecs/__init__.py**

```python
# tecs/__init__.py
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd /Users/ghost/Dev/test-1 && python -m pytest tests/test_types.py -v`
Expected: All 5 tests PASS

- [ ] **Step 9: Write failing test for config loader**

```python
# tests/test_config.py
from tecs.config import load_config

def test_load_config_defaults():
    cfg = load_config("config.yaml")
    assert cfg.search.population_size == 50
    assert cfg.fitness.w_emergence == 0.4
    assert cfg.termination.max_hours == 48
    assert cfg.emergence.window_size == 10

def test_load_config_override():
    cfg = load_config("config.yaml", overrides={"search.population_size": 100})
    assert cfg.search.population_size == 100
```

- [ ] **Step 10: Implement tecs/config.py**

```python
# tecs/config.py
from __future__ import annotations
from dataclasses import dataclass
import yaml


@dataclass
class SearchConfig:
    population_size: int = 50
    elite_ratio: float = 0.2
    tournament_size: int = 3
    mutation_rate: float = 0.3
    crossover_rate: float = 0.7
    diversity_threshold: float = 0.3
    seed: int = 42

@dataclass
class ScalingConfig:
    phase1_nodes: int = 100
    phase2_nodes: int = 1000
    phase5_nodes: int = 10000
    phase1_max_gen: int = 30
    phase2_max_gen: int = 50

@dataclass
class FitnessConfig:
    w_emergence: float = 0.4
    w_benchmark: float = 0.4
    w_efficiency: float = 0.2

@dataclass
class EmergenceConfig:
    sigma_threshold: float = 2.0
    r_threshold: float = 0.2
    phi_critical: float = 1.0
    window_size: int = 10
    min_generations: int = 3

@dataclass
class TerminationConfig:
    target_hallucination: float = 0.01
    target_emergence: float = 0.8
    target_benchmark: float = 0.7
    plateau_generations: int = 5
    plateau_epsilon: float = 0.01
    max_hours: float = 48
    max_loops: int = 10
    max_memory_pct: int = 80

@dataclass
class ReportingConfig:
    claude_cli: bool = True
    report_on_phase: bool = True
    report_on_emergence: bool = True

@dataclass
class TECSConfig:
    search: SearchConfig = None
    scaling: ScalingConfig = None
    fitness: FitnessConfig = None
    emergence: EmergenceConfig = None
    termination: TerminationConfig = None
    reporting: ReportingConfig = None

    def __post_init__(self):
        self.search = self.search or SearchConfig()
        self.scaling = self.scaling or ScalingConfig()
        self.fitness = self.fitness or FitnessConfig()
        self.emergence = self.emergence or EmergenceConfig()
        self.termination = self.termination or TerminationConfig()
        self.reporting = self.reporting or ReportingConfig()


def load_config(path: str, overrides: dict | None = None) -> TECSConfig:
    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    if overrides:
        for dotted_key, value in overrides.items():
            parts = dotted_key.split(".")
            d = raw
            for part in parts[:-1]:
                d = d.setdefault(part, {})
            d[parts[-1]] = value

    cfg = TECSConfig(
        search=SearchConfig(**raw.get("search", {})),
        scaling=ScalingConfig(**raw.get("scaling", {})),
        fitness=FitnessConfig(**raw.get("fitness", {})),
        emergence=EmergenceConfig(**raw.get("emergence", {})),
        termination=TerminationConfig(**raw.get("termination", {})),
        reporting=ReportingConfig(**raw.get("reporting", {})),
    )
    return cfg
```

- [ ] **Step 11: Run tests**

Run: `cd /Users/ghost/Dev/test-1 && python -m pytest tests/test_types.py tests/test_config.py -v`
Expected: All PASS

- [ ] **Step 12: Write run.py stub**

```python
# run.py
"""TECS Meta-Research Engine — 진입점"""
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="TECS Meta-Research Engine")
    parser.add_argument("--config", default="config.yaml", help="설정 파일 경로")
    parser.add_argument("--resume", default=None, help="체크포인트에서 복구 (run 디렉토리 경로)")
    args = parser.parse_args()

    from tecs.config import load_config
    cfg = load_config(args.config)
    print(f"TECS Engine loaded. Population: {cfg.search.population_size}, Seed: {cfg.search.seed}")
    print("Orchestrator not yet implemented.")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

- [ ] **Step 13: Create directory structure**

```bash
mkdir -p tecs/components/representation tecs/components/reasoning tecs/components/emergence tecs/components/verification tecs/components/optimization tecs/engine tecs/analysis tecs/data tecs/reporting
mkdir -p tests/test_components tests/test_engine tests/test_analysis tests/test_data tests/test_reporting
mkdir -p results/hall_of_fame data
touch tecs/components/__init__.py tecs/components/representation/__init__.py tecs/components/reasoning/__init__.py tecs/components/emergence/__init__.py tecs/components/verification/__init__.py tecs/components/optimization/__init__.py
touch tecs/engine/__init__.py tecs/analysis/__init__.py tecs/data/__init__.py tecs/reporting/__init__.py
touch tests/test_components/__init__.py tests/test_engine/__init__.py tests/test_analysis/__init__.py tests/test_data/__init__.py tests/test_reporting/__init__.py
```

- [ ] **Step 14: Commit**

```bash
git add -A && git commit -m "feat: project scaffold with core types, config, and run.py"
```

---

## Task 2: Component Base + Registry

**Files:**
- Create: `tecs/components/base.py`
- Create: `tecs/components/registry.py`
- Create: `tests/test_components/test_registry.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_components/test_registry.py
from tecs.components.registry import ComponentRegistry
from tecs.components.base import Component
from tecs.types import TopologyState, LAYERS, COMPONENT_POOL
import numpy as np

class FakeComponent:
    name = "fake"
    layer = "representation"
    compatible_types = ["simplicial"]

    def configure(self, params: dict) -> None:
        self.params = params

    def execute(self, state: TopologyState) -> TopologyState:
        return state

    def measure(self, state: TopologyState) -> dict[str, float]:
        return {"test": 1.0}

    def cost(self) -> float:
        return 0.1

def test_register_and_get():
    reg = ComponentRegistry()
    comp = FakeComponent()
    reg.register(comp)
    assert reg.get("representation", "fake") is comp

def test_get_missing_raises():
    import pytest
    reg = ComponentRegistry()
    with pytest.raises(KeyError):
        reg.get("representation", "nonexistent")

def test_check_compatibility_pass():
    reg = ComponentRegistry()
    comp = FakeComponent()
    reg.register(comp)
    state = TopologyState.empty("simplicial")
    assert reg.check_compatible(comp, state) is True

def test_check_compatibility_fail():
    reg = ComponentRegistry()
    comp = FakeComponent()
    reg.register(comp)
    state = TopologyState.empty("graph")
    assert reg.check_compatible(comp, state) is False

def test_list_layers():
    reg = ComponentRegistry()
    reg.register(FakeComponent())
    assert "representation" in reg.list_layers()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ghost/Dev/test-1 && python -m pytest tests/test_components/test_registry.py -v`
Expected: FAIL

- [ ] **Step 3: Implement base.py and registry.py**

```python
# tecs/components/base.py
from __future__ import annotations
from typing import Protocol, runtime_checkable
from tecs.types import TopologyState


@runtime_checkable
class Component(Protocol):
    name: str
    layer: str
    compatible_types: list[str]

    def configure(self, params: dict) -> None: ...
    def execute(self, state: TopologyState) -> TopologyState: ...
    def measure(self, state: TopologyState) -> dict[str, float]: ...
    def cost(self) -> float: ...


@runtime_checkable
class VerificationComponent(Component, Protocol):
    def verify(self, state: TopologyState, reference: TopologyState) -> dict[str, float]: ...
```

```python
# tecs/components/registry.py
from __future__ import annotations
from tecs.components.base import Component
from tecs.types import TopologyState


class ComponentRegistry:
    def __init__(self):
        self._components: dict[str, dict[str, Component]] = {}

    def register(self, component: Component) -> None:
        layer = component.layer
        name = component.name
        self._components.setdefault(layer, {})[name] = component

    def get(self, layer: str, name: str) -> Component:
        try:
            return self._components[layer][name]
        except KeyError:
            raise KeyError(f"Component '{name}' not found in layer '{layer}'")

    def check_compatible(self, component: Component, state: TopologyState) -> bool:
        return state.complex_type in component.compatible_types

    def list_layers(self) -> list[str]:
        return list(self._components.keys())

    def list_components(self, layer: str) -> list[str]:
        return list(self._components.get(layer, {}).keys())
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/ghost/Dev/test-1 && python -m pytest tests/test_components/test_registry.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add tecs/components/base.py tecs/components/registry.py tests/test_components/test_registry.py
git commit -m "feat: component base protocols and registry"
```

---

## Task 3: Representation Components (3개)

**Files:**
- Create: `tecs/components/representation/simplicial_complex.py`
- Create: `tecs/components/representation/riemannian_manifold.py`
- Create: `tecs/components/representation/dynamic_hypergraph.py`
- Create: `tests/test_components/test_simplicial_complex.py`
- Create: `tests/test_components/test_riemannian_manifold.py`
- Create: `tests/test_components/test_dynamic_hypergraph.py`

- [ ] **Step 1: Write failing test for simplicial_complex**

```python
# tests/test_components/test_simplicial_complex.py
import numpy as np
from tecs.types import TopologyState
from tecs.components.representation.simplicial_complex import SimplicialComplexComponent

def test_create():
    comp = SimplicialComplexComponent()
    assert comp.name == "simplicial_complex"
    assert comp.layer == "representation"
    assert "simplicial" in comp.compatible_types

def test_execute_builds_complex():
    comp = SimplicialComplexComponent()
    comp.configure({"max_edge_length": 2.0})
    # Input: point cloud in metadata
    state = TopologyState.empty("simplicial")
    state.metadata["points"] = np.random.rand(20, 3)
    result = comp.execute(state)
    assert result.complex is not None
    assert result.complex_type == "simplicial"

def test_measure_returns_betti():
    comp = SimplicialComplexComponent()
    comp.configure({"max_edge_length": 2.0})
    state = TopologyState.empty("simplicial")
    state.metadata["points"] = np.random.rand(20, 3)
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "betti_0" in metrics
    assert "betti_1" in metrics

def test_cost_in_range():
    comp = SimplicialComplexComponent()
    assert 0.0 <= comp.cost() <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ghost/Dev/test-1 && python -m pytest tests/test_components/test_simplicial_complex.py -v`
Expected: FAIL

- [ ] **Step 3: Implement simplicial_complex.py**

```python
# tecs/components/representation/simplicial_complex.py
from __future__ import annotations
import gudhi
import numpy as np
from tecs.types import TopologyState


class SimplicialComplexComponent:
    name = "simplicial_complex"
    layer = "representation"
    compatible_types = ["simplicial"]

    def __init__(self):
        self._params = {"max_edge_length": 2.0, "max_dimension": 2}

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        points = state.metadata.get("points")
        if points is None:
            raise ValueError("No 'points' in state.metadata")

        rips = gudhi.RipsComplex(points=points, max_edge_length=self._params["max_edge_length"])
        stree = rips.create_simplex_tree(max_dimension=self._params["max_dimension"])

        return TopologyState(
            complex=stree,
            complex_type="simplicial",
            curvature=np.array([]),
            metrics=state.metrics.copy(),
            history=state.history + [{"action": "build_rips_complex", "n_simplices": stree.num_simplices()}],
            metadata=state.metadata.copy(),
        )

    def measure(self, state: TopologyState) -> dict[str, float]:
        stree = state.complex
        stree.compute_persistence()
        betti = stree.betti_numbers()
        result = {}
        for i, b in enumerate(betti):
            result[f"betti_{i}"] = float(b)
        # Euler characteristic
        result["euler_characteristic"] = sum((-1)**i * b for i, b in enumerate(betti))
        return result

    def cost(self) -> float:
        return 0.3
```

- [ ] **Step 4: Run test**

Run: `cd /Users/ghost/Dev/test-1 && python -m pytest tests/test_components/test_simplicial_complex.py -v`
Expected: All PASS

- [ ] **Step 5: Write failing test for riemannian_manifold**

```python
# tests/test_components/test_riemannian_manifold.py
import numpy as np
import networkx as nx
from tecs.types import TopologyState
from tecs.components.representation.riemannian_manifold import RiemannianManifoldComponent

def test_create():
    comp = RiemannianManifoldComponent()
    assert comp.name == "riemannian_manifold"
    assert "graph" in comp.compatible_types

def test_execute_builds_graph_with_metric():
    comp = RiemannianManifoldComponent()
    state = TopologyState.empty("graph")
    state.metadata["points"] = np.random.rand(20, 3)
    state.metadata["k_neighbors"] = 5
    result = comp.execute(state)
    assert isinstance(result.complex, nx.Graph)
    assert len(result.complex.nodes) == 20
    assert result.curvature.shape[0] > 0

def test_measure_returns_curvature_stats():
    comp = RiemannianManifoldComponent()
    state = TopologyState.empty("graph")
    state.metadata["points"] = np.random.rand(20, 3)
    state.metadata["k_neighbors"] = 5
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "mean_curvature" in metrics
    assert "max_curvature" in metrics
```

- [ ] **Step 6: Implement riemannian_manifold.py**

```python
# tecs/components/representation/riemannian_manifold.py
from __future__ import annotations
import numpy as np
import networkx as nx
from scipy.spatial import KDTree
from tecs.types import TopologyState


class RiemannianManifoldComponent:
    name = "riemannian_manifold"
    layer = "representation"
    compatible_types = ["graph"]

    def __init__(self):
        self._params = {"k_neighbors": 5}

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        points = state.metadata.get("points")
        if points is None:
            raise ValueError("No 'points' in state.metadata")

        k = state.metadata.get("k_neighbors", self._params["k_neighbors"])
        tree = KDTree(points)
        G = nx.Graph()

        for i in range(len(points)):
            G.add_node(i, pos=points[i])

        distances, indices = tree.query(points, k=k + 1)
        for i in range(len(points)):
            for j_idx in range(1, k + 1):
                j = indices[i][j_idx]
                d = distances[i][j_idx]
                if not G.has_edge(i, j):
                    G.add_edge(i, j, weight=d)

        # Simple curvature estimate: degree-based proxy
        curvatures = np.array([1.0 - G.degree(n) / (2 * k) for n in G.nodes])

        return TopologyState(
            complex=G,
            complex_type="graph",
            curvature=curvatures,
            metrics=state.metrics.copy(),
            history=state.history + [{"action": "build_knn_graph", "n_nodes": len(G.nodes), "n_edges": len(G.edges)}],
            metadata=state.metadata.copy(),
        )

    def measure(self, state: TopologyState) -> dict[str, float]:
        c = state.curvature
        return {
            "mean_curvature": float(np.mean(c)) if len(c) > 0 else 0.0,
            "max_curvature": float(np.max(np.abs(c))) if len(c) > 0 else 0.0,
            "std_curvature": float(np.std(c)) if len(c) > 0 else 0.0,
        }

    def cost(self) -> float:
        return 0.2
```

- [ ] **Step 7: Run test**

Run: `cd /Users/ghost/Dev/test-1 && python -m pytest tests/test_components/test_riemannian_manifold.py -v`
Expected: All PASS

- [ ] **Step 8: Write failing test for dynamic_hypergraph**

```python
# tests/test_components/test_dynamic_hypergraph.py
import numpy as np
from tecs.types import TopologyState
from tecs.components.representation.dynamic_hypergraph import DynamicHypergraphComponent

def test_create():
    comp = DynamicHypergraphComponent()
    assert comp.name == "dynamic_hypergraph"
    assert "hypergraph" in comp.compatible_types

def test_execute_builds_hypergraph():
    comp = DynamicHypergraphComponent()
    state = TopologyState.empty("hypergraph")
    state.metadata["points"] = np.random.rand(20, 3)
    state.metadata["cluster_threshold"] = 1.0
    result = comp.execute(state)
    assert result.complex is not None
    assert result.complex_type == "hypergraph"

def test_measure_returns_hyperedge_stats():
    comp = DynamicHypergraphComponent()
    state = TopologyState.empty("hypergraph")
    state.metadata["points"] = np.random.rand(20, 3)
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "n_hyperedges" in metrics
    assert "mean_hyperedge_size" in metrics
```

- [ ] **Step 9: Implement dynamic_hypergraph.py**

```python
# tecs/components/representation/dynamic_hypergraph.py
from __future__ import annotations
import numpy as np
from scipy.spatial.distance import pdist, squareform
from tecs.types import TopologyState

try:
    import hypernetx as hnx
except ImportError:
    hnx = None


class DynamicHypergraphComponent:
    name = "dynamic_hypergraph"
    layer = "representation"
    compatible_types = ["hypergraph"]

    def __init__(self):
        self._params = {"cluster_threshold": 1.0, "min_cluster_size": 2}

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        if hnx is None:
            raise ImportError("hypernetx is required for DynamicHypergraphComponent")

        points = state.metadata.get("points")
        if points is None:
            raise ValueError("No 'points' in state.metadata")

        threshold = state.metadata.get("cluster_threshold", self._params["cluster_threshold"])
        dist_matrix = squareform(pdist(points))

        # Build hyperedges: for each node, group all nodes within threshold
        hyperedges = {}
        for i in range(len(points)):
            neighbors = tuple(sorted(np.where(dist_matrix[i] < threshold)[0]))
            if len(neighbors) >= self._params["min_cluster_size"]:
                key = f"he_{i}"
                hyperedges[key] = neighbors

        H = hnx.Hypergraph(hyperedges)

        return TopologyState(
            complex=H,
            complex_type="hypergraph",
            curvature=np.array([]),
            metrics=state.metrics.copy(),
            history=state.history + [{"action": "build_hypergraph", "n_hyperedges": len(hyperedges)}],
            metadata=state.metadata.copy(),
        )

    def measure(self, state: TopologyState) -> dict[str, float]:
        H = state.complex
        edges = list(H.edges)
        sizes = [len(H.edges[e]) for e in edges] if edges else [0]
        return {
            "n_hyperedges": float(len(edges)),
            "mean_hyperedge_size": float(np.mean(sizes)),
            "max_hyperedge_size": float(max(sizes)),
        }

    def cost(self) -> float:
        return 0.25
```

- [ ] **Step 10: Run all representation tests**

Run: `cd /Users/ghost/Dev/test-1 && python -m pytest tests/test_components/test_simplicial_complex.py tests/test_components/test_riemannian_manifold.py tests/test_components/test_dynamic_hypergraph.py -v`
Expected: All PASS

- [ ] **Step 11: Commit**

```bash
git add tecs/components/representation/ tests/test_components/test_simplicial_complex.py tests/test_components/test_riemannian_manifold.py tests/test_components/test_dynamic_hypergraph.py
git commit -m "feat: representation layer — simplicial complex, riemannian manifold, hypergraph"
```

---

## Task 4: Reasoning Components (3개)

**Files:**
- Create: `tecs/components/reasoning/ricci_flow.py`
- Create: `tecs/components/reasoning/homotopy_deformation.py`
- Create: `tecs/components/reasoning/geodesic_bifurcation.py`
- Create: `tests/test_components/test_ricci_flow.py`
- Create: `tests/test_components/test_homotopy_deformation.py`
- Create: `tests/test_components/test_geodesic_bifurcation.py`

Each reasoning component takes a TopologyState (with complex already built by representation layer) and transforms it.

- [ ] **Step 1: Write failing test for ricci_flow**

```python
# tests/test_components/test_ricci_flow.py
import numpy as np
import networkx as nx
from tecs.types import TopologyState
from tecs.components.reasoning.ricci_flow import RicciFlowComponent

def _make_graph_state():
    G = nx.karate_club_graph()
    for u, v in G.edges:
        G[u][v]["weight"] = 1.0
    curvatures = np.zeros(len(G.nodes))
    return TopologyState(complex=G, complex_type="graph", curvature=curvatures, metrics={}, history=[], metadata={})

def test_create():
    comp = RicciFlowComponent()
    assert comp.name == "ricci_flow"
    assert "graph" in comp.compatible_types

def test_execute_modifies_weights():
    comp = RicciFlowComponent()
    comp.configure({"n_steps": 5})
    state = _make_graph_state()
    original_weights = [state.complex[u][v]["weight"] for u, v in state.complex.edges]
    result = comp.execute(state)
    new_weights = [result.complex[u][v]["weight"] for u, v in result.complex.edges]
    assert original_weights != new_weights  # weights should change

def test_measure_returns_curvature():
    comp = RicciFlowComponent()
    comp.configure({"n_steps": 3})
    state = _make_graph_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "mean_ricci_curvature" in metrics
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ghost/Dev/test-1 && python -m pytest tests/test_components/test_ricci_flow.py -v`

- [ ] **Step 3: Implement ricci_flow.py**

```python
# tecs/components/reasoning/ricci_flow.py
from __future__ import annotations
import numpy as np
import networkx as nx
from tecs.types import TopologyState


class RicciFlowComponent:
    name = "ricci_flow"
    layer = "reasoning"
    compatible_types = ["graph"]

    def __init__(self):
        self._params = {"n_steps": 10, "step_size": 0.1}

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        G = state.complex.copy()
        n_steps = self._params["n_steps"]
        dt = self._params["step_size"]

        for _ in range(n_steps):
            curvatures = self._compute_ollivier_ricci(G)
            for (u, v), curv in curvatures.items():
                w = G[u][v].get("weight", 1.0)
                G[u][v]["weight"] = max(0.01, w - dt * curv * w)

        node_curv = np.zeros(len(G.nodes))
        for i, n in enumerate(G.nodes):
            neighbor_curvs = [curvatures.get((min(n, nb), max(n, nb)), 0.0) for nb in G.neighbors(n)]
            node_curv[i] = np.mean(neighbor_curvs) if neighbor_curvs else 0.0

        return TopologyState(
            complex=G,
            complex_type="graph",
            curvature=node_curv,
            metrics=state.metrics.copy(),
            history=state.history + [{"action": "ricci_flow", "n_steps": n_steps}],
            metadata=state.metadata.copy(),
        )

    def _compute_ollivier_ricci(self, G: nx.Graph) -> dict[tuple, float]:
        """Simplified Ollivier-Ricci curvature using neighbor overlap."""
        curvatures = {}
        for u, v in G.edges:
            nu = set(G.neighbors(u))
            nv = set(G.neighbors(v))
            overlap = len(nu & nv)
            total = len(nu | nv)
            curvatures[(min(u, v), max(u, v))] = (overlap / total) if total > 0 else 0.0
        return curvatures

    def measure(self, state: TopologyState) -> dict[str, float]:
        c = state.curvature
        return {
            "mean_ricci_curvature": float(np.mean(c)) if len(c) > 0 else 0.0,
            "std_ricci_curvature": float(np.std(c)) if len(c) > 0 else 0.0,
        }

    def cost(self) -> float:
        return 0.5
```

- [ ] **Step 4: Run test**

Run: `cd /Users/ghost/Dev/test-1 && python -m pytest tests/test_components/test_ricci_flow.py -v`
Expected: All PASS

- [ ] **Step 5: Implement + test homotopy_deformation.py (same TDD pattern)**

Test key behaviors: takes simplicial state, returns deformed state, preserves complex_type, measures filtration values. Implementation: uses GUDHI filtration to parameterize a deformation path between two complexes.

- [ ] **Step 6: Implement + test geodesic_bifurcation.py (same TDD pattern)**

Test key behaviors: takes graph state, finds unstable points (high curvature variance), generates multiple branching paths via SciPy ODE solver, returns best branch.

- [ ] **Step 7: Run all reasoning tests**

Run: `cd /Users/ghost/Dev/test-1 && python -m pytest tests/test_components/test_ricci_flow.py tests/test_components/test_homotopy_deformation.py tests/test_components/test_geodesic_bifurcation.py -v`
Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add tecs/components/reasoning/ tests/test_components/test_ricci_flow.py tests/test_components/test_homotopy_deformation.py tests/test_components/test_geodesic_bifurcation.py
git commit -m "feat: reasoning layer — ricci flow, homotopy deformation, geodesic bifurcation"
```

---

## Task 5: Emergence Components (3개)

**Files:**
- Create: `tecs/components/emergence/kuramoto_oscillator.py`
- Create: `tecs/components/emergence/ising_phase_transition.py`
- Create: `tecs/components/emergence/lyapunov_bifurcation.py`
- Create: corresponding test files

Same TDD pattern as Task 4. Key behaviors:

- **kuramoto_oscillator**: 3-layer coupled oscillator on graph/simplicial state. Measures order parameter r. configure() accepts K_ij coupling, n_steps.
- **ising_phase_transition**: Monte Carlo Ising model on complex. Information temperature T_i from Betti number change rate. Measures phase transition via magnetization.
- **lyapunov_bifurcation**: Perturbs trajectories in state space, measures divergence rate. Reports Lyapunov exponent λ. Injects nonlinear operator to force λ > 0.

- [ ] **Step 1: Write failing tests for all 3 components**

```python
# tests/test_components/test_kuramoto_oscillator.py
from tecs.components.emergence.kuramoto_oscillator import KuramotoOscillatorComponent
from tecs.types import TopologyState
import networkx as nx, numpy as np

def test_create():
    comp = KuramotoOscillatorComponent()
    assert comp.name == "kuramoto_oscillator"

def test_execute_on_graph():
    comp = KuramotoOscillatorComponent()
    comp.configure({"n_steps": 10, "K": 2.0})
    G = nx.karate_club_graph()
    state = TopologyState(complex=G, complex_type="graph", curvature=np.zeros(len(G.nodes)))
    result = comp.execute(state)
    assert result.complex is not None

def test_measure_order_parameter():
    comp = KuramotoOscillatorComponent()
    comp.configure({"n_steps": 10, "K": 2.0})
    G = nx.karate_club_graph()
    state = TopologyState(complex=G, complex_type="graph", curvature=np.zeros(len(G.nodes)))
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "order_parameter_r" in metrics
    assert 0.0 <= metrics["order_parameter_r"] <= 1.0

# tests/test_components/test_ising_phase_transition.py
def test_execute_monte_carlo():
    comp = IsingPhaseTransitionComponent()
    comp.configure({"n_sweeps": 50, "temperature": 2.0})
    state = TopologyState(complex=G, complex_type="graph", curvature=np.zeros(len(G.nodes)))
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "magnetization" in metrics

# tests/test_components/test_lyapunov_bifurcation.py
def test_measure_lyapunov_exponent():
    comp = LyapunovBifurcationComponent()
    state = TopologyState(complex=G, complex_type="graph", curvature=np.zeros(len(G.nodes)))
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "lyapunov_exponent" in metrics
```

- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Implement kuramoto_oscillator.py** (3-layer Kuramoto model, SciPy ODE, order parameter r)
- [ ] **Step 4: Implement ising_phase_transition.py** (Monte Carlo Ising, information temperature, magnetization)
- [ ] **Step 5: Implement lyapunov_bifurcation.py** (trajectory perturbation, divergence rate, λ sign tracking)
- [ ] **Step 6: Run all emergence tests — expected PASS**
- [ ] **Step 7: Commit**

```bash
git commit -m "feat: emergence layer — kuramoto, ising, lyapunov"
```

---

## Task 6: Verification Components (3개)

**Files:**
- Create: `tecs/components/verification/persistent_homology_dual.py`
- Create: `tecs/components/verification/shadow_manifold_audit.py`
- Create: `tecs/components/verification/stress_tensor_zero.py`
- Create: corresponding test files

These implement `VerificationComponent` protocol (with `verify(state, reference)` method).

- **persistent_homology_dual**: Builds dual complex K*, computes persistent homology on both, calculates Defect(r) = Σ|Δβ_n|.
- **shadow_manifold_audit**: Constructs shadow manifold M* with confidence fiber, computes hallucination_score = |Ric_M|·c/|Ric_M*|.
- **stress_tensor_zero**: Detects tears/intersections between manifolds, measures stress tensor magnitude.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_components/test_persistent_homology_dual.py
def test_verify_returns_defect():
    comp = PersistentHomologyDualComponent()
    result = comp.verify(state, reference)
    assert "defect_score" in result
    assert result["defect_score"] >= 0.0

# tests/test_components/test_shadow_manifold_audit.py
def test_verify_returns_hallucination_score():
    comp = ShadowManifoldAuditComponent()
    result = comp.verify(state, reference)
    assert "hallucination_score" in result

# tests/test_components/test_stress_tensor_zero.py
def test_verify_returns_stress_magnitude():
    comp = StressTensorZeroComponent()
    result = comp.verify(state, reference)
    assert "stress_magnitude" in result
```

- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Implement persistent_homology_dual.py** (GUDHI dual complex, persistent diagram comparison, Defect(r))
- [ ] **Step 4: Implement shadow_manifold_audit.py** (M* construction, confidence fiber, hallucination score)
- [ ] **Step 5: Implement stress_tensor_zero.py** (intersection detection, stress tensor, self-healing)
- [ ] **Step 6: Run all verification tests — expected PASS**
- [ ] **Step 7: Commit**

```bash
git commit -m "feat: verification layer — persistent homology dual, shadow manifold, stress tensor"
```

---

## Task 7: Optimization Components (3개)

**Files:**
- Create: `tecs/components/optimization/min_description_topology.py`
- Create: `tecs/components/optimization/fisher_distillation.py`
- Create: `tecs/components/optimization/free_energy_annealing.py`
- Create: corresponding test files

- **min_description_topology**: MDT(D) = argmin[Σβ_n + λ·d_GH]. Simplifies complex while preserving topology.
- **fisher_distillation**: Computes Fisher information matrix, absorbs into metric tensor. Measures compression ratio.
- **free_energy_annealing**: F_s = C(K) - T_s·H(K). Simulated annealing to minimize free energy.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_components/test_min_description_topology.py
def test_execute_reduces_complexity():
    comp = MinDescriptionTopologyComponent()
    result = comp.execute(state)
    assert comp.measure(result)["total_betti"] <= comp.measure(state)["total_betti"]

# tests/test_components/test_fisher_distillation.py
def test_execute_compresses():
    comp = FisherDistillationComponent()
    result = comp.execute(state)
    assert comp.measure(result)["compression_ratio"] < 1.0

# tests/test_components/test_free_energy_annealing.py
def test_execute_reduces_free_energy():
    comp = FreeEnergyAnnealingComponent()
    before = comp.measure(state)["free_energy"]
    result = comp.execute(state)
    after = comp.measure(result)["free_energy"]
    assert after <= before
```

- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Implement min_description_topology.py** (simplicial reduction, Betti preservation, GH distance approx)
- [ ] **Step 4: Implement fisher_distillation.py** (Fisher info matrix, metric absorption, eigenvalue truncation)
- [ ] **Step 5: Implement free_energy_annealing.py** (free energy F_s, simulated annealing, crystallization)
- [ ] **Step 6: Run all optimization tests — expected PASS**
- [ ] **Step 7: Commit**

```bash
git commit -m "feat: optimization layer — MDT, fisher distillation, free energy annealing"
```

---

## Task 8: Data Manager + Benchmark Data

**Files:**
- Create: `tecs/data/data_manager.py`
- Create: `tecs/data/conceptnet_loader.py`
- Create: `tecs/data/wordnet_loader.py`
- Create: `tecs/data/synthetic_generator.py`
- Create: `tests/test_data/test_data_manager.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_data/test_data_manager.py
from tecs.data.data_manager import DataManager
import numpy as np

def test_get_points_returns_array():
    dm = DataManager(cache_dir="data/", use_external=False)
    points = dm.get_points(n=50, dim=3)
    assert isinstance(points, np.ndarray)
    assert points.shape == (50, 3)

def test_get_concept_relations():
    dm = DataManager(cache_dir="data/", use_external=False)
    relations = dm.get_concept_relations(n=100)
    assert len(relations) > 0
    assert all("head" in r and "relation" in r and "tail" in r for r in relations)

def test_get_contradictions():
    dm = DataManager(cache_dir="data/", use_external=False)
    pairs = dm.get_contradictions(n=50)
    assert len(pairs) > 0
    assert all("positive" in p and "negative" in p for p in pairs)

def test_get_analogies():
    dm = DataManager(cache_dir="data/", use_external=False)
    analogies = dm.get_analogies(n=50)
    assert len(analogies) > 0
```

- [ ] **Step 2: Implement data_manager.py with synthetic fallbacks**

DataManager tries external data first (ConceptNet API + WordNet + SAT corpus). If unavailable or `use_external=False`, falls back to synthetic generation using `synthetic_generator.py`.

- [ ] **Step 3: Implement conceptnet_loader.py, wordnet_loader.py, synthetic_generator.py**

- [ ] **Step 4: Run tests**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat: data manager with ConceptNet, WordNet, synthetic generators"
```

---

## Task 9: Result Logger + Claude Reporter

**Files:**
- Create: `tecs/reporting/result_logger.py`
- Create: `tecs/reporting/claude_reporter.py`
- Create: `tests/test_reporting/test_result_logger.py`
- Create: `tests/test_reporting/test_claude_reporter.py`

- [ ] **Step 1: Write failing test for result_logger**

```python
# tests/test_reporting/test_result_logger.py
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
        ef = Path(tmpdir) / "emergence_events.jsonl"
        assert ef.exists()

def test_log_phase():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ResultLogger(run_dir=tmpdir)
        logger.log_phase({"phase": 1, "action": "transition", "top_candidates": 5})
        pf = Path(tmpdir) / "phase_log.jsonl"
        assert pf.exists()

def test_save_checkpoint():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ResultLogger(run_dir=tmpdir)
        logger.save_checkpoint({"phase": 2, "generation": 34})
        cp = Path(tmpdir) / "checkpoint.json"
        assert cp.exists()
```

- [ ] **Step 2: Implement result_logger.py**

```python
# tecs/reporting/result_logger.py
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime


class ResultLogger:
    def __init__(self, run_dir: str):
        self._dir = Path(run_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _append_jsonl(self, filename: str, data: dict) -> None:
        data["timestamp"] = datetime.now().isoformat()
        with open(self._dir / filename, "a") as f:
            f.write(json.dumps(data, default=str) + "\n")

    def log_generation(self, data: dict) -> None:
        self._append_jsonl("evolution.jsonl", data)

    def log_emergence_event(self, data: dict) -> None:
        self._append_jsonl("emergence_events.jsonl", data)

    def log_benchmark(self, data: dict) -> None:
        self._append_jsonl("benchmarks.jsonl", data)

    def log_phase(self, data: dict) -> None:
        self._append_jsonl("phase_log.jsonl", data)

    def save_checkpoint(self, data: dict) -> None:
        with open(self._dir / "checkpoint.json", "w") as f:
            json.dump(data, f, indent=2, default=str)

    def save_causal_graph(self, data: dict) -> None:
        with open(self._dir / "causal_graph.json", "w") as f:
            json.dump(data, f, indent=2, default=str)

    @property
    def run_dir(self) -> Path:
        return self._dir
```

- [ ] **Step 3: Write failing test for claude_reporter**

```python
# tests/test_reporting/test_claude_reporter.py
from unittest.mock import patch, MagicMock
from tecs.reporting.claude_reporter import ClaudeReporter

def test_generate_report_calls_subprocess():
    reporter = ClaudeReporter(enabled=True)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="# Report\nTest report", returncode=0)
        result = reporter.generate_report({"phase": 1, "best_fitness": 0.5}, prompt_prefix="분석해:")
        assert "Report" in result
        mock_run.assert_called_once()

def test_generate_report_disabled():
    reporter = ClaudeReporter(enabled=False)
    result = reporter.generate_report({"phase": 1}, prompt_prefix="분석:")
    assert result == ""  # returns empty when disabled

def test_generate_report_fallback_on_error():
    reporter = ClaudeReporter(enabled=True)
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = reporter.generate_report({"phase": 1}, prompt_prefix="분석:")
        assert result == ""  # graceful fallback
```

- [ ] **Step 4: Implement claude_reporter.py**

```python
# tecs/reporting/claude_reporter.py
from __future__ import annotations
import json
import subprocess


class ClaudeReporter:
    def __init__(self, enabled: bool = True):
        self._enabled = enabled

    def generate_report(self, data: dict, prompt_prefix: str = "이 결과를 분석해서 한국어 리포트를 작성해:") -> str:
        if not self._enabled:
            return ""
        try:
            data_str = json.dumps(data, indent=2, default=str, ensure_ascii=False)
            prompt = f"{prompt_prefix}\n\n{data_str}"
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return ""
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return ""
```

- [ ] **Step 5: Run tests**

Run: `cd /Users/ghost/Dev/test-1 && python -m pytest tests/test_reporting/ -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: result logger (JSONL/checkpoint) and claude CLI reporter"
```

---

## Task 10: Topology Simulator + Fitness Evaluator

**Files:**
- Create: `tecs/engine/topology_simulator.py`
- Create: `tecs/engine/fitness_evaluator.py`
- Create: `tests/test_engine/test_topology_simulator.py`
- Create: `tests/test_engine/test_fitness_evaluator.py`

TopologySimulator orchestrates the 5-layer pipeline for a single candidate. FitnessEvaluator computes the weighted fitness score.

- [ ] **Step 1: Write failing test for topology_simulator**

```python
# tests/test_engine/test_topology_simulator.py
def test_rejects_incompatible_combo():
    # simplicial representation + graph-only reasoning = error
    sim = TopologySimulator(registry)
    candidate = Candidate(components={"representation": "simplicial_complex", "reasoning": "ricci_flow", ...})
    with pytest.raises(IncompatibleComponentError):
        sim.simulate(candidate, data_points)

def test_runs_compatible_combo():
    sim = TopologySimulator(registry)
    candidate = Candidate(components={"representation": "riemannian_manifold", "reasoning": "ricci_flow", ...})
    result = sim.simulate(candidate, data_points)
    assert isinstance(result, TopologyState)
    assert len(result.history) == 5  # 5 layers executed

def test_verification_receives_dual_state():
    # verify() should be called with (state, reference), not execute()
    sim = TopologySimulator(registry)
    result = sim.simulate(candidate_with_verification, data_points)
    assert "defect_score" in result.metrics or "hallucination_score" in result.metrics
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement topology_simulator.py** (registry lookup, type check, sequential 5-layer pipeline, dual state for verification)
- [ ] **Step 4: Run test — expected PASS**

- [ ] **Step 5: Write failing test for fitness_evaluator**

```python
# tests/test_engine/test_fitness_evaluator.py
def test_weighted_fitness():
    evaluator = FitnessEvaluator(w_e=0.4, w_b=0.4, w_f=0.2)
    fitness = evaluator.compute(emergence={"betti_change": 0.5, ...}, benchmark={"concept": 0.8, ...}, cost=0.3)
    assert 0.0 <= fitness <= 1.0

def test_handles_missing_metrics():
    evaluator = FitnessEvaluator(w_e=0.4, w_b=0.4, w_f=0.2)
    fitness = evaluator.compute(emergence={}, benchmark={}, cost=0.0)
    assert fitness == 0.0  # all zeros when no data

def test_normalization_within_window():
    evaluator = FitnessEvaluator(w_e=0.4, w_b=0.4, w_f=0.2)
    evaluator.update_history([0.3, 0.5, 0.7])
    normalized = evaluator.normalize_metric(0.5, "betti_change")
    assert 0.0 <= normalized <= 1.0
```

- [ ] **Step 6: Implement fitness_evaluator.py**
- [ ] **Step 7: Run test — expected PASS**
- [ ] **Step 8: Commit**

```bash
git commit -m "feat: topology simulator and fitness evaluator"
```

---

## Task 11: Evolution Engine

**Files:**
- Create: `tecs/engine/evolution_engine.py`
- Create: `tecs/engine/architecture_generator.py`
- Create: `tests/test_engine/test_evolution_engine.py`
- Create: `tests/test_engine/test_architecture_generator.py`

- [ ] **Step 1: Write failing test for architecture_generator**

```python
# tests/test_engine/test_architecture_generator.py
def test_random_population():
    gen = ArchitectureGenerator(seed=42)
    pop = gen.random_population(n=10, generation=0, phase=1)
    assert len(pop) == 10
    assert all(len(c.components) == 5 for c in pop)

def test_mutate_records_layer():
    gen = ArchitectureGenerator(seed=42)
    parent = Candidate.random(generation=0, phase=1)
    child = gen.mutate(parent, target_layer="reasoning")
    assert child.mutation_layer == "reasoning"
    assert child.parent_ids == [parent.id]
    assert child.components["reasoning"] != parent.components["reasoning"]

def test_crossover_records_parents():
    gen = ArchitectureGenerator(seed=42)
    p1 = Candidate.random(generation=0, phase=1)
    p2 = Candidate.random(generation=0, phase=1)
    child = gen.crossover(p1, p2)
    assert set(child.parent_ids) == {p1.id, p2.id}

def test_diversity_filter():
    gen = ArchitectureGenerator(seed=42)
    pop = [Candidate.random(generation=0, phase=1) for _ in range(10)]
    filtered = gen.enforce_diversity(pop, threshold=0.3)
    # No two candidates should be identical
    for i, a in enumerate(filtered):
        for b in filtered[i+1:]:
            assert a.hamming_distance(b) > 0
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement architecture_generator.py**
- [ ] **Step 4: Run test — expected PASS**

- [ ] **Step 5: Write failing test for evolution_engine**

```python
# tests/test_engine/test_evolution_engine.py
def test_tournament_selection():
    engine = EvolutionEngine(cfg)
    pop = [make_candidate(fitness=f) for f in [0.1, 0.5, 0.9, 0.3]]
    selected = engine.tournament_select(pop, tournament_size=3)
    assert selected.fitness >= 0.3  # likely picks a good one

def test_elite_preservation():
    engine = EvolutionEngine(cfg)
    pop = [make_candidate(fitness=f) for f in [0.1, 0.5, 0.9, 0.3, 0.7]]
    elites = engine.get_elites(pop, ratio=0.2)
    assert len(elites) == 1
    assert elites[0].fitness == 0.9

def test_targeted_mutation_uses_causal_info():
    engine = EvolutionEngine(cfg)
    causal_info = {"weakest_layer": "verification"}
    parent = Candidate.random(generation=0, phase=1)
    child = engine.targeted_mutate(parent, causal_info)
    assert child.mutation_layer == "verification"

def test_next_generation():
    engine = EvolutionEngine(cfg)
    pop = [make_candidate(fitness=random.random()) for _ in range(10)]
    next_pop = engine.next_generation(pop, causal_info=None)
    assert len(next_pop) == len(pop)
    assert all(c.generation == pop[0].generation + 1 for c in next_pop)
```

- [ ] **Step 6: Implement evolution_engine.py**
- [ ] **Step 7: Run test — expected PASS**
- [ ] **Step 8: Commit**

```bash
git commit -m "feat: evolution engine with lineage tracking and targeted mutation"
```

---

## Task 12: Emergence Detector + Causal Tracer

**Files:**
- Create: `tecs/analysis/emergence_detector.py`
- Create: `tecs/analysis/causal_tracer.py`
- Create: `tests/test_analysis/test_emergence_detector.py`
- Create: `tests/test_analysis/test_causal_tracer.py`

- [ ] **Step 1: Write failing test for emergence_detector**

```python
# tests/test_analysis/test_emergence_detector.py
def test_no_spike_early_generations():
    detector = EmergenceDetector(cfg.emergence)
    event = detector.check(generation=1, metrics={"betti_0": 5, "betti_1": 2})
    assert event is None  # min_generations=3 not reached

def test_detects_betti_spike():
    detector = EmergenceDetector(cfg.emergence)
    for i in range(10):
        detector.check(generation=i, metrics={"betti_1": 2.0})
    event = detector.check(generation=10, metrics={"betti_1": 10.0})  # 4σ jump
    assert event is not None
    assert event["metric"] == "betti_1"

def test_detects_lyapunov_sign_change():
    detector = EmergenceDetector(cfg.emergence)
    for i in range(5):
        detector.check(generation=i, metrics={"lyapunov_exponent": -0.5})
    event = detector.check(generation=5, metrics={"lyapunov_exponent": 0.3})
    assert event is not None

def test_sliding_window_size():
    detector = EmergenceDetector(cfg.emergence)
    assert detector._window_size == 10
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement emergence_detector.py**
- [ ] **Step 4: Run test — expected PASS**

- [ ] **Step 5: Write failing test for causal_tracer**

```python
# tests/test_analysis/test_causal_tracer.py
def test_requires_min_generations():
    tracer = CausalTracer(min_generations=20)
    result = tracer.analyze(history_of_5_generations)
    assert result["confidence"] == "insufficient_data"

def test_identifies_weakest_layer():
    tracer = CausalTracer(min_generations=5)  # relaxed for test
    # Simulate 10 generations where verification layer changes correlate with fitness drops
    history = make_history_with_weak_verification(n=10)
    result = tracer.analyze(history)
    assert result["weakest_layer"] == "verification"

def test_causal_strength_matrix():
    tracer = CausalTracer(min_generations=5)
    history = make_history(n=10)
    result = tracer.analyze(history)
    assert "causal_matrix" in result
    assert result["causal_matrix"].shape == (5, 5)  # 5 layers x 5 metrics
```

- [ ] **Step 6: Implement causal_tracer.py**
- [ ] **Step 7: Run test — expected PASS**
- [ ] **Step 8: Commit**

```bash
git commit -m "feat: emergence detector and causal tracer"
```

---

## Task 13: Benchmark Runner + Scale Controller

**Files:**
- Create: `tecs/engine/benchmark_runner.py`
- Create: `tecs/engine/scale_controller.py`
- Create: `tests/test_engine/test_benchmark_runner.py`
- Create: `tests/test_engine/test_scale_controller.py`

- [ ] **Step 1: Write failing test for benchmark_runner**

```python
# tests/test_engine/test_benchmark_runner.py
def test_concept_relation_accuracy():
    runner = BenchmarkRunner(data_manager)
    score = runner.run_concept_relation(candidate, state)
    assert 0.0 <= score <= 1.0

def test_contradiction_detection():
    runner = BenchmarkRunner(data_manager)
    score = runner.run_contradiction(candidate, state)
    assert 0.0 <= score <= 1.0

def test_analogy_reasoning():
    runner = BenchmarkRunner(data_manager)
    score = runner.run_analogy(candidate, state)
    assert 0.0 <= score <= 1.0

def test_combined_score():
    runner = BenchmarkRunner(data_manager)
    scores = runner.run_all(candidate, state)
    assert "combined" in scores
    assert scores["combined"] == (scores["concept"] + scores["contradiction"] + scores["analogy"]) / 3
```

- [ ] **Step 2: Implement benchmark_runner.py**
- [ ] **Step 3: Run test — expected PASS**

- [ ] **Step 4: Write failing test for scale_controller**

```python
# tests/test_engine/test_scale_controller.py
def test_starts_at_phase1_scale():
    sc = ScaleController(cfg.scaling)
    assert sc.current_nodes == 100

def test_scales_up_on_phase_change():
    sc = ScaleController(cfg.scaling)
    sc.on_phase_change(2)
    assert sc.current_nodes == 1000

def test_memory_budget_check():
    sc = ScaleController(cfg.scaling)
    assert sc.check_memory_ok(max_pct=80) is True
```

- [ ] **Step 5: Implement scale_controller.py**
- [ ] **Step 6: Run test — expected PASS**
- [ ] **Step 7: Commit**

```bash
git commit -m "feat: benchmark runner and scale controller"
```

---

## Task 14a: Orchestrator Core (single generation loop)

**Files:**
- Create: `tecs/orchestrator.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_orchestrator.py
from unittest.mock import MagicMock, patch
from tecs.orchestrator import Orchestrator
from tecs.config import load_config

def test_orchestrator_runs_phase1():
    cfg = load_config("config.yaml", overrides={"scaling.phase1_max_gen": 2, "search.population_size": 5})
    orch = Orchestrator(cfg)
    with patch.object(orch, '_simulate_candidate', return_value=0.5):
        orch.run_phase(1)
    assert orch.current_phase == 1
    assert len(orch.population) > 0

def test_single_generation_step():
    cfg = load_config("config.yaml", overrides={"search.population_size": 5})
    orch = Orchestrator(cfg)
    orch._init_population()
    with patch.object(orch, '_simulate_candidate', return_value=0.5):
        orch._run_generation()
    assert orch.generation == 1
```

- [ ] **Step 2: Implement orchestrator core** (`__init__`, `_init_population`, `_run_generation`, `run_phase`)
- [ ] **Step 3: Run test — expected PASS**
- [ ] **Step 4: Commit**

```bash
git commit -m "feat: orchestrator core — single generation loop"
```

---

## Task 14b: Phase Transitions + Termination

**Files:**
- Modify: `tecs/orchestrator.py`
- Modify: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing tests for phase transitions**

```python
def test_phase_1_to_2_transition():
    cfg = load_config("config.yaml", overrides={"scaling.phase1_max_gen": 1, "search.population_size": 5})
    orch = Orchestrator(cfg)
    with patch.object(orch, '_simulate_candidate', return_value=0.5):
        orch.run_phase(1)
    assert orch.decide_next_phase() == 2

def test_phase_4_to_2_loop():
    cfg = load_config("config.yaml")
    orch = Orchestrator(cfg)
    orch.current_phase = 4
    orch._loop_count = 0
    orch._prev_loop_best = 0.5
    orch._best_fitness = 0.55  # improvement > 0.01
    assert orch.decide_next_phase() == 2
    assert orch._loop_count == 1

def test_phase_4_to_5_on_max_loops():
    cfg = load_config("config.yaml", overrides={"termination.max_loops": 3})
    orch = Orchestrator(cfg)
    orch.current_phase = 4
    orch._loop_count = 3
    assert orch.decide_next_phase() == 5

def test_phase_4_to_5_on_no_improvement():
    cfg = load_config("config.yaml")
    orch = Orchestrator(cfg)
    orch.current_phase = 4
    orch._prev_loop_best = 0.5
    orch._best_fitness = 0.505  # improvement <= 0.01
    assert orch.decide_next_phase() == 5

def test_termination_plateau():
    cfg = load_config("config.yaml", overrides={"termination.plateau_generations": 2})
    orch = Orchestrator(cfg)
    orch._fitness_history = [0.5, 0.5, 0.5]
    assert orch.should_terminate() == "plateau"

def test_termination_success():
    cfg = load_config("config.yaml")
    orch = Orchestrator(cfg)
    orch._current_metrics = {"hallucination_rate": 0.005, "emergence_rate": 0.85, "benchmark_avg": 0.75}
    assert orch.should_terminate() == "success"

def test_no_termination_when_improving():
    cfg = load_config("config.yaml")
    orch = Orchestrator(cfg)
    orch._fitness_history = [0.3, 0.4, 0.5, 0.6]
    assert orch.should_terminate() is None
```

- [ ] **Step 2: Implement phase transition + termination logic**
- [ ] **Step 3: Run test — expected PASS**
- [ ] **Step 4: Commit**

```bash
git commit -m "feat: orchestrator phase transitions and termination conditions"
```

---

## Task 14c: Checkpoint/Resume + Emergence Spike Handling

**Files:**
- Modify: `tecs/orchestrator.py`
- Modify: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing tests for checkpoint/resume**

```python
import tempfile, json

def test_checkpoint_saves_state():
    cfg = load_config("config.yaml", overrides={"search.population_size": 3, "search.seed": 42})
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch._init_population()
        orch._save_checkpoint()
        cp_path = list(Path(tmpdir).glob("runs/*/checkpoint.json"))[0]
        cp = json.loads(cp_path.read_text())
        assert cp["phase"] == orch.current_phase
        assert cp["generation"] == orch.generation
        assert "population" in cp
        assert "rng_state" in cp

def test_resume_from_checkpoint():
    cfg = load_config("config.yaml", overrides={"search.population_size": 3, "search.seed": 42})
    with tempfile.TemporaryDirectory() as tmpdir:
        # Run and save
        orch1 = Orchestrator(cfg, results_dir=tmpdir)
        orch1._init_population()
        orch1.generation = 5
        orch1._save_checkpoint()

        # Resume
        run_dir = list(Path(tmpdir).glob("runs/run_*"))[0]
        orch2 = Orchestrator.from_checkpoint(str(run_dir), cfg)
        assert orch2.generation == 5
        assert len(orch2.population) == 3

def test_rng_state_restored():
    """After resume, RNG produces same sequence as if uninterrupted."""
    cfg = load_config("config.yaml", overrides={"search.population_size": 3, "search.seed": 42})
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch._init_population()
        orch._save_checkpoint()
        run_dir = list(Path(tmpdir).glob("runs/run_*"))[0]
        orch2 = Orchestrator.from_checkpoint(str(run_dir), cfg)
        # Both should produce same next random candidate
        r1 = orch._rng.random()
        r2 = orch2._rng.random()
        assert r1 == r2

def test_emergence_spike_triggers_report_and_hall_of_fame():
    cfg = load_config("config.yaml", overrides={"reporting.claude_cli": False})
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        event = {"generation": 12, "metric": "betti_1", "delta": 3.0, "candidate_id": "abc"}
        orch._on_emergence_spike(event)
        ef = list(Path(tmpdir).glob("runs/*/emergence_events.jsonl"))[0]
        assert ef.exists()
        hf = Path(tmpdir) / "hall_of_fame" / "best_candidates.jsonl"
        assert hf.exists()
```

- [ ] **Step 2: Implement checkpoint save/load and emergence spike handling**
- [ ] **Step 3: Run test — expected PASS**
- [ ] **Step 4: Commit**

```bash
git commit -m "feat: orchestrator checkpoint/resume and emergence spike handling"
```

---

## Task 15: run.py Integration + End-to-End Test

**Files:**
- Modify: `run.py`
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
import tempfile
from pathlib import Path
from tecs.config import load_config
from tecs.orchestrator import Orchestrator

def test_full_run_tiny():
    """Tiny end-to-end run: 3 candidates, 2 generations, Phase 1 only."""
    cfg = load_config("config.yaml", overrides={
        "search.population_size": 3,
        "scaling.phase1_max_gen": 2,
        "scaling.phase1_nodes": 10,
        "reporting.claude_cli": False,
        "termination.max_hours": 0.01,
    })
    with tempfile.TemporaryDirectory() as tmpdir:
        orch = Orchestrator(cfg, results_dir=tmpdir)
        orch.run()
        # Check outputs exist
        run_dir = list(Path(tmpdir).glob("runs/run_*"))
        assert len(run_dir) == 1
        assert (run_dir[0] / "evolution.jsonl").exists()
        assert (run_dir[0] / "phase_log.jsonl").exists()
```

- [ ] **Step 2: Update run.py to wire everything**

```python
# run.py
import argparse
import sys
from datetime import datetime
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="TECS Meta-Research Engine")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--resume", default=None)
    parser.add_argument("--results-dir", default="results")
    args = parser.parse_args()

    from tecs.config import load_config
    from tecs.orchestrator import Orchestrator

    cfg = load_config(args.config)

    if args.resume:
        orch = Orchestrator.from_checkpoint(args.resume, cfg)
        print(f"Resuming from {args.resume}")
    else:
        orch = Orchestrator(cfg, results_dir=args.results_dir)
        print(f"TECS Engine started. Population: {cfg.search.population_size}, Seed: {cfg.search.seed}")

    orch.run()
    print(f"Done. Results: {orch.logger.run_dir}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run integration test**

Run: `cd /Users/ghost/Dev/test-1 && python -m pytest tests/test_integration.py -v --timeout=120`
Expected: PASS

- [ ] **Step 4: Run full test suite**

Run: `cd /Users/ghost/Dev/test-1 && python -m pytest -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: run.py wiring and end-to-end integration test"
```

---

## Task 16: REPORT.md Template + Hall of Fame

**Files:**
- Create: `tecs/reporting/report_template.md.j2`
- Modify: `tecs/reporting/result_logger.py` (add `generate_markdown_report()`)
- Create: `results/hall_of_fame/best_candidates.jsonl` (empty)
- Create: `results/README.md`

- [ ] **Step 1: Create Jinja2 template for REPORT.md**
- [ ] **Step 2: Add markdown report generation to ResultLogger**
- [ ] **Step 3: Add hall_of_fame update logic**
- [ ] **Step 4: Create results/README.md stub**
- [ ] **Step 5: Test report generation**
- [ ] **Step 6: Commit**

```bash
git commit -m "feat: REPORT.md template, hall of fame, results README"
```

---

## Task Summary

| Task | Description | Dependencies |
|------|-------------|-------------|
| 1 | Project scaffold + core types | None |
| 2 | Component base + registry | 1 |
| 3 | Representation components (3) | 2 |
| 4 | Reasoning components (3) | 2 |
| 5 | Emergence components (3) | 2 |
| 6 | Verification components (3) | 2 |
| 7 | Optimization components (3) | 2 |
| 8 | Data manager + benchmark data | 1 |
| 9 | Result logger + claude reporter | 1 |
| 10 | Topology simulator + fitness evaluator | 2, 3-7 |
| 11 | Evolution engine + architecture generator | 1, 10 |
| 12 | Emergence detector + causal tracer | 1, 10 |
| 13 | Benchmark runner + scale controller | 8, 10 |
| 14a | Orchestrator core | 10-13 |
| 14b | Phase transitions + termination | 14a |
| 14c | Checkpoint/resume + emergence spike | 14b, 9 |
| 15 | run.py integration + E2E test | 14c |
| 16 | REPORT.md template + hall of fame | 9 |

**Parallelizable:** Tasks 3-7 can all run in parallel (they only depend on Task 2). Tasks 8, 9 can run in parallel with 3-7.
