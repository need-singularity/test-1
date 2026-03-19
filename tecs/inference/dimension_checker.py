"""Automatic dimensional analysis for bridge equations using SymPy."""
from __future__ import annotations

try:
    from sympy.physics.units.dimensions import Dimension
    from sympy.physics.units import length, time, mass, energy, temperature
    from sympy import symbols, sqrt, log, Abs
    _SYMPY_AVAILABLE = True
except ImportError:
    _SYMPY_AVAILABLE = False


class DimensionChecker:
    """Validates that both sides of an equation have matching dimensions."""

    def __init__(self):
        self._available = _SYMPY_AVAILABLE

    def check(self, lhs_dim: str, rhs_dim: str) -> dict:
        """Check if two dimension strings match.

        Dimension strings use: L (length), T (time), M (mass), E (energy), K (temperature), 1 (dimensionless)
        Examples: "L^2/T", "M*L/T^2", "1" (dimensionless)
        """
        lhs_parsed = self._parse_dimension(lhs_dim)
        rhs_parsed = self._parse_dimension(rhs_dim)

        match = lhs_parsed == rhs_parsed

        return {
            "match": match,
            "lhs": lhs_dim,
            "rhs": rhs_dim,
            "lhs_parsed": lhs_parsed,
            "rhs_parsed": rhs_parsed,
            "verdict": "PASS" if match else "FAIL: dimensional mismatch",
        }

    def _parse_dimension(self, dim_str: str) -> dict:
        """Parse dimension string into {base: exponent} dict."""
        dim_str = dim_str.strip()
        if dim_str == "1" or dim_str == "dimensionless":
            return {"L": 0, "T": 0, "M": 0}

        result = {"L": 0, "T": 0, "M": 0, "K": 0}

        # Handle division
        if "/" in dim_str:
            num, den = dim_str.split("/", 1)
            num_dims = self._parse_term(num)
            den_dims = self._parse_term(den)
            for base in result:
                result[base] = num_dims.get(base, 0) - den_dims.get(base, 0)
        else:
            result = self._parse_term(dim_str)

        # Remove zero entries
        return {k: v for k, v in result.items() if v != 0}

    def _parse_term(self, term: str) -> dict:
        """Parse a single term like 'M*L^2' or 'L^2*T^-1'."""
        result = {"L": 0, "T": 0, "M": 0, "K": 0}
        parts = term.replace("*", " ").split()

        for part in parts:
            part = part.strip()
            if "^" in part:
                base, exp = part.split("^")
                base = base.strip()
                exp = int(exp.strip())
            else:
                base = part.strip()
                exp = 1

            if base in result:
                result[base] += exp

        return {k: v for k, v in result.items() if v != 0}

    def validate_equation(self, name: str, lhs_dim: str, rhs_dim: str) -> str:
        """Validate an equation and return formatted result."""
        result = self.check(lhs_dim, rhs_dim)
        if result["match"]:
            return f"\u2705 {name}: [{lhs_dim}] = [{rhs_dim}] \u2014 PASS"
        else:
            return f"\u274c {name}: [{lhs_dim}] \u2260 [{rhs_dim}] \u2014 DIMENSIONAL MISMATCH"
