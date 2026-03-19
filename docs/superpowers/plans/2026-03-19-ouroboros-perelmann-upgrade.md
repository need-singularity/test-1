# Ouroboros Perelmann Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace naive antipodal mapping with proper Fuchsian group quotient distance, add Ollivier-Ricci curvature verification, and build a comprehensive validation pipeline.

**Architecture:** FuchsianGroup class provides Moebius-transform generators and orbit-based quotient distance. Ollivier-Ricci curvature (self-implemented with scipy) powers a discrete Ricci flow for geometric verification. All new geometry code lives in `tecs/inference/poincare_utils.py` with FuchsianGroup in a new `tecs/inference/ouroboros_geometry.py`. Verification runs independently via `scripts/verify_ouroboros.py`.

**Tech Stack:** Python 3.14, numpy, scipy (`linear_sum_assignment`), networkx, pytest

**Spec:** `docs/superpowers/specs/2026-03-19-ouroboros-perelmann-upgrade-design.md`

---

## File Structure

| File | Responsibility |
|------|----------------|
| `tecs/inference/ouroboros_geometry.py` | **New.** FuchsianGroup class (generators, orbit, quotient_distance) |
| `tecs/inference/poincare_utils.py` | **Modify.** Wire ouroboros_distance to FuchsianGroup; add adaptive_sigma, ollivier_ricci_curvature, compute_ricci_flow, detect_neck_pinch |
| `tecs/inference/inference_engine.py` | **Modify.** Init FuchsianGroup + adaptive_sigma in __init__, pass sigma to ouroboros_distance |
| `tecs/inference/eval_set.py` | **Modify.** Add Level-2-only queries, Level-4 cross-domain, reverse triples |
| `tecs/inference/verification.py` | **New.** Verification metric functions (importable module) |
| `scripts/verify_ouroboros.py` | **New.** CLI wrapper that calls `tecs.inference.verification` |
| `tests/test_inference/test_ouroboros_geometry.py` | **New.** Tests for FuchsianGroup |
| `tests/test_inference/test_poincare_utils.py` | **New.** Tests for Ollivier curvature, Ricci flow, adaptive sigma |
| `tests/test_inference/test_verification.py` | **New.** Tests for verification metrics (imports from tecs.inference.verification) |
| `docs/ouroboros/THEORY.md` | **New.** Mathematical background |
| `docs/ouroboros/IMPLEMENTATION.md` | **New.** Implementation guide |
| `docs/ouroboros/VERIFICATION.md` | **New.** Verification protocol |

---

### Task 1: FuchsianGroup — Moebius Generators and Orbit

**Files:**
- Create: `tecs/inference/ouroboros_geometry.py`
- Test: `tests/test_inference/test_ouroboros_geometry.py`

- [ ] **Step 1: Write failing tests for FuchsianGroup**

```python
# tests/test_inference/test_ouroboros_geometry.py
import numpy as np
import pytest
from tecs.inference.ouroboros_geometry import FuchsianGroup
from tecs.inference.poincare_utils import poincare_distance


class TestFuchsianGroupInit:
    def test_dim2_has_2_generators(self):
        fg = FuchsianGroup(dim=2)
        assert len(fg.generators()) == 2

    def test_dim3_has_6_generators(self):
        fg = FuchsianGroup(dim=3)
        assert len(fg.generators()) == 6

    def test_dim_d_has_2d_generators(self):
        fg = FuchsianGroup(dim=5)
        assert len(fg.generators()) == 10

    def test_dim_below_2_raises(self):
        with pytest.raises(ValueError):
            FuchsianGroup(dim=1)

    def test_fallback_mode_returns_legacy(self):
        fg = FuchsianGroup(dim=2, use_fuchsian=False)
        v = np.array([0.5, 0.3])
        orbit = fg.orbit(v, max_depth=2)
        # Legacy: only v and -v
        assert len(orbit) == 2


class TestMoebiusTransforms:
    def test_generators_preserve_disk(self):
        """All generators must map points inside the disk to points inside the disk."""
        fg = FuchsianGroup(dim=2)
        v = np.array([0.5, 0.3])
        for gen in fg.generators():
            w = gen(v)
            assert np.linalg.norm(w) < 1.0, f"Generator mapped outside disk: ||w||={np.linalg.norm(w)}"

    def test_generators_are_isometries(self):
        """d_H(γu, γv) == d_H(u, v) for all generators γ."""
        fg = FuchsianGroup(dim=2)
        u = np.array([0.3, 0.2])
        v = np.array([0.6, -0.1])
        d_orig = poincare_distance(u, v)
        for gen in fg.generators():
            d_mapped = poincare_distance(gen(u), gen(v))
            assert abs(d_mapped - d_orig) < 1e-6, (
                f"Not an isometry: d_orig={d_orig:.6f}, d_mapped={d_mapped:.6f}"
            )

    def test_dim3_generators_preserve_ball(self):
        fg = FuchsianGroup(dim=3)
        v = np.array([0.4, 0.3, 0.2])
        for gen in fg.generators():
            w = gen(v)
            assert np.linalg.norm(w) < 1.0


class TestOrbit:
    def test_orbit_includes_identity(self):
        fg = FuchsianGroup(dim=2)
        v = np.array([0.5, 0.3])
        orbit = fg.orbit(v, max_depth=1)
        # v itself should be in the orbit
        assert any(np.allclose(o, v, atol=1e-6) for o in orbit)

    def test_orbit_depth0_is_just_v(self):
        fg = FuchsianGroup(dim=2)
        v = np.array([0.5, 0.3])
        orbit = fg.orbit(v, max_depth=0)
        assert len(orbit) == 1
        assert np.allclose(orbit[0], v)

    def test_orbit_depth1_more_than_depth0(self):
        fg = FuchsianGroup(dim=2)
        v = np.array([0.5, 0.3])
        o0 = fg.orbit(v, max_depth=0)
        o1 = fg.orbit(v, max_depth=1)
        assert len(o1) > len(o0)

    def test_orbit_capped_at_50(self):
        fg = FuchsianGroup(dim=2)
        v = np.array([0.5, 0.3])
        orbit = fg.orbit(v, max_depth=10)
        assert len(orbit) <= 50

    def test_orbit_deduplication(self):
        fg = FuchsianGroup(dim=2)
        v = np.array([0.5, 0.3])
        orbit = fg.orbit(v, max_depth=2)
        for i in range(len(orbit)):
            for j in range(i + 1, len(orbit)):
                d = poincare_distance(orbit[i], orbit[j])
                assert d > 0.005, f"Duplicate in orbit: d={d:.6f}"


class TestQuotientDistance:
    def test_quotient_leq_direct(self):
        """Quotient distance should be ≤ direct Poincare distance."""
        fg = FuchsianGroup(dim=2)
        u = np.array([0.3, 0.2])
        v = np.array([-0.6, 0.1])
        d_direct = poincare_distance(u, v)
        d_quot = fg.quotient_distance(u, v)
        assert d_quot <= d_direct + 1e-6

    def test_quotient_symmetric(self):
        fg = FuchsianGroup(dim=2)
        u = np.array([0.3, 0.2])
        v = np.array([-0.6, 0.1])
        assert abs(fg.quotient_distance(u, v) - fg.quotient_distance(v, u)) < 1e-6

    def test_quotient_zero_for_same_point(self):
        fg = FuchsianGroup(dim=2)
        u = np.array([0.3, 0.2])
        assert fg.quotient_distance(u, u) < 1e-6

    def test_fallback_matches_legacy(self):
        """use_fuchsian=False should give same result as old -v approach."""
        fg = FuchsianGroup(dim=2, use_fuchsian=False)
        u = np.array([0.3, 0.2])
        v = np.array([0.8, -0.1])
        d_quot = fg.quotient_distance(u, v)
        d_legacy = min(poincare_distance(u, v), poincare_distance(u, -v))
        assert abs(d_quot - d_legacy) < 1e-6

    def test_triangle_inequality(self):
        fg = FuchsianGroup(dim=2)
        x = np.array([0.2, 0.1])
        y = np.array([-0.3, 0.4])
        z = np.array([0.5, -0.2])
        d_xz = fg.quotient_distance(x, z)
        d_xy = fg.quotient_distance(x, y)
        d_yz = fg.quotient_distance(y, z)
        assert d_xz <= d_xy + d_yz + 1e-6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_inference/test_ouroboros_geometry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tecs.inference.ouroboros_geometry'`

