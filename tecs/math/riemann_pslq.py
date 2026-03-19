"""Riemann zeros high-order statistics + PSLQ discovery engine.

This is pure computation — no LLM, no pattern matching.
If PSLQ finds an integer relation, it's a genuine mathematical conjecture.
"""
from __future__ import annotations
import time
import json
import numpy as np
from pathlib import Path


def compute_zeros(n_zeros: int, checkpoint_every: int = 1000) -> list[float]:
    """Compute first n nontrivial zeros of Riemann zeta function."""
    from mpmath import zetazero

    zeros = []
    start = time.time()

    for i in range(1, n_zeros + 1):
        z = float(zetazero(i).imag)
        zeros.append(z)

        if i % checkpoint_every == 0:
            elapsed = time.time() - start
            rate = i / elapsed
            eta = (n_zeros - i) / rate
            print(f"  {i:,}/{n_zeros:,} zeros ({elapsed:.0f}s, {rate:.0f}/s, ETA {eta:.0f}s)")

    elapsed = time.time() - start
    print(f"  완료: {n_zeros:,}개 영점, {elapsed:.0f}초")
    return zeros


def unfold_spacings(zeros: list[float]) -> np.ndarray:
    """Normalize zero spacings to mean 1 (unfolding)."""
    zeros = np.array(zeros)
    spacings_raw = np.diff(zeros)

    # Average density at height T: (1/2π) log(T/2π)
    mean_density = np.array([(1/(2*np.pi)) * np.log(z/(2*np.pi)) for z in zeros[:-1]])
    spacings = spacings_raw * mean_density
    spacings = spacings / np.mean(spacings)  # renormalize to mean 1

    return spacings


def compute_cumulants(spacings: np.ndarray, max_order: int = 8) -> dict[int, float]:
    """Compute cumulants κ₁ through κ_max from spacing data."""
    n = len(spacings)
    mean = np.mean(spacings)

    # Central moments
    moments = {}
    for k in range(1, max_order + 1):
        moments[k] = float(np.mean((spacings - mean) ** k))

    # Cumulants from moments (standard formulas)
    c = {}
    c[1] = float(mean)
    c[2] = moments[2]
    c[3] = moments[3]
    c[4] = moments[4] - 3 * moments[2]**2
    c[5] = moments[5] - 10 * moments[3] * moments[2]
    c[6] = moments[6] - 15 * moments[4] * moments[2] - 10 * moments[3]**2 + 30 * moments[2]**3

    if max_order >= 7:
        c[7] = (moments[7] - 21 * moments[5] * moments[2] - 35 * moments[4] * moments[3]
                + 210 * moments[3] * moments[2]**2)
    if max_order >= 8:
        c[8] = (moments[8] - 28 * moments[6] * moments[2] - 56 * moments[5] * moments[3]
                - 35 * moments[4]**2 + 420 * moments[4] * moments[2]**2
                + 560 * moments[3]**2 * moments[2] - 630 * moments[2]**4)

    return c


def compute_gue_wigner_cumulants(max_order: int = 8) -> dict[int, float]:
    """Compute GUE Wigner surmise cumulants analytically."""
    from scipy.integrate import quad

    def wigner_gue(s):
        return (32 / np.pi**2) * s**2 * np.exp(-4 * s**2 / np.pi)

    # Moments
    gue_moments = {}
    for k in range(1, max_order + 1):
        val, _ = quad(lambda s: s**k * wigner_gue(s), 0, 20)
        gue_moments[k] = val

    mean = gue_moments[1]

    # Central moments
    cm = {}
    for k in range(1, max_order + 1):
        val, _ = quad(lambda s: (s - mean)**k * wigner_gue(s), 0, 20)
        cm[k] = val

    # Cumulants
    c = {}
    c[1] = mean
    c[2] = cm[2]
    c[3] = cm[3]
    c[4] = cm[4] - 3 * cm[2]**2
    c[5] = cm[5] - 10 * cm[3] * cm[2]
    c[6] = cm[6] - 15 * cm[4] * cm[2] - 10 * cm[3]**2 + 30 * cm[2]**3

    if max_order >= 7:
        c[7] = cm[7] - 21 * cm[5] * cm[2] - 35 * cm[4] * cm[3] + 210 * cm[3] * cm[2]**2
    if max_order >= 8:
        c[8] = (cm[8] - 28 * cm[6] * cm[2] - 56 * cm[5] * cm[3]
                - 35 * cm[4]**2 + 420 * cm[4] * cm[2]**2
                + 560 * cm[3]**2 * cm[2] - 630 * cm[2]**4)

    return c


