# Ouroboros Implementation Guide

## 1. FuchsianGroup Generator Design

The `FuchsianGroup` class constructs explicit generators for the discrete isometry group Gamma acting on the Poincare disk/ball.

**dim = 2:** Two Moebius transforms are used:
- g1: rotation by pi (z -> -z), which identifies antipodal boundary regions
- g2: hyperbolic translation with parameter t = ln(3), implemented as a Moebius addition with translation vector a = tanh(t/2) * e1

These two generators and their inverses produce a free group whose orbit approximates the Fuchsian identification.

**dim = d (general):** 2d generators are constructed:
- d coordinate reflections: x_i -> -x_i (implemented as Moebius transforms)
- d Moebius additions along each coordinate axis with translation parameter t = ln(3)

**dim = 3 (Mostow-rigid path):** Same generator scheme as general dim, but Mostow rigidity guarantees the resulting quotient geometry is unique up to isometry. Use `FuchsianGroup(dim=3)`. See `docs/ouroboros/THEORY.md` Section 5 for theoretical justification.

## 2. Quotient Distance Algorithm

The quotient distance computes:

```
d_M([x], [y]) = inf_{gamma in Gamma} d_H(x, gamma(y))
```

Since Gamma is infinite, this is approximated via orbit enumeration:

1. **Orbit BFS:** Generate the orbit of y under Gamma up to word length `max_depth`. At depth k, apply each generator (and inverse) to all points from depth k-1.
2. **Deduplication:** Points within Poincare distance < 0.01 of an existing orbit point are discarded (prevents exponential blowup from redundant group words).
3. **Cap:** The orbit is capped at 50 points regardless of depth.
4. **Minimum:** Return the minimum d_H(x, gamma_y) over all orbit points gamma_y.

The orbit BFS is the computational bottleneck. For max_depth=2 in dim=2 (4 generators + inverses = 8), the raw orbit has up to 1 + 8 + 64 = 73 points before deduplication, typically reduced to ~30-50 after.

## 3. Ollivier-Ricci Curvature

Ollivier-Ricci curvature kappa(a, b) measures whether neighbors of a and neighbors of b are closer or farther than a and b themselves:

```
kappa(a, b) = 1 - W_1(mu_a, mu_b) / d(a, b)
```

where mu_a and mu_b are uniform distributions over the 1-hop neighbors of a and b in the knowledge graph.

**Wasserstein-1 computation:** Uses the optimal transport formulation via `scipy.optimize.linear_sum_assignment` on the pairwise distance matrix between neighbors of a and neighbors of b. When neighbor sets have unequal sizes, dummy nodes are added with distance equal to the diameter estimate (MAX_RADIUS), ensuring the assignment is well-defined.

**Interpretation:**
- kappa > 0: positive curvature, neighbors are closer than expected (cluster-like)
- kappa < 0: negative curvature, neighbors are farther than expected (tree-like)
- kappa ~ 0: flat

The mean curvature over all edges provides a global diagnostic for how the Fuchsian quotient reshapes the graph geometry.

## 4. Adaptive Sigma

The sigma parameter controls how much the quotient distance compresses boundary-to-boundary connections:

```
d_ouroboros(x, y) = d_quotient(x, y) * sigma  (when both ||x||, ||y|| > theta)
```

**Adaptive computation:**
1. Identify all boundary nodes: {v : ||v|| > theta}
2. Compute pairwise quotient distances among boundary nodes
3. Take the median boundary distance m
4. Set sigma = clamp(1/m, 0.05, 0.30)

This is a **preprocessing step** computed once before evaluation. The `ouroboros_distance` function signature does not change -- sigma is stored as a module-level parameter.

**Rationale:** If boundary nodes are already close in quotient space (small m), sigma should be large (less additional compression needed). If they are far (large m), sigma should be small (more compression).

## 5. Parameter Tuning Guide

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `theta` | 0.85 | [0.7, 0.95] | Boundary norm threshold. Lower = more nodes qualify as boundary = more wormhole connections. Higher = stricter, fewer wormholes. |
| `sigma` | auto (or 0.15) | [0.05, 0.30] | Compression ratio for boundary-to-boundary quotient distances. Lower = stronger compression = more analogy shortcuts. Higher = weaker compression. |
| `max_depth` | 2 | [1, 4] | Maximum word length in orbit BFS. Higher = better approximation of true infimum, but O(generators^depth) cost. Diminishing returns past 3. |
| `TAU` | 3.0 | [1.5, 5.0] | Single-hop distance pruning threshold. Lower = more aggressive pruning = fewer hallucination paths but may lose valid connections. |
| `MAX_RADIUS` | 12.0 | [8.0, 20.0] | Cognitive horizon. Paths exceeding this total distance are considered unreachable. Also used as dummy-node distance in Wasserstein computation. |

**Recommended starting point:** Use defaults (theta=0.85, sigma=auto, max_depth=2, TAU=3.0). If analogy scores are too low, decrease theta to 0.80. If hallucination rates increase, increase TAU to 4.0. For dim >= 3, max_depth=2 is usually sufficient due to Mostow rigidity stabilizing the orbit structure.