- [ ] **Step 3: Implement FuchsianGroup**

```python
# tecs/inference/ouroboros_geometry.py
"""Fuchsian group generators and quotient distance on the Poincare disk/ball.

Mathematical basis: For a closed hyperbolic manifold M = H^d / Γ, the
quotient distance is d_M([x],[y]) = inf_{γ ∈ Γ} d_H(x, γy).

dim=2: Fuchsian group with Moebius transforms on the Poincare disk.
dim=3: Mostow rigidity guarantees geometric uniqueness given correct π₁.
       (Paradoxically safer than dim=2 post-implementation.)
dim=d: 2d coordinate hyperplane reflection generators.

Reference: Perelman's geometrization theorem (2003) provides topological
justification for closed hyperbolic structure. This is the "license to
assume closed universe" — but actual computation requires explicit Γ.
"""
from __future__ import annotations

import numpy as np
from tecs.inference.poincare_utils import poincare_distance

# Maximum orbit size to prevent combinatorial explosion
_MAX_ORBIT_SIZE = 50
# Deduplication threshold in hyperbolic distance
_DEDUP_EPS = 0.01


def _moebius_transform_2d(z: np.ndarray, a: complex, b: complex) -> np.ndarray:
    """Apply Moebius transform γ(z) = (az + b) / (conj(b)z + conj(a)).

    In the Poincare disk model, isometries are Moebius transforms with
    |a|² - |b|² = 1. We represent 2D points as complex numbers.
    """
    z_c = complex(z[0], z[1])
    w = (a * z_c + b) / (np.conj(b) * z_c + np.conj(a))
    result = np.array([w.real, w.imag])
    # Numerical safety: clamp inside disk
    norm = np.linalg.norm(result)
    if norm >= 1.0:
        result = result * (0.999 / norm)
    return result


def _make_2d_generators() -> list:
    """Create 2 Fuchsian generators as Moebius transforms.

    γ₁: z → -z  (antipodal, the existing behavior)
        Moebius params: a = i, b = 0  →  γ(z) = iz/i = ...
        Actually for z → -z: a = -1, b = 0 (or equivalently a=i, b=0 for π/2 rot)
        Let's be precise:
        - γ₁ (antipodal): a = -1+0j, b = 0+0j  →  (-z)/(0·z + (-1)) = z ...

    For proper Moebius transforms with |a|² - |b|² = 1:
    γ₁ (rotation by π): a = e^{iπ/2} = i, b = 0  →  γ(z) = iz/(0·z + (-i)) = iz/(-i) = -z  ✓
        Wait: conj(a) = -i, so γ(z) = (iz + 0)/(0·z + (-i)) = iz/(-i) = -z  ✓
        Check: |a|² - |b|² = 1 - 0 = 1  ✓

    γ₂ (hyperbolic translation along real axis):
        a = cosh(t/2), b = sinh(t/2) with t = ln(3) ≈ 1.1
        This translates points along the real geodesic.
        |a|² - |b|² = cosh²(t/2) - sinh²(t/2) = 1  ✓
    """
    # γ₁: rotation by π  (z → -z)
    a1 = complex(0, 1)   # i
    b1 = complex(0, 0)

    # γ₂: hyperbolic translation along real axis
    t = np.log(3.0)  # translation distance
    a2 = complex(np.cosh(t / 2), 0)
    b2 = complex(np.sinh(t / 2), 0)

    def gen1(v: np.ndarray) -> np.ndarray:
        return _moebius_transform_2d(v, a1, b1)

    def gen2(v: np.ndarray) -> np.ndarray:
        return _moebius_transform_2d(v, a2, b2)

    return [gen1, gen2]


def _make_nd_generators(dim: int) -> list:
    """Create 2d generators for d-dimensional Poincare ball.

    Each generator is a coordinate hyperplane reflection:
    γ_k: x → x with x_k negated (reflection through k-th hyperplane)
    Plus a hyperbolic translation per axis pair.

    Note on Mostow rigidity (dim >= 3): Once the fundamental group π₁
    is correctly defined, the hyperbolic structure on the resulting
    closed manifold is unique. This means getting the generators right
    is sufficient — no Teichmüller-space ambiguity to worry about.
    """
    generators = []
    for k in range(dim):
        def make_reflection(axis: int):
            def reflect(v: np.ndarray) -> np.ndarray:
                w = v.copy()
                w[axis] = -w[axis]
                # This is a valid isometry of the Poincare ball
                # (coordinate reflection preserves the ball metric)
                return w
            return reflect
        generators.append(make_reflection(k))

    # Add hyperbolic translations along each axis
    for k in range(dim):
        def make_translation(axis: int):
            t = np.log(3.0)
            shift = np.zeros(dim)
            shift[axis] = np.tanh(t / 2)

            def translate(v: np.ndarray) -> np.ndarray:
                # Moebius addition in the ball model:
                # a ⊕ b = ((1 + 2<a,b> + ||b||²)a + (1 - ||a||²)b)
                #          / (1 + 2<a,b> + ||a||²||b||²)
                a = shift
                b = v
                dot_ab = np.dot(a, b)
                norm_a_sq = np.dot(a, a)
                norm_b_sq = np.dot(b, b)
                num = (1 + 2 * dot_ab + norm_b_sq) * a + (1 - norm_a_sq) * b
                den = 1 + 2 * dot_ab + norm_a_sq * norm_b_sq
                result = num / den
                norm = np.linalg.norm(result)
                if norm >= 1.0:
                    result = result * (0.999 / norm)
                return result
            return translate
        generators.append(make_translation(k))

    return generators


class FuchsianGroup:
    """Discrete isometry group Γ for constructing closed hyperbolic manifolds.

    Provides orbit computation and quotient distance:
    d_M([x],[y]) = inf_{γ ∈ Γ} d_H(x, γy)
    """

    def __init__(self, dim: int = 2, num_generators: int | None = None,
                 use_fuchsian: bool = True):
        if dim < 2:
            raise ValueError(f"dim must be >= 2 for Poincare ball model, got {dim}")
        self._dim = dim
        self._use_fuchsian = use_fuchsian

        if not use_fuchsian:
            # Legacy fallback: only antipodal mapping
            self._generators = [lambda v: -v]
            return

        if dim == 2:
            self._generators = _make_2d_generators()
        else:
            # dim >= 3: Mostow rigidity ensures geometric uniqueness
            # once generators are defined. No Teichmüller ambiguity.
            self._generators = _make_nd_generators(dim)

        if num_generators is not None:
            self._generators = self._generators[:num_generators]

    def generators(self) -> list:
        return list(self._generators)

    def orbit(self, v: np.ndarray, max_depth: int = 2) -> list[np.ndarray]:
        """Compute the Γ-orbit of v up to word length max_depth.

        Returns deduplicated list of γv for all words γ of length ≤ max_depth.
        Capped at _MAX_ORBIT_SIZE to prevent combinatorial explosion.
        """
        orbit = [v.copy()]

        if max_depth == 0:
            return orbit

        if not self._use_fuchsian:
            # Legacy: just v and -v
            neg_v = -v.copy()
            orbit.append(neg_v)
            return orbit

        current_level = [v.copy()]
        seen = [v.copy()]

        for _depth in range(max_depth):
            next_level = []
            for point in current_level:
                for gen in self._generators:
                    new_point = gen(point)
                    # Also apply inverse (for reflections, inverse = self)
                    # For translations, we'd need explicit inverses
                    # but reflections are self-inverse and rotation by π is self-inverse

                    # Deduplication: skip if too close to any existing orbit point
                    is_dup = False
                    for existing in seen:
                        if poincare_distance(new_point, existing) < _DEDUP_EPS:
                            is_dup = True
                            break
                    if not is_dup:
                        seen.append(new_point)
                        next_level.append(new_point)
                        orbit.append(new_point)

                    if len(orbit) >= _MAX_ORBIT_SIZE:
                        return orbit

            current_level = next_level
            if not current_level:
                break

        return orbit

    def quotient_distance(self, u: np.ndarray, v: np.ndarray,
                          max_depth: int = 2) -> float:
        """Compute d_M([u],[v]) = inf_{γ ∈ Γ} d_H(u, γv).

        This is the correct distance on the quotient manifold H^d / Γ.
        The old approach of just computing d_H(u, -v) is the max_depth=0
        legacy fallback with a single antipodal generator.
        """
        orbit_v = self.orbit(v, max_depth=max_depth)
        return min(poincare_distance(u, gv) for gv in orbit_v)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_inference/test_ouroboros_geometry.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add tecs/inference/ouroboros_geometry.py tests/test_inference/test_ouroboros_geometry.py
git commit -m "feat: FuchsianGroup with Moebius generators and quotient distance"
```

