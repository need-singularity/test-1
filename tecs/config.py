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
class CausalConfig:
    p_value_threshold: float = 0.05
    min_generations_for_significance: int = 20

@dataclass
class DataConfig:
    cache_dir: str = "data/"
    use_external: bool = True
    conceptnet_url: str = "https://api.conceptnet.io"
    conceptnet_cache: str = "data/conceptnet/"
    wordnet_auto_download: bool = True

@dataclass
class TECSConfig:
    search: SearchConfig = None
    scaling: ScalingConfig = None
    fitness: FitnessConfig = None
    emergence: EmergenceConfig = None
    termination: TerminationConfig = None
    reporting: ReportingConfig = None
    causal: CausalConfig = None
    data: DataConfig = None

    def __post_init__(self):
        self.search = self.search or SearchConfig()
        self.scaling = self.scaling or ScalingConfig()
        self.fitness = self.fitness or FitnessConfig()
        self.emergence = self.emergence or EmergenceConfig()
        self.termination = self.termination or TerminationConfig()
        self.reporting = self.reporting or ReportingConfig()
        self.causal = self.causal or CausalConfig()
        self.data = self.data or DataConfig()


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
        causal=CausalConfig(**raw.get("causal", {})),
        data=DataConfig(**raw.get("data", {})),
    )
    return cfg
