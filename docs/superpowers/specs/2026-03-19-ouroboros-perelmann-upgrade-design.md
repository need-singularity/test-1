# Ouroboros Engine Upgrade: Perelmann Verification Framework

**Date**: 2026-03-19
**Status**: Approved
**Approach**: Pragmatic Patch (C) — minimal file changes, interface-preserving
**Review**: 1 round — 3 Critical, 4 Important, 3 Suggestions resolved

## Problem Statement

The current `ouroboros_distance` uses `poincare_distance(u, -v)` as a single
antipodal reflection to approximate Fuchsian boundary identification. Three
independent model analyses (GPT-5.4, Claude Opus 4.6, Gemini) agree that:

1. `-v` is valid in 2D but insufficient in higher dimensions — must be replaced
   by quotient distance $d_M([x],[y]) = \inf_{\gamma \in \Gamma} d_{\mathbb{H}^n}(x, \gamma y)$
2. Perelman's geometrization theorem provides topological justification but
   not computational license — actual implementation requires discrete isometry
   group $\Gamma$ with explicit generators
3. Discrete Ricci flow (Ollivier curvature) can verify curvature convergence
4. Mostow rigidity (dim≥3) guarantees geometric uniqueness given correct $\pi_1$

## Scope

Full implementation:
- Γ-orbit quotient distance replacing antipodal mapping
- Ollivier curvature (self-implemented, scipy `linear_sum_assignment`)
- Discrete Ricci flow + neck pinch detection
- Injectivity radius sweep + adaptive sigma
- Eval set reinforcement
- Independent verification script
- Documentation (THEORY.md, IMPLEMENTATION.md, VERIFICATION.md)

## Architecture

### Dimension Strategy

- **dim=2 (default)**: Rigorous Fuchsian group with 2 generators. Primary target.
- **dim=d (variable)**: Infrastructure for 2d generators per coordinate reflection.
  A/B testable in Phase 4 experiments.
- **dim=3 (Mostow)**: Annotated code path. Mostow rigidity guarantees geometric
  uniqueness — paradoxically safer than dim=2 post-implementation.

All three paths implemented with verification and comments for future expansion.

### File Changes

| Component | File | Change Type |
|-----------|------|-------------|
| FuchsianGroup class | `ouroboros_geometry.py` | New file |
| Verification metrics | `verification.py` | New file (importable module for tests + CLI) |
| quotient_distance | `poincare_utils.py` | Replace `-v` internals |
| Ollivier curvature | `poincare_utils.py` | Add |
| Ricci flow + neck pinch | `poincare_utils.py` | Add |
| adaptive_sigma | `poincare_utils.py` | Add |
| Verification script | `scripts/verify_ouroboros.py` | New file |
| Eval set reinforcement | `tecs/inference/eval_set.py` | Edit |
| Theory docs | `docs/ouroboros/THEORY.md` | New file |
| Implementation docs | `docs/ouroboros/IMPLEMENTATION.md` | New file |
| Verification docs | `docs/ouroboros/VERIFICATION.md` | New file |
| CLAUDE.md | `CLAUDE.md` | Update |

### Interface Preservation

The `ouroboros_distance()` signature is **strictly unchanged**:
```python
def ouroboros_distance(
    u, v, analogy_mode=False, theta=0.85, sigma=0.15, eps=1e-7
) -> tuple[float, bool]
```

Internal change: `poincare_distance(u, -v)` → `FuchsianGroup.quotient_distance(u, v)`.

**Adaptive sigma** is a preprocessing step that computes a float value *before*
calling `ouroboros_distance` — not a string parameter. The caller passes the
computed float to `sigma=`. This preserves the `sigma: float` type contract.

### Rollback Strategy

A feature flag `use_fuchsian: bool` in `FuchsianGroup` defaults to `True`.
Setting it to `False` falls back to the original `-v` antipodal mapping.
This enables safe A/B comparison and instant rollback if quotient distance
produces worse inference results.

## Component Designs

### 1. FuchsianGroup

```
class FuchsianGroup:
    __init__(dim, num_generators=None, use_fuchsian=True)
        dim=2: 2 generators as Moebius transformations
               γ₁: z → -z (antipodal, existing behavior)
               γ₂: z → iz  (π/2 rotation in Poincare disk)
               Represented as (a, b) pairs where γ(z) = (az+b)/(b̄z+ā)
               with |a|² - |b|² = 1
        dim=d: 2d generators — coordinate hyperplane reflections
               Each as Moebius transform in the d-dim ball model
        dim=3: Mostow rigidity annotations
        use_fuchsian=False: orbit() returns only [v, -v] (legacy fallback)

    generators() → list[Callable]
        Each generator: np.ndarray → np.ndarray
        Implemented as proper hyperbolic isometries (Moebius transforms),
        NOT Euclidean linear maps applied to Poincare coordinates.

    orbit(v, max_depth=2) → list[np.ndarray]
        Word length 0..max_depth, deduplicated by poincare_distance < 0.01
        (hyperbolic scale epsilon, not Euclidean)
        max_depth enables GPT-5.4's "generator word length ablation"
        Orbit size capped at 50 to prevent explosion

    quotient_distance(u, v) → float
        inf_{γv in orbit(v)} d_H(u, γv)
```

### 2. Ollivier-Ricci Curvature (Self-Implemented)