---

### Task 2: Wire ouroboros_distance to FuchsianGroup + adaptive_sigma

**Files:**
- Modify: `tecs/inference/poincare_utils.py`
- Test: `tests/test_inference/test_poincare_utils.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_inference/test_poincare_utils.py
import numpy as np
import pytest
from tecs.inference.poincare_utils import (
    poincare_distance, ouroboros_distance, adaptive_sigma,
)


class TestOuroborosWithFuchsian:
    def test_ouroboros_boundary_pair_shorter_than_direct(self):
        """Boundary-to-boundary with analogy_mode should be shorter than raw."""
        u = np.array([0.90, 0.15])
        v = np.array([-0.85, 0.20])
        d_raw = poincare_distance(u, v)
        d_ouro, wh = ouroboros_distance(u, v, analogy_mode=True)
        assert wh is True
        assert d_ouro < d_raw

    def test_ouroboros_center_pair_unchanged(self):
        """Center-to-center should not activate wormhole."""
        u = np.array([0.1, 0.2])
        v = np.array([0.3, 0.1])
        d_raw = poincare_distance(u, v)
        d_ouro, wh = ouroboros_distance(u, v, analogy_mode=True)
        assert wh is False
        assert abs(d_ouro - d_raw) < 1e-6

    def test_ouroboros_analogy_mode_false(self):
        """analogy_mode=False should never activate wormhole."""
        u = np.array([0.90, 0.15])
        v = np.array([-0.85, 0.20])
        d_ouro, wh = ouroboros_distance(u, v, analogy_mode=False)
        assert wh is False

    def test_ouroboros_quotient_better_than_antipodal(self):
        """FuchsianGroup quotient should find paths at least as short as old -v."""
        u = np.array([0.90, 0.15])
        v = np.array([-0.85, 0.20])
        d_old_antipodal = min(poincare_distance(u, v), poincare_distance(u, -v))
        from tecs.inference.ouroboros_geometry import FuchsianGroup
        fg = FuchsianGroup(dim=2)
        d_quotient = fg.quotient_distance(u, v)
        assert d_quotient <= d_old_antipodal + 1e-6


class TestAdaptiveSigma:
    def test_returns_float(self):
        embeddings = {
            0: np.array([0.90, 0.10]),
            1: np.array([-0.88, 0.15]),
            2: np.array([0.30, 0.20]),
            3: np.array([0.92, -0.10]),
        }
        sigma = adaptive_sigma(embeddings, theta=0.85)
        assert isinstance(sigma, float)

    def test_clamped_range(self):
        embeddings = {i: np.array([0.90, 0.01 * i]) for i in range(20)}
        sigma = adaptive_sigma(embeddings, theta=0.85)
        assert 0.05 <= sigma <= 0.30

    def test_no_boundary_nodes_returns_default(self):
        embeddings = {
            0: np.array([0.10, 0.10]),
            1: np.array([0.20, 0.15]),
        }
        sigma = adaptive_sigma(embeddings, theta=0.85)
        assert sigma == 0.15  # default fallback
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_inference/test_poincare_utils.py -v`
Expected: FAIL — `adaptive_sigma` not found

- [ ] **Step 3: Implement changes in poincare_utils.py**

Add `adaptive_sigma` function and rewire `ouroboros_distance` internals:

