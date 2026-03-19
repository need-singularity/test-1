"""Fuchsian group discretization for Ouroboros quotient geometry.

Provides Moebius generators acting on the Poincare disk/ball model,
orbit computation, and quotient distance (min over group orbit).
"""
from __future__ import annotations

from typing import Callable, List

import numpy as np

from tecs.inference.poincare_utils import poincare_distance

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MAX_NORM = 0.999  # clamp points strictly inside the disk/ball


def _clamp(v: np.ndarray) -> np.ndarray:
    """Clamp a point to lie strictly inside the unit ball."""
    n = np.linalg.norm(v)
    if n >= _MAX_NORM:
        return v * (_MAX_NORM / n)
    return v


# ---------------------------------------------------------------------------
# Moebius transforms  (Poincare ball model, arbitrary dimension)
# ---------------------------------------------------------------------------

def _moebius_add(a: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Moebius addition  a (+) x  in the Poincare ball model.

    Formula (see Ungar 2005):
        a (+) x = ((1 + 2<a,x> + ||x||^2) a + (1 - ||a||^2) x)
                  / (1 + 2<a,x> + ||a||^2 ||x||^2)
    """
    a_dot_x = np.dot(a, x)
    norm_a2 = np.dot(a, a)
    norm_x2 = np.dot(x, x)
    denom = 1.0 + 2.0 * a_dot_x + norm_a2 * norm_x2
    if abs(denom) < 1e-15:
        denom = 1e-15
    num = (1.0 + 2.0 * a_dot_x + norm_x2) * a + (1.0 - norm_a2) * x
    return _clamp(num / denom)


def _make_reflection(dim: int, axis: int) -> Callable[[np.ndarray], np.ndarray]:
    """Create a coordinate-reflection isometry: negate the *axis*-th coordinate.

    This is an isometry of the Poincare ball (it maps the ball to itself
    and preserves the metric because it is an orthogonal transformation).
    """
    def transform(v: np.ndarray) -> np.ndarray:
        w = v.copy()
        w[axis] = -w[axis]
        return _clamp(w)
    return transform


def _make_translation(dim: int, axis: int, t: float) -> Callable[[np.ndarray], np.ndarray]:
    """Create a hyperbolic translation along *axis* by distance *t*.

    Uses Moebius addition with a translation vector along the given axis.
    The translation parameter is tanh(t/2) to convert from hyperbolic
    distance to the Poincare ball coordinate.
    """
    a = np.zeros(dim)
    a[axis] = np.tanh(t / 2.0)

    def transform(v: np.ndarray) -> np.ndarray:
        return _clamp(_moebius_add(a, v))
    return transform


# ---------------------------------------------------------------------------
# Dim-2 specialisation: classical Moebius transforms on the Poincare disk
# ---------------------------------------------------------------------------

def _make_dim2_generators() -> List[Callable[[np.ndarray], np.ndarray]]:
    """Two generators for dim=2.

    gamma_1: rotation by pi  (z -> -z).  This is the coordinate reflection
             through the origin — an isometry of the Poincare disk.
    gamma_2: hyperbolic translation along x-axis with t = ln(3).
    """
    # gamma_1: point inversion (rotation by pi)
    def gamma1(v: np.ndarray) -> np.ndarray:
        return _clamp(-v)

    # gamma_2: hyperbolic translation, t = ln(3)
    t = np.log(3.0)
    gamma2 = _make_translation(2, 0, t)

    return [gamma1, gamma2]


# ---------------------------------------------------------------------------
# General dim-d generators
# ---------------------------------------------------------------------------

def _make_general_generators(dim: int) -> List[Callable[[np.ndarray], np.ndarray]]:
    """2*dim generators: d coordinate reflections + d translations."""
    gens: List[Callable] = []
    t = np.log(3.0)
    for axis in range(dim):
        gens.append(_make_reflection(dim, axis))
        gens.append(_make_translation(dim, axis, t))
    return gens


# ---------------------------------------------------------------------------
# FuchsianGroup
# ---------------------------------------------------------------------------

class FuchsianGroup:
    """Discrete isometry group of the Poincare disk/ball.

    Parameters
    ----------
    dim : int
        Ambient dimension (must be >= 2).
    num_generators : int | None
        Ignored (kept for API compat); generator count is determined by dim.
    use_fuchsian : bool
        If False, fall back to legacy mode (orbit = [v, -v]).
    """

    def __init__(
        self,
        dim: int,
        num_generators: int | None = None,
        use_fuchsian: bool = True,
    ) -> None:
        if dim < 2:
            raise ValueError(f"dim must be >= 2, got {dim}")
        self._dim = dim
        self._use_fuchsian = use_fuchsian

        if use_fuchsian:
            if dim == 2:
                self._gens = _make_dim2_generators()
            else:
                # For dim >= 3 (including Mostow-rigid cases): 2*d generators
                self._gens = _make_general_generators(dim)
        else:
            self._gens: List[Callable] = []

    # -- public API ----------------------------------------------------------

    def generators(self) -> List[Callable[[np.ndarray], np.ndarray]]:
        """Return the list of generator transforms."""
        return list(self._gens)

    def orbit(
        self,
        v: np.ndarray,
        max_depth: int = 2,
        *,
        max_size: int = 50,
        dedup_thresh: float = 0.01,
    ) -> List[np.ndarray]:
        """Compute the group orbit of *v* up to *max_depth* generator applications.

        Returns a deduplicated list of points (capped at *max_size*).
        """
        v = _clamp(np.asarray(v, dtype=np.float64))

        # Legacy fallback
        if not self._use_fuchsian:
            return [v.copy(), _clamp(-v)]

        orbit_points: List[np.ndarray] = [v.copy()]

        if max_depth <= 0:
            return orbit_points

        # BFS over generator applications
        frontier = [v.copy()]
        for _depth in range(max_depth):
            next_frontier: List[np.ndarray] = []
            for pt in frontier:
                for gen in self._gens:
                    w = gen(pt)
                    # deduplicate
                    if not any(
                        poincare_distance(w, existing) < dedup_thresh
                        for existing in orbit_points
                    ):
                        orbit_points.append(w)
                        next_frontier.append(w)
                        if len(orbit_points) >= max_size:
                            return orbit_points
            frontier = next_frontier
            if not frontier:
                break

        return orbit_points

    def quotient_distance(self, u: np.ndarray, v: np.ndarray) -> float:
        """Quotient distance: min d_H(gamma_a(u), gamma_b(v)) over orbits.

        For true symmetry we minimise over orbits of both u and v.
        """
        u = _clamp(np.asarray(u, dtype=np.float64))
        v = _clamp(np.asarray(v, dtype=np.float64))

        # Short-circuit: identical points → distance 0
        if np.allclose(u, v, atol=1e-12):
            return 0.0

        if not self._use_fuchsian:
            # Legacy: just v and -v
            return min(poincare_distance(u, v), poincare_distance(u, _clamp(-v)))

        orbit_u = self.orbit(u)
        orbit_v = self.orbit(v)
        best = float("inf")
        for gu in orbit_u:
            for gv in orbit_v:
                d = poincare_distance(gu, gv)
                if d < best:
                    best = d
        return best