```
ollivier_ricci_curvature(G, a, b, embeddings=None) → float
    - Uniform distribution μₐ, μᵦ over 1-hop neighbors of a, b
    - Cost matrix: poincare_distance between all neighbor pairs
    - When |N(a)| ≠ |N(b)|: pad smaller set with dummy nodes at
      max-distance cost to make cost matrix square, then apply
      scipy.optimize.linear_sum_assignment
    - κ(a,b) = 1 - W₁(μₐ, μᵦ) / d(a,b)

compute_ricci_flow(G, embeddings, iterations=10, step=0.1)
    → dict[edge, list[float]]
    - Per-iteration: compute curvature → adjust edge weights
    - Convergence: curvature variance < epsilon

detect_neck_pinch(curvature_map, threshold=None)
    → list[tuple[node, node, float]]
    - Default threshold: mean + 2*std of curvature distribution
      (data-driven, not hardcoded 0.5 — avoids false positives
      from natural high-curvature clusters in small-world graphs)
    - Edges with positive curvature above threshold
    - These are candidate geometric bottlenecks
    - Note: Ollivier-Ricci on graphs differs from smooth manifold
      Ricci curvature. High positive values indicate dense clusters,
      not necessarily pathological neck pinches. The verification
      script reports these for human inspection rather than auto-reject.
```

### 3. Adaptive Sigma

```
adaptive_sigma(embeddings, theta=0.85) → float
    - Compute pairwise distances among boundary nodes (||x|| > theta)
    - sigma = clamp(1.0 / median_distance, 0.05, 0.30)
    - Dense boundary → lower sigma, sparse → higher sigma
    - Returns a float value; caller passes it to ouroboros_distance(sigma=...)
    - This is a preprocessing step, NOT a parameter type change
```

### 4. Verification Script

`scripts/verify_ouroboros.py` — independent of evolution loop.

**6 Metrics (algebraic + differential-geometric):**

| # | Metric | Type | Target | Notes |
|---|--------|------|--------|-------|
| 1 | Group invariance violation rate | Algebraic | 0% | d_M([γx],[y]) == d_M([x],[y]) |
| 2 | Triangle inequality violation rate | Algebraic | 0% | d_M(x,z) ≤ d_M(x,y) + d_M(y,z) |
| 3 | Antipodal dependency rate | Algebraic | High = improvement | How often quotient ≠ old -v result |
| 4 | Curvature convergence (variance after Ricci flow) | Diff-geom | Empirical baseline first | Target TBD after initial run on current graph |
| 5 | Neck pinch candidates (curvature > mean+2σ) | Diff-geom | Report, no auto-reject | Human inspection |
| 6 | Injectivity radius distribution | Diff-geom | Report histogram | Defined as min quotient_distance(v, γv) over non-identity γ ∈ Γ for each node v |

**Execution modes:**
```bash
python scripts/verify_ouroboros.py --checkpoint <path>
python scripts/verify_ouroboros.py --sweep-depth 0,1,2,3 --sweep-sigma 0.05,0.10,0.15,0.20
python scripts/verify_ouroboros.py --eval-only
```

**Output:** PASS/FAIL (metrics 1-2 only) + advisory report (metrics 3-6)
+ `results/ouroboros_verification.json`

### 5. Eval Set Reinforcement

Add to `eval_set.py`:
- 5 Level-2-only queries (no direct triple in Level 1)
  - e.g., `("fur", "PartOf", "cat")`, `("wheel", "PartOf", "car")`
- 3 Level-4 cross-domain queries using **existing** `"RelatedTo"` relation
  - e.g., `("gravity", "RelatedTo", "price")` — NOT "AnalogousTo"
  - `"RelatedTo"` is already handled by the `is_analogy` check in
    `inference_engine.py:188` and exists in EVAL_KNOWLEDGE
- Reverse triples in EVAL_KNOWLEDGE
  - e.g., `("electron", "PartOf", "atom")`

### 6. inference_engine.py Integration

Interface-preserving changes only:
- `__init__`: Create `FuchsianGroup` instance (dim auto-detected from embeddings)
- `__init__`: Optionally compute `adaptive_sigma` and store as `self._sigma`
- `_level2_multipath`: Pass `self._sigma` to `ouroboros_distance(sigma=self._sigma)`
- Note: `_level2_multipath` already receives `relation` as an explicit parameter
  (confirmed at line 125). No scope fix needed — the prior analysis was incorrect.
- All imports unchanged

### Benchmark Impact

Existing benchmark scores may shift after the quotient distance upgrade:
- `run_inference_benchmark` creates `InferenceEngine` which calls `ouroboros_distance`
- The `use_fuchsian` feature flag enables A/B comparison pre/post upgrade
- `config.yaml` targets (`target_benchmark: 0.7`) should be re-evaluated after
  initial verification run, not pre-adjusted

## Documentation

```
docs/ouroboros/
├── THEORY.md          — Mathematical background (paper §3.4 basis)
├── IMPLEMENTATION.md  — Implementation guide with parameter tuning
└── VERIFICATION.md    — Verification protocol and metric definitions
```

## Verification Pipeline Order

1. **Algebraic verification** (fast, direct) — metrics 1-3
2. **Ricci flow verification** (slow, global) — metrics 4-6

Two-stage pipeline as recommended by cross-model analysis.

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Phase 2 worker still running | Interface preservation — no import changes |
| Quotient distance produces worse results | `use_fuchsian` feature flag for A/B and rollback |
| poincare_utils.py grows large | Split FuchsianGroup into `ouroboros_geometry.py` now |
| Orbit explosion at high max_depth | Deduplication + capped orbit size (50) |
| Ollivier curvature slow on large graphs | Verification script is independent, not in evolution loop |
| Neck pinch false positives | Data-driven threshold (mean+2σ), human inspection, no auto-reject |
| Benchmark targets may shift | A/B compare before adjusting config.yaml thresholds |

## Future Work (Annotated in Code)

- Refactor to `tecs/inference/geometry/` package (Approach B)
- Teichmüller space exploration for dim=2
- Full Kleinian group implementation for dim=3
- Integration of verification into evolution loop (per-phase-transition)