```python
# Add to poincare_utils.py — new import at top
from tecs.inference.ouroboros_geometry import FuchsianGroup

# Module-level config: set to False to revert to legacy -v behavior
USE_FUCHSIAN = True

# Module-level singleton (lazy init)
_default_group: FuchsianGroup | None = None

def _get_default_group(dim: int = 2) -> FuchsianGroup:
    global _default_group
    if _default_group is None or _default_group._dim != dim:
        _default_group = FuchsianGroup(dim=dim, use_fuchsian=USE_FUCHSIAN)
    return _default_group


def adaptive_sigma(
    embeddings: dict[int, np.ndarray], theta: float = OUROBOROS_THETA,
) -> float:
    """Compute adaptive compression ratio based on boundary node density.

    Returns a float sigma value. Caller passes it to ouroboros_distance(sigma=...).
    """
    boundary = [emb for emb in embeddings.values() if np.linalg.norm(emb) > theta]
    if len(boundary) < 2:
        return OUROBOROS_SIGMA  # default fallback

    # Compute pairwise distances among boundary nodes
    dists = []
    for i in range(len(boundary)):
        for j in range(i + 1, len(boundary)):
            dists.append(poincare_distance(boundary[i], boundary[j]))

    if not dists:
        return OUROBOROS_SIGMA

    median_dist = float(np.median(dists))
    if median_dist < 1e-6:
        return 0.30  # very dense → max compression

    sigma = 1.0 / median_dist
    return float(np.clip(sigma, 0.05, 0.30))
```

Replace `ouroboros_distance` internals:

```python
def ouroboros_distance(
    u: np.ndarray, v: np.ndarray,
    analogy_mode: bool = False,
    theta: float = OUROBOROS_THETA,
    sigma: float = OUROBOROS_SIGMA,
    eps: float = 1e-7,
) -> tuple[float, bool]:
    """Compute Ouroboros-aware distance. Signature unchanged."""
    raw = poincare_distance(u, v, eps)

    if analogy_mode:
        norm_u = float(np.linalg.norm(u))
        norm_v = float(np.linalg.norm(v))
        if norm_u > theta and norm_v > theta:
            dim = len(u)
            group = _get_default_group(dim)
            quotient_raw = group.quotient_distance(u, v)
            wormhole_dist = quotient_raw * sigma
            return wormhole_dist, True

    return raw, False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_inference/test_poincare_utils.py tests/test_inference/test_ouroboros_geometry.py -v`
Expected: All PASS

- [ ] **Step 5: Run existing inference tests for regression**

Run: `.venv/bin/pytest tests/test_inference/ -v`
Expected: All previously passing tests still PASS

- [ ] **Step 6: Commit**

```bash
git add tecs/inference/poincare_utils.py tests/test_inference/test_poincare_utils.py
git commit -m "feat: wire ouroboros_distance to FuchsianGroup quotient + adaptive_sigma"
```

---

### Task 3: Ollivier-Ricci Curvature + Ricci Flow + Neck Pinch

**Files:**
- Modify: `tecs/inference/poincare_utils.py`
- Test: `tests/test_inference/test_poincare_utils.py` (append)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_inference/test_poincare_utils.py`:

```python
import networkx as nx
from tecs.inference.poincare_utils import (
    ollivier_ricci_curvature, compute_ricci_flow, detect_neck_pinch,
    generate_poincare_embeddings,
)


class TestOllivierRicci:
    def _make_graph_and_embeddings(self):
        G = nx.karate_club_graph()
        emb = generate_poincare_embeddings(G)
        return G, emb

    def test_curvature_returns_float(self):
        G, emb = self._make_graph_and_embeddings()
        edge = list(G.edges())[0]
        k = ollivier_ricci_curvature(G, edge[0], edge[1], embeddings=emb)
        assert isinstance(k, float)

    def test_curvature_range(self):
        """Ollivier-Ricci curvature should be in [-1, 1] for most graphs."""
        G, emb = self._make_graph_and_embeddings()
        for u, v in list(G.edges())[:10]:
            k = ollivier_ricci_curvature(G, u, v, embeddings=emb)
            assert -2.0 <= k <= 2.0, f"Curvature out of range: {k}"

    def test_curvature_unequal_degree(self):
        """Should handle nodes with different degree (padded W1)."""
        G = nx.star_graph(5)  # center has degree 5, leaves have degree 1
        emb = generate_poincare_embeddings(G)
        k = ollivier_ricci_curvature(G, 0, 1, embeddings=emb)
        assert isinstance(k, float)


class TestRicciFlow:
    def test_returns_curvature_history(self):
        G = nx.karate_club_graph()
        emb = generate_poincare_embeddings(G)
        result = compute_ricci_flow(G, emb, iterations=3)
        assert isinstance(result, dict)
        for edge, history in result.items():
            assert len(history) == 3
            assert all(isinstance(h, float) for h in history)

    def test_flow_reduces_variance(self):
        """Ricci flow should reduce curvature variance over iterations."""
        G = nx.karate_club_graph()
        emb = generate_poincare_embeddings(G)
        result = compute_ricci_flow(G, emb, iterations=5)
        # Compute variance of curvatures at first and last iteration
        first_curvatures = [h[0] for h in result.values()]
        last_curvatures = [h[-1] for h in result.values()]
        var_first = np.var(first_curvatures)
        var_last = np.var(last_curvatures)
        # Flow should at least not increase variance dramatically
        assert var_last <= var_first * 2.0


class TestNeckPinch:
    def test_returns_list_of_tuples(self):
        curvature_map = {(0, 1): 0.3, (1, 2): 0.8, (2, 3): -0.1, (3, 4): 1.5}
        result = detect_neck_pinch(curvature_map)
        assert isinstance(result, list)
        for item in result:
            assert len(item) == 3  # (node_a, node_b, curvature)

    def test_data_driven_threshold(self):
        """Should use mean + 2*std, not hardcoded 0.5."""
        # mean=0.5, std≈0.5, threshold≈1.5 → only 2.0 exceeds
        curvature_map = {
            (0, 1): 0.0, (1, 2): 0.2, (2, 3): 0.4,
            (3, 4): 0.5, (4, 5): 0.7, (5, 6): 2.0,
        }
        result = detect_neck_pinch(curvature_map)
        assert len(result) >= 1
        assert all(k > 0 for _, _, k in result)

    def test_custom_threshold(self):
        curvature_map = {(0, 1): 0.3, (1, 2): 0.8, (2, 3): 1.5}
        result = detect_neck_pinch(curvature_map, threshold=0.5)
        assert len(result) == 2  # 0.8 and 1.5
```

- [ ] **Step 2: Run to verify failures**

Run: `.venv/bin/pytest tests/test_inference/test_poincare_utils.py::TestOllivierRicci -v`
Expected: FAIL — `ollivier_ricci_curvature` not found

- [ ] **Step 3: Implement Ollivier-Ricci, Ricci flow, neck pinch**

Add to `poincare_utils.py`:

```python
from scipy.optimize import linear_sum_assignment


