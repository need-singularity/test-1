# Ouroboros Engine Upgrade: Perelmann Verification Framework

**Date**: 2026-03-19
**Status**: Approved
**Approach**: Pragmatic Patch (C) — minimal file changes, interface-preserving

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
| FuchsianGroup class | `poincare_utils.py` | Add |
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

The `ouroboros_distance()` signature is **unchanged**:
```python
def ouroboros_distance(
    u, v, analogy_mode=False, theta=0.85, sigma=0.15, eps=1e-7
) -> tuple[float, bool]
```

Internal change: `poincare_distance(u, -v)` → `FuchsianGroup.quotient_distance(u, v)`.
`sigma` gains `"auto"` option for adaptive calibration.

## Component Designs

### 1. FuchsianGroup

```
class FuchsianGroup:
    __init__(dim, num_generators=None)
        dim=2: 2 generators (antipodal + π/2 rotation)
        dim=d: 2d coordinate reflection generators
        dim=3: Mostow rigidity annotations

    generators() → list[Callable]
        Each generator: np.ndarray → np.ndarray

    orbit(v, max_depth=2) → list[np.ndarray]
        Word length 0..max_depth, deduplicated by distance epsilon
        max_depth enables GPT-5.4's "generator word length ablation"

    quotient_distance(u, v) → float
        inf_{γv in orbit(v)} d_H(u, γv)
```

### 2. Ollivier-Ricci Curvature (Self-Implemented)

```
ollivier_ricci_curvature(G, a, b, embeddings=None) → float
    - Uniform distribution over 1-hop neighbors
    - Cost matrix: poincare_distance between neighbor pairs
    - Optimal transport: scipy.optimize.linear_sum_assignment
    - κ(a,b) = 1 - W₁(μₐ, μᵦ) / d(a,b)

compute_ricci_flow(G, embeddings, iterations=10, step=0.1)
    → dict[edge, list[float]]
    - Per-iteration: compute curvature → adjust edge weights
    - Convergence: curvature variance < epsilon

detect_neck_pinch(curvature_map, threshold=0.5)
    → list[tuple[node, node, float]]
    - Edges with positive curvature > threshold
    - These are geometric bottlenecks created by wormholes
```

### 3. Adaptive Sigma

```
adaptive_sigma(embeddings, theta=0.85) → float
    - Compute pairwise distances among boundary nodes (||x|| > theta)
    - sigma = clamp(1.0 / median_distance, 0.05, 0.30)
    - Dense boundary → lower sigma, sparse → higher sigma

ouroboros_distance gains sigma="auto" option
```

### 4. Verification Script

`scripts/verify_ouroboros.py` — independent of evolution loop.

**6 Metrics (algebraic + differential-geometric):**

| # | Metric | Type | Target |
|---|--------|------|--------|
| 1 | Group invariance violation rate | Algebraic | 0% |
| 2 | Triangle inequality violation rate | Algebraic | 0% |
| 3 | Antipodal dependency rate | Algebraic | High = improvement |
| 4 | Curvature convergence (variance after Ricci flow) | Diff-geom | < 0.01 |
| 5 | Neck pinch count (positive curvature spikes) | Diff-geom | 0 |
| 6 | Injectivity radius distribution | Diff-geom | Within [0.5, 3.0] |

**Execution modes:**
```bash
python scripts/verify_ouroboros.py --checkpoint <path>
python scripts/verify_ouroboros.py --sweep-depth 0,1,2,3 --sweep-sigma 0.05,0.10,0.15,0.20
python scripts/verify_ouroboros.py --eval-only
```

**Output:** PASS/FAIL + `results/ouroboros_verification.json`

### 5. Eval Set Reinforcement

Add to `eval_set.py`:
- 5 Level-2-only queries (no direct triple in Level 1)
  - e.g., `("fur", "PartOf", "cat")`, `("wheel", "PartOf", "car")`
- 3 Level-4 cross-domain queries
  - e.g., `("gravity", "AnalogousTo", "price")`
- Reverse triples in EVAL_KNOWLEDGE
  - e.g., `("electron", "PartOf", "atom")`

### 6. inference_engine.py Integration

Interface-preserving changes only:
- `__init__`: Create `FuchsianGroup` instance (dim auto-detected from embeddings)
- `_level2_multipath`: Fix `relation` variable scope (explicit parameter instead of closure)
- All imports unchanged

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
| poincare_utils.py grows to ~300 lines | Post-Phase 4 refactor to package structure |
| Orbit explosion at high max_depth | Deduplication + capped orbit size |
| Ollivier curvature slow on large graphs | Verification script is independent, not in evolution loop |

## Future Work (Annotated in Code)

- Refactor to `tecs/inference/geometry/` package (Approach B)
- Teichmüller space exploration for dim=2
- Full Kleinian group implementation for dim=3
- Integration of verification into evolution loop (per-phase-transition)