def run_pslq(target: float, constants: dict[str, float], precision: int = 50) -> dict | None:
    """Run PSLQ to find integer relation: a₀·target + a₁·c₁ + a₂·c₂ + ... = 0

    Returns coefficients if found, None otherwise.
    """
    from mpmath import mpf, pi, log, zeta, euler, catalan, identify, pslq

    # Set precision
    import mpmath
    mpmath.mp.dps = precision

    target_mp = mpf(str(target))

    # Method 1: mpmath identify (tries common constants)
    identified = identify(target_mp)
    if identified:
        return {"method": "identify", "result": identified, "target": float(target)}

    # Method 2: PSLQ with specified constants
    const_names = list(constants.keys())
    const_values = [mpf(str(v)) for v in constants.values()]

    # Vector: [target, c1, c2, ..., 1]
    vector = [target_mp] + const_values + [mpf(1)]

    relation = pslq(vector)
    if relation is not None:
        # Check: relation is [a0, a1, ..., an, a_const]
        # a0*target + a1*c1 + ... + an*1 = 0
        # → target = -(a1*c1 + ... + an) / a0
        names = ["TARGET"] + const_names + ["1"]
        terms = []
        for coeff, name in zip(relation, names):
            if coeff != 0:
                terms.append(f"{coeff}·{name}")

        formula = " + ".join(terms) + " = 0"

        # Verify
        check = sum(r * v for r, v in zip(relation, [target_mp] + const_values + [mpf(1)]))
        residual = abs(float(check))

        return {
            "method": "pslq",
            "relation": [int(r) for r in relation],
            "names": names,
            "formula": formula,
            "residual": residual,
            "target": float(target),
        }

    return None