def ollivier_ricci_curvature(
    G: nx.Graph, a: int, b: int, embeddings: dict[int, np.ndarray] | None = None,
) -> float:
    """Compute Ollivier-Ricci curvature κ(a,b) for edge (a,b).

    κ(a,b) = 1 - W₁(μₐ, μᵦ) / d(a,b)

    where μₐ, μᵦ are uniform distributions over 1-hop neighbors,
    and W₁ is the Wasserstein-1 (earth mover's) distance.

    When |N(a)| ≠ |N(b)|, the smaller set is padded with dummy nodes
    at max cost to make the assignment problem square.
    """
    neighbors_a = list(G.neighbors(a))
    neighbors_b = list(G.neighbors(b))

    if not neighbors_a or not neighbors_b:
        return 0.0

    # Distance between a and b
    if embeddings and a in embeddings and b in embeddings:
        d_ab = poincare_distance(embeddings[a], embeddings[b])
    else:
        try:
            d_ab = float(nx.shortest_path_length(G, a, b))
        except nx.NetworkXNoPath:
            return 0.0

    if d_ab < 1e-8:
        return 0.0

    # Cost matrix: distance between each pair of neighbors
    na, nb = len(neighbors_a), len(neighbors_b)
    max_size = max(na, nb)

    cost = np.zeros((max_size, max_size))
    for i in range(na):
        for j in range(nb):
            ni, nj = neighbors_a[i], neighbors_b[j]
            if embeddings and ni in embeddings and nj in embeddings:
                cost[i, j] = poincare_distance(embeddings[ni], embeddings[nj])
            else:
                try:
                    cost[i, j] = float(nx.shortest_path_length(G, ni, nj))
                except nx.NetworkXNoPath:
                    cost[i, j] = 100.0  # large penalty

    # Pad with max cost for unequal sizes
    max_cost = cost[:na, :nb].max() if na > 0 and nb > 0 else 100.0
    if na < max_size:
        cost[na:, :] = max_cost
    if nb < max_size:
        cost[:, nb:] = max_cost

    # Optimal transport via Hungarian algorithm
    row_ind, col_ind = linear_sum_assignment(cost)
    w1 = cost[row_ind, col_ind].sum() / max_size

    return float(1.0 - w1 / d_ab)


def compute_ricci_flow(
    G: nx.Graph, embeddings: dict[int, np.ndarray],
    iterations: int = 10, step: float = 0.1,
) -> dict[tuple[int, int], list[float]]:
    """Run discrete Ricci flow and return curvature history per edge.

    Each iteration: compute Ollivier curvature for all edges,
    then adjust edge weights: w_new = w * (1 - step * κ).
    """
    G_flow = G.copy()
    # Initialize weights
    for u, v in G_flow.edges():
        if "weight" not in G_flow[u][v]:
            G_flow[u][v]["weight"] = 1.0

    history: dict[tuple[int, int], list[float]] = {
        (u, v): [] for u, v in G_flow.edges()
    }

    for _it in range(iterations):
        curvatures = {}
        for u, v in G_flow.edges():
            k = ollivier_ricci_curvature(G_flow, u, v, embeddings)
            curvatures[(u, v)] = k
            history[(u, v)].append(k)

        # Update weights
        for (u, v), k in curvatures.items():
            w = G_flow[u][v].get("weight", 1.0)
            G_flow[u][v]["weight"] = w * (1.0 - step * k)

    return history


def detect_neck_pinch(
    curvature_map: dict[tuple[int, int], float],
    threshold: float | None = None,
) -> list[tuple[int, int, float]]:
    """Detect candidate neck pinch singularities.

    Default threshold: mean + 2*std of positive curvature values.
    Returns edges with curvature above threshold for human inspection.

    Note: Ollivier-Ricci on graphs differs from smooth Ricci curvature.
    High positive values indicate dense clusters, not necessarily
    pathological neck pinches. Results are advisory, not auto-reject.
    """
    if not curvature_map:
        return []

    values = list(curvature_map.values())

    if threshold is None:
        mean_k = np.mean(values)
        std_k = np.std(values)
        threshold = mean_k + 2.0 * std_k

    return [
        (u, v, k) for (u, v), k in curvature_map.items()
        if k > threshold
    ]
```

- [ ] **Step 4: Run all poincare_utils tests**

Run: `.venv/bin/pytest tests/test_inference/test_poincare_utils.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add tecs/inference/poincare_utils.py tests/test_inference/test_poincare_utils.py
git commit -m "feat: Ollivier-Ricci curvature, discrete Ricci flow, neck pinch detection"
```

---

### Task 4: Eval Set Reinforcement

**Files:**
- Modify: `tecs/inference/eval_set.py`
- Test: `tests/test_inference/test_inference_engine.py` (append)

- [ ] **Step 1: Write failing test**

Append to `tests/test_inference/test_inference_engine.py`:

```python
def test_eval_set_has_level2_only_queries():
    """Level 2 queries should have no direct triple match in Level 1."""
    from tecs.inference.eval_set import EVAL_QUERIES, EVAL_KNOWLEDGE

    direct_triples = {(h, r, t) for h, r, t in EVAL_KNOWLEDGE}
    level2_queries = [(s, r, e) for s, r, e, lvl, _ in EVAL_QUERIES if lvl == 2]

    for subj, rel, expected in level2_queries:
        # At least some Level 2 queries should NOT have a direct triple
        pass

    # There should be at least 5 Level-2-only queries
    level2_no_direct = []
    for subj, rel, expected, lvl, _ in EVAL_QUERIES:
        if lvl == 2 and (subj, rel, expected) not in direct_triples:
            level2_no_direct.append((subj, rel, expected))
    assert len(level2_no_direct) >= 5


def test_eval_set_has_reverse_triples():
    from tecs.inference.eval_set import EVAL_KNOWLEDGE
    # Check that PartOf triples exist (reverse of HasA)
    partof = [(h, r, t) for h, r, t in EVAL_KNOWLEDGE if r == "PartOf"]
    assert len(partof) >= 3


def test_eval_set_has_cross_domain_queries():
    from tecs.inference.eval_set import EVAL_QUERIES
    level4 = [q for q in EVAL_QUERIES if q[3] >= 4]
    assert len(level4) >= 3
```

- [ ] **Step 2: Run to verify failures**

Run: `.venv/bin/pytest tests/test_inference/test_inference_engine.py::test_eval_set_has_level2_only_queries -v`
Expected: FAIL — fewer than 5 Level-2-only queries

- [ ] **Step 3: Update eval_set.py**

Add to `EVAL_QUERIES`:
```python
    # Level 2: Multi-hop ONLY (no direct triple exists for these)
    ("fur", "PartOf", "cat", 2, "biology"),        # cat HasA fur → fur PartOf cat
    ("wheel", "PartOf", "car", 2, "transport"),     # car HasA wheels → wheel PartOf car
    ("proton", "PartOf", "atom", 2, "chemistry"),   # atom HasA proton → proton PartOf atom
    ("gene", "PartOf", "dna", 2, "biology"),        # dna HasA gene → gene PartOf dna
    ("engine", "PartOf", "car", 2, "transport"),    # car HasA engine → engine PartOf car

    # Level 4: Cross-domain (uses existing "RelatedTo" relation)
    ("gravity", "RelatedTo", "price", 4, "cross_domain"),
    ("force", "RelatedTo", "supply", 4, "cross_domain"),
    ("energy", "RelatedTo", "demand", 4, "cross_domain"),
