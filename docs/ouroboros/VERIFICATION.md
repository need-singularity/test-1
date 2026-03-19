# Ouroboros Verification Protocol

## 1. The 6 Metrics

| Metric | Definition | PASS Criterion | Interpretation |
|--------|-----------|----------------|----------------|
| **multihop_accuracy** | Fraction of 3-hop inference queries answered correctly via BFS on the knowledge graph. | >= 0.38 | Measures basic reasoning capability. Should not regress from baseline. |
| **concept_coherence** | Mean cosine similarity between a node's embedding and the centroid of its semantic cluster. | >= 0.55 | High = nodes are well-grouped by meaning. Collapse (e.g., 0.01) indicates embedding degeneration. |
| **analogy_score** | Fraction of cross-domain analogy pairs where d_M(a, b) < TAU (reachable via quotient distance). | >= 0.65 | The primary Ouroboros metric. Low = quotient is not connecting analogous boundary nodes. |
| **hallucination_rate** | Fraction of non-analogous cross-domain pairs incorrectly connected (d_M < TAU). | <= 0.05 | False positive rate. High = the wormholes are too permissive. |
| **injectivity_radius** | Minimum distance from any point to its nearest non-trivial orbit image: min_x min_{gamma != e} d_H(x, gamma(x)). | >= 0.3 | Geometric health check. See Section 3 below. |
| **mean_curvature** | Mean Ollivier-Ricci curvature over all edges in the knowledge graph. | in [-0.30, 0.00] | Mildly negative = healthy hyperbolic structure. Strongly negative = fragmented. Positive = degenerate (nearly Euclidean). |

**Overall PASS:** All 6 metrics must satisfy their criteria simultaneously.

## 2. verify_ouroboros.py Usage

```bash
# Full pipeline: build graph, compute Fuchsian orbits, evaluate all 6 metrics
python scripts/verify_ouroboros.py

# Eval-only: skip graph construction, load from checkpoint
python scripts/verify_ouroboros.py --eval-only

# Load a specific checkpoint
python scripts/verify_ouroboros.py --checkpoint results/ouroboros_checkpoint_v2.pkl

# Sweep max_depth values [1, 2, 3, 4] and report metric sensitivity
python scripts/verify_ouroboros.py --sweep-depth

# Sweep sigma values [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
python scripts/verify_ouroboros.py --sweep-sigma
```

Output is written to `results/ouroboros_verification.json` with structure:

```json
{
  "timestamp": "2026-03-20T...",
  "params": {"theta": 0.85, "sigma": 0.15, "max_depth": 2, "dim": 2},
  "metrics": {
    "multihop_accuracy": 0.42,
    "concept_coherence": 0.61,
    "analogy_score": 0.72,
    "hallucination_rate": 0.03,
    "injectivity_radius": 0.45,
    "mean_curvature": -0.18
  },
  "pass": true
}
```

## 3. Injectivity Radius Interpretation

The injectivity radius r_inj is the radius of the largest ball around any point that contains no identified (quotient-equivalent) copies. It measures how "tight" the Fuchsian wrapping is.

- **r_inj too small (< 0.3):** The fundamental domain is too small. Too many wormholes are created, flooding the graph with spurious shortcuts. Hallucination rate will spike. Fix: reduce `max_depth`, increase `theta`, or use fewer generators.
- **r_inj too large (> 2.0):** The Fuchsian group acts too sparsely. The quotient is nearly identical to the open disk -- no wormhole effect. Analogy score will remain low. Fix: increase `max_depth` or decrease `theta`.
- **Sweet spot (0.3 - 1.5):** Wormholes exist but are selective. Cross-domain analogies are enabled without flooding.

## 4. Known Limitations

**Finite orbit approximation.** The true quotient distance d_M([x],[y]) = inf over all of Gamma, but we only enumerate orbit points up to word length `max_depth`. This means:
- The computed distance is an upper bound on the true quotient distance.
- A small fraction of valid analogies may be missed (false negatives).
- Expected violation rate: 2-5% of analogy pairs may fail that would pass with deeper enumeration.

**Ollivier curvature on graphs vs smooth Ricci curvature.** The Ollivier-Ricci curvature is a discrete analogue of Ricci curvature defined on metric-measure spaces. On finite graphs, it captures coarse geometric properties but does not converge to smooth Ricci curvature in any formal limit. The mean_curvature metric should be interpreted as a diagnostic proxy, not a rigorous curvature measurement. In particular:
- Graph topology (degree distribution, clustering) affects Ollivier curvature independently of the underlying metric.
- Curvature values are not directly comparable across graphs with different densities.

**Numerical precision near boundary.** For ||x|| > 0.999, the Poincare distance computation suffers from floating-point cancellation in the denominator (1 - ||x||^2). Points are clamped to ||x|| <= 1 - 1e-6 to prevent NaN, but distances for very-near-boundary points have reduced precision (~3-4 significant digits instead of ~15).

**Deduplication threshold sensitivity.** The orbit deduplication threshold (0.01 in Poincare distance) is a heuristic. In high dimensions (d >= 10), this threshold may be too aggressive, collapsing genuinely distinct orbit points. For high-dimensional experiments, consider reducing to 0.001.