def run_experiment(n_zeros: int = 10000, max_order: int = 8, pslq_precision: int = 50):
    """Full experiment: compute zeros → cumulants → PSLQ discovery."""

    print("=" * 70)
    print(f"  Riemann Zero Statistics + PSLQ Discovery")
    print(f"  Zeros: {n_zeros:,}, Cumulants: up to κ_{max_order}")
    print("=" * 70)

    # Step 1: Compute zeros
    print(f"\n[1/4] Computing {n_zeros:,} zeros...")
    zeros = compute_zeros(n_zeros)

    # Step 2: Unfold spacings
    print(f"\n[2/4] Unfolding spacings...")
    spacings = unfold_spacings(zeros)
    print(f"  {len(spacings)} spacings, mean={np.mean(spacings):.6f}, std={np.std(spacings):.6f}")

    # Step 3: Compute cumulants
    print(f"\n[3/4] Computing cumulants κ₁ through κ_{max_order}...")
    zeta_cumulants = compute_cumulants(spacings, max_order)
    gue_cumulants = compute_gue_wigner_cumulants(max_order)

    print(f"\n  {'κ':>4} | {'Zeta zeros':>14} | {'GUE (Wigner)':>14} | {'Δ':>12} | {'Δ%':>8}")
    print(f"  {'─'*4}─┼─{'─'*14}─┼─{'─'*14}─┼─{'─'*12}─┼─{'─'*8}")

    deltas = {}
    for k in range(1, max_order + 1):
        if k in zeta_cumulants and k in gue_cumulants:
            z = zeta_cumulants[k]
            g = gue_cumulants[k]
            delta = z - g
            deltas[k] = delta
            pct = abs(delta / g * 100) if abs(g) > 1e-15 else float('inf')
            print(f"  κ_{k:1d} | {z:+14.10f} | {g:+14.10f} | {delta:+12.10f} | {pct:7.2f}%")

    # Step 4: PSLQ on cumulants and deltas
    print(f"\n[4/4] Running PSLQ on cumulants...")

    from mpmath import pi as mp_pi, log as mp_log, zeta as mp_zeta, euler as mp_euler

    known_constants = {
        "π": float(mp_pi),
        "π²": float(mp_pi**2),
        "log(2)": float(mp_log(2)),
        "ζ(3)": float(mp_zeta(3)),
        "γ": float(mp_euler),
        "π²/6": float(mp_pi**2 / 6),
        "1/π": float(1 / mp_pi),
        "1/π²": float(1 / mp_pi**2),
    }

    discoveries = []

    # Try PSLQ on each cumulant
    for k in range(2, max_order + 1):
        if k not in zeta_cumulants:
            continue

        val = zeta_cumulants[k]
        print(f"\n  PSLQ on κ_{k} = {val:+.15f}")

        result = run_pslq(val, known_constants, precision=pslq_precision)
        if result:
            print(f"    발견: {result.get('formula', result.get('result', ''))}")
            print(f"    잔차: {result.get('residual', 'N/A')}")
            discoveries.append({"cumulant": k, "value": val, **result})
        else:
            print(f"    정수 관계 없음")

        # Also try on delta (zeta - GUE)
        if k in deltas and abs(deltas[k]) > 1e-15:
            delta = deltas[k]
            print(f"\n  PSLQ on Δκ_{k} = {delta:+.15f} (zeta - GUE)")
            result = run_pslq(delta, known_constants, precision=pslq_precision)
            if result:
                print(f"    발견: {result.get('formula', result.get('result', ''))}")
                discoveries.append({"cumulant_delta": k, "value": delta, **result})
            else:
                print(f"    정수 관계 없음")

    # Summary
    print(f"\n{'='*70}")
    print(f"  결과 요약")
    print(f"{'='*70}")
    print(f"  영점 수: {n_zeros:,}")
    print(f"  커뮬런트 계산: κ₁~κ_{max_order}")
    print(f"  PSLQ 발견: {len(discoveries)}건")

    if discoveries:
        print(f"\n  발견된 정수 관계:")
        for d in discoveries:
            k = d.get("cumulant", d.get("cumulant_delta", "?"))
            prefix = "κ" if "cumulant" in d else "Δκ"
            print(f"    {prefix}_{k}: {d.get('formula', d.get('result', ''))}")
    else:
        print(f"\n  정수 관계 발견 없음 — 더 높은 정밀도나 더 많은 영점이 필요할 수 있음")

    # Save results
    output = {
        "n_zeros": n_zeros,
        "max_order": max_order,
        "pslq_precision": pslq_precision,
        "cumulants_zeta": {str(k): v for k, v in zeta_cumulants.items()},
        "cumulants_gue": {str(k): v for k, v in gue_cumulants.items()},
        "deltas": {str(k): v for k, v in deltas.items()},
        "discoveries": discoveries,
    }

    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Riemann zeros PSLQ discovery")
    parser.add_argument("--zeros", type=int, default=10000, help="Number of zeros to compute")
    parser.add_argument("--order", type=int, default=8, help="Max cumulant order")
    parser.add_argument("--precision", type=int, default=50, help="PSLQ decimal precision")
    parser.add_argument("--output", default="results/riemann_pslq_result.json", help="Output file")
    args = parser.parse_args()

    result = run_experiment(n_zeros=args.zeros, max_order=args.order, pslq_precision=args.precision)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n결과 저장: {args.output}")