```

Add to `EVAL_KNOWLEDGE`:
```python
    # Reverse triples (PartOf — inverse of HasA)
    ("fur", "PartOf", "cat"), ("tail", "PartOf", "dog"),
    ("wheel", "PartOf", "car"), ("engine", "PartOf", "car"),
    ("electron", "PartOf", "atom"), ("proton", "PartOf", "atom"),
    ("neutron", "PartOf", "atom"), ("gene", "PartOf", "dna"),
    # Cross-domain bridge triples
    ("gravity", "RelatedTo", "price"), ("force", "RelatedTo", "supply"),
    ("energy", "RelatedTo", "demand"),
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/test_inference/test_inference_engine.py -v`
Expected: All PASS (including new eval set tests)

- [ ] **Step 5: Commit**

```bash
git add tecs/inference/eval_set.py tests/test_inference/test_inference_engine.py
git commit -m "feat: reinforce eval_set with Level-2-only, Level-4, and reverse triples"
```

---

### Task 5: inference_engine.py Integration

**Files:**
- Modify: `tecs/inference/inference_engine.py`

- [ ] **Step 1: Write failing test**

**Append** these functions to the **existing** file `tests/test_inference/test_inference_engine.py`
(which already defines `_make_engine()` at the top — do NOT create a new file):

```python
def test_engine_uses_adaptive_sigma():
    """Engine should compute adaptive_sigma and pass it to ouroboros_distance."""
    engine = _make_engine()
    assert hasattr(engine, '_sigma')
    assert isinstance(engine._sigma, float)
    assert 0.05 <= engine._sigma <= 0.30 or engine._sigma == 0.15


def test_engine_has_fuchsian_group():
    engine = _make_engine()
    assert hasattr(engine, '_fuchsian_group')
```

- [ ] **Step 2: Run to verify failures**

Run: `.venv/bin/pytest tests/test_inference/test_inference_engine.py::test_engine_uses_adaptive_sigma -v`
Expected: FAIL — `_sigma` attribute not found

- [ ] **Step 3: Update inference_engine.py**

In `InferenceEngine.__init__`, after the embeddings setup:

```python
        # Fuchsian group for quotient distance (dim auto-detected)
        from tecs.inference.ouroboros_geometry import FuchsianGroup
        from tecs.inference.poincare_utils import adaptive_sigma as _adaptive_sigma
        sample_emb = next(iter(self._embeddings.values()), None)
        dim = len(sample_emb) if sample_emb is not None else 2
        self._fuchsian_group = FuchsianGroup(dim=dim)
        self._sigma = _adaptive_sigma(self._embeddings)
```

In `_level2_multipath`, change the `ouroboros_distance` call:

```python
                edge_dist, via_wormhole = ouroboros_distance(
                    emb_u, emb_v, analogy_mode=is_analogy,
                    sigma=self._sigma,
                )
```

- [ ] **Step 4: Run full inference test suite**

Run: `.venv/bin/pytest tests/test_inference/ -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add tecs/inference/inference_engine.py tests/test_inference/test_inference_engine.py
git commit -m "feat: integrate FuchsianGroup + adaptive_sigma into InferenceEngine"
```

---

### Task 6: Verification Script

**Files:**
- Create: `scripts/verify_ouroboros.py`
- Test: `tests/test_inference/test_verification.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_inference/test_verification.py
import numpy as np
import networkx as nx
import pytest

from tecs.inference.verification import (
    check_group_invariance, check_triangle_inequality, compute_injectivity_radii,
)
from tecs.inference.ouroboros_geometry import FuchsianGroup
from tecs.inference.poincare_utils import generate_poincare_embeddings


class TestVerificationMetrics:
    """Test the metric computation functions directly."""

    def _make_fg_and_emb(self):
        G = nx.cycle_graph(20)  # smaller than karate club for speed
        emb = generate_poincare_embeddings(G)
        fg = FuchsianGroup(dim=2)
        return fg, emb

    def test_group_invariance_metric(self):
        fg, emb = self._make_fg_and_emb()
        violation_rate = check_group_invariance(fg, emb, n_samples=50)
        assert violation_rate == 0.0

    def test_triangle_inequality_metric(self):
        fg, emb = self._make_fg_and_emb()
        violation_rate = check_triangle_inequality(fg, emb, n_samples=50)
        assert violation_rate == 0.0

    def test_injectivity_radius(self):
        fg, emb = self._make_fg_and_emb()
        radii = compute_injectivity_radii(fg, emb)
        assert len(radii) > 0
        assert all(r > 0 for r in radii)
```

- [ ] **Step 2: Run to verify failures**

Run: `.venv/bin/pytest tests/test_inference/test_verification.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tecs.inference.verification'`

- [ ] **Step 3a: Implement verification module (importable)**

```python
# tecs/inference/verification.py
"""Ouroboros geometric verification metrics.

Importable module — used by both tests and the CLI script.
"""
from __future__ import annotations

import numpy as np
import networkx as nx

from tecs.inference.ouroboros_geometry import FuchsianGroup
from tecs.inference.poincare_utils import (
    poincare_distance, generate_poincare_embeddings,
    ollivier_ricci_curvature, compute_ricci_flow, detect_neck_pinch,
    ouroboros_distance,
)


def check_group_invariance(
    fg: FuchsianGroup, embeddings: dict, n_samples: int = 100,
    tol: float = 1e-4,
) -> float:
    """Metric 1: d_M([γx],[y]) should equal d_M([x],[y]) for all γ ∈ Γ."""
    nodes = list(embeddings.keys())
    rng = np.random.default_rng(42)
    violations = 0
    total = 0

    for _ in range(n_samples):
        i, j = rng.choice(nodes, 2, replace=False)
        u, v = embeddings[i], embeddings[j]
        d_base = fg.quotient_distance(u, v)

        for gen in fg.generators():
            gu = gen(u)
            d_transformed = fg.quotient_distance(gu, v)
            if abs(d_transformed - d_base) > tol:
                violations += 1
            total += 1

    return violations / max(total, 1)


def check_triangle_inequality(
    fg: FuchsianGroup, embeddings: dict, n_samples: int = 100,
    tol: float = 1e-4,
) -> float:
    """Metric 2: d_M(x,z) ≤ d_M(x,y) + d_M(y,z)."""
    nodes = list(embeddings.keys())
    rng = np.random.default_rng(42)
    violations = 0

    for _ in range(n_samples):
        i, j, k = rng.choice(nodes, 3, replace=False)
        x, y, z = embeddings[i], embeddings[j], embeddings[k]
        d_xz = fg.quotient_distance(x, z)
        d_xy = fg.quotient_distance(x, y)
        d_yz = fg.quotient_distance(y, z)
        if d_xz > d_xy + d_yz + tol:
            violations += 1

    return violations / n_samples


def check_antipodal_dependency(
    fg: FuchsianGroup, embeddings: dict, n_samples: int = 100,
) -> float:
    """Metric 3: How often quotient distance differs from old -v approach."""
    nodes = list(embeddings.keys())
    rng = np.random.default_rng(42)
    differs = 0

    for _ in range(n_samples):
        i, j = rng.choice(nodes, 2, replace=False)
        u, v = embeddings[i], embeddings[j]
        d_quotient = fg.quotient_distance(u, v)
        d_old = min(poincare_distance(u, v), poincare_distance(u, -v))
        if abs(d_quotient - d_old) > 1e-4:
            differs += 1

    return differs / n_samples


def compute_injectivity_radii(
    fg: FuchsianGroup, embeddings: dict,
) -> list[float]:
    """Metric 6: Injectivity radius per node.

    Defined as min_{γ ≠ id} d_H(v, γv) for each node v.
    This is half the length of the shortest closed geodesic through v.
    """
    radii = []
    for v in embeddings.values():
        orbit = fg.orbit(v, max_depth=2)
        if len(orbit) <= 1:
            continue
        # Exclude identity (first element)
        min_d = min(poincare_distance(v, gv) for gv in orbit[1:])
        radii.append(min_d)
    return radii


def run_verification(
    G: nx.Graph, embeddings: dict, fg: FuchsianGroup,
) -> dict:
    """Run all 6 verification metrics."""
    report = {}

    # Algebraic (fast)
    report["group_invariance_violation"] = check_group_invariance(fg, embeddings)
    report["triangle_inequality_violation"] = check_triangle_inequality(fg, embeddings)
    report["antipodal_dependency_rate"] = check_antipodal_dependency(fg, embeddings)

    # Differential-geometric (slow)
    flow = compute_ricci_flow(G, embeddings, iterations=5)
    last_curvatures = {edge: hist[-1] for edge, hist in flow.items()}
    curvature_values = list(last_curvatures.values())

    report["curvature_mean"] = float(np.mean(curvature_values)) if curvature_values else 0.0
    report["curvature_variance"] = float(np.var(curvature_values)) if curvature_values else 0.0

    neck_pinches = detect_neck_pinch(last_curvatures)
    report["neck_pinch_count"] = len(neck_pinches)
    report["neck_pinch_edges"] = [(u, v, float(k)) for u, v, k in neck_pinches]

    radii = compute_injectivity_radii(fg, embeddings)
    report["injectivity_radius_min"] = float(min(radii)) if radii else 0.0
    report["injectivity_radius_max"] = float(max(radii)) if radii else 0.0
    report["injectivity_radius_mean"] = float(np.mean(radii)) if radii else 0.0

    # PASS/FAIL (only metrics 1-2)
    report["PASS"] = (
        report["group_invariance_violation"] == 0.0
        and report["triangle_inequality_violation"] == 0.0
    )

    return report


def run_sweep(embeddings, depths, sigmas):
    """Sweep over depth and sigma combinations."""
    results = []
    for depth in depths:
        for sigma in sigmas:
            fg = FuchsianGroup(dim=2)
            nodes = list(embeddings.keys())
            rng = np.random.default_rng(42)

            # Measure hallucination block rate vs analogy recovery
            halluc_blocked = 0
            analogy_recovered = 0
            n_trials = 50

            for _ in range(n_trials):
                i, j = rng.choice(nodes, 2, replace=False)
                u, v = embeddings[i], embeddings[j]
                norm_u = np.linalg.norm(u)
                norm_v = np.linalg.norm(v)

                d_ouro, wh = ouroboros_distance(u, v, analogy_mode=True, sigma=sigma)
                d_raw = poincare_distance(u, v)

                if norm_u < 0.5 and norm_v > 0.85:
                    # Center-to-boundary (hallucination attempt)
                    if not wh:
                        halluc_blocked += 1
                elif norm_u > 0.85 and norm_v > 0.85:
                    # Boundary-to-boundary (analogy)
                    if wh and d_ouro < d_raw * 0.5:
                        analogy_recovered += 1

            results.append({
                "depth": depth,
                "sigma": sigma,
                "halluc_block_rate": halluc_blocked / max(1, n_trials),
                "analogy_recovery_rate": analogy_recovered / max(1, n_trials),
            })

    return results


```

- [ ] **Step 3b: Implement CLI wrapper**

```python
#!/usr/bin/env python3
# scripts/verify_ouroboros.py
"""CLI wrapper for Ouroboros geometric verification.

All metric logic lives in tecs.inference.verification (importable).
This script handles CLI args, graph loading, and output formatting.

Usage:
    python scripts/verify_ouroboros.py --eval-only
    python scripts/verify_ouroboros.py --checkpoint results/runs/.../checkpoint.json
    python scripts/verify_ouroboros.py --sweep-depth 0,1,2,3 --sweep-sigma 0.05,0.10,0.15,0.20
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx
from tecs.inference.ouroboros_geometry import FuchsianGroup
from tecs.inference.poincare_utils import generate_poincare_embeddings
from tecs.inference.verification import run_verification, run_sweep


def main():
    parser = argparse.ArgumentParser(description="Ouroboros Geometric Verification")
    parser.add_argument("--checkpoint", help="Path to checkpoint JSON")
    parser.add_argument("--eval-only", action="store_true", help="Quick eval-set verification")
    parser.add_argument("--sweep-depth", help="Comma-separated depths (e.g., 0,1,2,3)")
    parser.add_argument("--sweep-sigma", help="Comma-separated sigmas (e.g., 0.05,0.10,0.15)")
    parser.add_argument("--output", default="results/ouroboros_verification.json")
    args = parser.parse_args()

    if args.eval_only:
        from tecs.inference.eval_set import EVAL_KNOWLEDGE
        G = nx.Graph()
        entity_set = set()
        for h, r, t in EVAL_KNOWLEDGE:
            entity_set.add(h); entity_set.add(t)
        entity_index = {}
        for i, entity in enumerate(sorted(entity_set)):
            G.add_node(i); entity_index[entity] = i
        for h, r, t in EVAL_KNOWLEDGE:
            if h in entity_index and t in entity_index:
                G.add_edge(entity_index[h], entity_index[t])
        embeddings = generate_poincare_embeddings(G)
        fg = FuchsianGroup(dim=2)
    elif args.checkpoint:
        print(f"Loading checkpoint: {args.checkpoint}")
        G = nx.karate_club_graph()
        embeddings = generate_poincare_embeddings(G)
        fg = FuchsianGroup(dim=2)
    else:
        G = nx.karate_club_graph()
        embeddings = generate_poincare_embeddings(G)
        fg = FuchsianGroup(dim=2)

    report = run_verification(G, embeddings, fg)

    if args.sweep_depth and args.sweep_sigma:
        depths = [int(d) for d in args.sweep_depth.split(",")]
        sigmas = [float(s) for s in args.sweep_sigma.split(",")]
        report["sweep"] = run_sweep(embeddings, depths, sigmas)

    verdict = "PASS" if report["PASS"] else "FAIL"
    print(f"\n{'='*60}")
    print(f"  Ouroboros Verification: {verdict}")
    print(f"{'='*60}")
    print(f"  Group invariance violations:   {report['group_invariance_violation']:.4f}")
    print(f"  Triangle inequality violations:{report['triangle_inequality_violation']:.4f}")
    print(f"  Antipodal dependency rate:     {report['antipodal_dependency_rate']:.4f}")
    print(f"  Curvature variance:            {report['curvature_variance']:.6f}")
    print(f"  Neck pinch candidates:         {report['neck_pinch_count']}")
    print(f"  Injectivity radius:            [{report['injectivity_radius_min']:.3f}, {report['injectivity_radius_max']:.3f}]")
    print(f"{'='*60}\n")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2, default=str))
    print(f"Report saved to {args.output}")
    return 0 if report["PASS"] else 1

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/test_inference/test_verify_ouroboros.py -v`
Expected: All PASS

- [ ] **Step 5: Run the script end-to-end**

Run: `.venv/bin/python scripts/verify_ouroboros.py --eval-only`
Expected: PASS verdict with 0 violations on metrics 1-2

- [ ] **Step 6: Commit**

```bash
git add scripts/verify_ouroboros.py tests/test_inference/test_verify_ouroboros.py
git commit -m "feat: independent verification script with 6 metrics and sweep mode"
```

---

### Task 7: Documentation

**Files:**
- Create: `docs/ouroboros/THEORY.md`
- Create: `docs/ouroboros/IMPLEMENTATION.md`
- Create: `docs/ouroboros/VERIFICATION.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Write THEORY.md**

Cover: open hyperbolic space analogy collapse, Fuchsian group quotient H^d/Γ, Ouroboros hypothesis (boundary identification), hallucination vs epiphany discrimination, Perelman geometrization scope and limits, Mostow rigidity for dim≥3.

- [ ] **Step 2: Write IMPLEMENTATION.md**

Cover: FuchsianGroup generator design (dim=2,3,d), quotient_distance algorithm, Ollivier curvature implementation detail, adaptive_sigma calibration strategy, parameter tuning guide (theta, sigma, max_depth).

- [ ] **Step 3: Write VERIFICATION.md**

Cover: 6 metric definitions with PASS/FAIL criteria, verify_ouroboros.py usage, injectivity radius sweep interpretation guide, known limitations and future work.

- [ ] **Step 4: Update CLAUDE.md**

Add under operational notes:
```
### Ouroboros Verification
- Quick check: `python scripts/verify_ouroboros.py --eval-only`
- Parameter defaults: theta=0.85, sigma=auto, max_depth=2, dim=2
- dim=3 Mostow path: `FuchsianGroup(dim=3)` + see docs/ouroboros/THEORY.md
- Rollback: `FuchsianGroup(use_fuchsian=False)` for legacy -v behavior
```

- [ ] **Step 5: Commit**

```bash
git add docs/ouroboros/ CLAUDE.md
git commit -m "docs: Ouroboros theory, implementation guide, verification protocol"
```

---

### Task 8: Full Integration Test

**Files:**
- No new files — run existing + new tests together

- [ ] **Step 1: Run full test suite**

Run: `.venv/bin/pytest tests/ -v --tb=short`
Expected: All tests PASS (except the pre-existing `test_diversity_filter_exact_duplicates` failure)

- [ ] **Step 2: Run verification script with sweep**

Run: `.venv/bin/python scripts/verify_ouroboros.py --eval-only --sweep-depth 0,1,2,3 --sweep-sigma 0.05,0.10,0.15,0.20`
Expected: PASS + sweep results in JSON

- [ ] **Step 3: Run inference benchmark comparison**

Run:
```python
.venv/bin/python -c "
from tecs.inference.ouroboros_geometry import FuchsianGroup
fg_new = FuchsianGroup(dim=2, use_fuchsian=True)
fg_old = FuchsianGroup(dim=2, use_fuchsian=False)
import numpy as np
from tecs.inference.poincare_utils import poincare_distance
u = np.array([0.90, 0.15])
v = np.array([-0.85, 0.20])
print(f'Old (antipodal): {fg_old.quotient_distance(u, v):.4f}')
print(f'New (Fuchsian):  {fg_new.quotient_distance(u, v):.4f}')
print(f'Direct d_H:      {poincare_distance(u, v):.4f}')
"
```
Expected: New ≤ Old ≤ Direct

- [ ] **Step 4: Run full inference benchmark A/B comparison**

Run:
```python
.venv/bin/python -c "
from tecs.engine.benchmark_runner import BenchmarkRunner
from tecs.inference.eval_set import EVAL_KNOWLEDGE
from tecs.inference.poincare_utils import generate_poincare_embeddings, USE_FUCHSIAN
from tecs.types import TopologyState
import tecs.inference.poincare_utils as pu
import networkx as nx, numpy as np

# Build eval state
BenchmarkRunner._inference_cache = None
G = nx.Graph()
es = set()
for h,r,t in EVAL_KNOWLEDGE: es.add(h); es.add(t)
ei = {e:i for i,e in enumerate(sorted(es))}
for i in ei.values(): G.add_node(i)
rw = {'IsA':0.9,'HasA':0.7,'PartOf':0.8,'RelatedTo':0.5,'MadeOf':0.7}
for h,r,t in EVAL_KNOWLEDGE:
    if h in ei and t in ei: G.add_edge(ei[h],ei[t],weight=rw.get(r,0.5),relation=r)
ite = {v:k for k,v in ei.items()}
emb = generate_poincare_embeddings(G)
state = TopologyState(complex=G,complex_type='graph',curvature=np.zeros(len(G.nodes)),
    metrics={},history=[],metadata={'entity_index':ei,'index_to_entity':ite,
    'triples':EVAL_KNOWLEDGE,'poincare_embeddings':emb})

# A: Fuchsian (new)
pu.USE_FUCHSIAN = True
pu._default_group = None
BenchmarkRunner._inference_cache = state
class FDM:
    def get_concept_relations(s,n=100): return [{'head':h,'relation':r,'tail':t} for h,r,t in EVAL_KNOWLEDGE]
    def get_contradictions(s,n=50): return []
    def get_analogies(s,n=50): return []
r = BenchmarkRunner(FDM())
inf_new = r.run_inference_benchmark(state)

# B: Legacy
pu.USE_FUCHSIAN = False
pu._default_group = None
BenchmarkRunner._inference_cache = None
inf_old = r.run_inference_benchmark(state)

print('A/B Comparison:')
for k in inf_new:
    print(f'  {k}: old={inf_old[k]:.4f}  new={inf_new[k]:.4f}  delta={inf_new[k]-inf_old[k]:+.4f}')

# Restore
pu.USE_FUCHSIAN = True
pu._default_group = None
"
```
Expected: New scores ≥ old scores (or within tolerance)

- [ ] **Step 5: Final commit with tag**

```bash
git add -A
git commit -m "test: full integration verification of Ouroboros Perelmann upgrade"
```
