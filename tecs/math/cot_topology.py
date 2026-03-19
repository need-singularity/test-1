"""Chain of Thought Topology — does reasoning create macro β₁ loops?

Hypothesis:
  Direct answer (System 1): text flows linearly → β₁ ≈ 0
  Self-correcting reasoning (System 2): text cross-references → β₁ > 0

We test this by building co-occurrence networks from text and tracking β₁.
"""
from __future__ import annotations
import numpy as np
import json
import time
from pathlib import Path


# Sample texts for comparison
SAMPLE_DIRECT = """The answer is 42. The capital of France is Paris. Water boils at 100 degrees celsius. The sun is a star. Gravity pulls objects toward earth. Light travels at 300000 km per second. DNA carries genetic information. Atoms are made of protons neutrons and electrons. The earth orbits the sun. Photosynthesis converts sunlight to energy."""

SAMPLE_HALLUCINATION = """The Riemann hypothesis was proven in 2019 by a team at Oxford using quantum computing methods. This breakthrough led to new encryption algorithms based on prime factorization being obsolete. The proof relies on a novel connection between zeta functions and neural networks. Subsequently all RSA encryption was replaced by quantum resistant alternatives. The mathematical community celebrated this as the greatest achievement since Fermats last theorem was proven by Andrew Wiles. The implications for number theory are profound as all L functions are now fully understood. This means the Langlands program has been completed and all automorphic forms are classified."""

SAMPLE_REASONING = """Let me think about whether the square root of 2 is rational. Assume for contradiction that sqrt(2) equals p over q where p and q are integers with no common factors. Then 2 equals p squared over q squared. So p squared equals 2 times q squared. This means p squared is even. But wait if p squared is even then p must be even. Let me check why. If p were odd then p squared would be odd. So p is even meaning p equals 2k for some integer k. Substituting back we get 4k squared equals 2q squared. So q squared equals 2k squared. But this means q squared is even and therefore q is even. Wait this contradicts our assumption that p and q have no common factors since both are even. Therefore sqrt 2 cannot be rational. Let me verify this makes sense. We assumed rationality and derived that both numerator and denominator must be even contradicting irreducibility. The logic is sound and each step follows necessarily from the previous one."""

SAMPLE_SELF_CORRECT = """What is 17 times 23. Let me compute step by step. 17 times 20 is 340. 17 times 3 is 51. So 17 times 23 is 340 plus 51 which is 391. Wait let me double check. 23 times 10 is 230. 23 times 7 is 161. 230 plus 161 is 391. Good both methods give 391. But actually let me verify once more. 17 times 23. I can also compute 20 times 23 minus 3 times 23. 20 times 23 is 460. 3 times 23 is 69. 460 minus 69 is 391. Three independent calculations all give 391. I am confident the answer is 391."""


def text_to_cooccurrence_graph(tokens: list[str], window_size: int = 5) -> tuple[list[str], np.ndarray]:
    """Build co-occurrence distance matrix from tokens."""
    vocab = sorted(set(tokens))
    if len(vocab) < 3:
        return vocab, np.zeros((len(vocab), len(vocab)))

    token_to_id = {t: i for i, t in enumerate(vocab)}
    n = len(vocab)

    # Count co-occurrences
    cooccur = np.zeros((n, n))
    for i in range(len(tokens) - window_size + 1):
        window = tokens[i:i + window_size]
        ids = [token_to_id[t] for t in window if t in token_to_id]
        for a in ids:
            for b in ids:
                if a != b:
                    cooccur[a][b] += 1

    # Convert to distance: high co-occurrence = short distance
    max_cooccur = cooccur.max() if cooccur.max() > 0 else 1
    dist = np.where(cooccur > 0, 1.0 / (1.0 + cooccur), 2.0)
    np.fill_diagonal(dist, 0)

    return vocab, dist


def compute_betti_from_distance(dist_matrix: np.ndarray, max_edge: float = 1.5) -> list[int]:
    """Compute Betti numbers from distance matrix."""
    n = dist_matrix.shape[0]
    if n < 3:
        return [n, 0, 0]

    try:
        import gudhi
        rips = gudhi.RipsComplex(distance_matrix=dist_matrix.tolist(), max_edge_length=max_edge)
        stree = rips.create_simplex_tree(max_dimension=2)
        stree.compute_persistence()
        betti = list(stree.betti_numbers())
        while len(betti) < 3:
            betti.append(0)
        return betti[:3]
    except ImportError:
        # Fallback
        edges = np.sum(dist_matrix < max_edge) // 2
        components = 1  # approximate
        return [components, max(0, edges - n + components), 0]


def track_beta1_over_length(text: str, window: int = 5, step: int = 20) -> list[dict]:
    """Track β₁ as text length T increases."""
    tokens = text.lower().split()
    trajectory = []

    for T in range(max(window + 5, 30), len(tokens) + 1, step):
        sub_tokens = tokens[:T]
        vocab, dist = text_to_cooccurrence_graph(sub_tokens, window_size=window)

        if len(vocab) < 3:
            trajectory.append({"T": T, "vocab_size": len(vocab), "beta0": 0, "beta1": 0, "beta2": 0})
            continue

        betti = compute_betti_from_distance(dist)
        trajectory.append({
            "T": T,
            "vocab_size": len(vocab),
            "beta0": betti[0],
            "beta1": betti[1],
            "beta2": betti[2],
        })

    return trajectory


def analyze_text(name: str, text: str, window: int = 5, step: int = 10):
    """Analyze one text sample."""
    tokens = text.lower().split()
    print(f"\n  [{name}] {len(tokens)} tokens")

    trajectory = track_beta1_over_length(text, window=window, step=step)

    # Print trajectory
    print(f"  {'T':>5} | {'Vocab':>5} | {'β₀':>4} {'β₁':>5} {'β₂':>4}")
    print(f"  {'─'*5}─┼─{'─'*5}─┼─{'─'*4}─{'─'*5}─{'─'*4}")
    for t in trajectory:
        print(f"  {t['T']:5d} | {t['vocab_size']:5d} | {t['beta0']:4d} {t['beta1']:5d} {t['beta2']:4d}")

    beta1_values = [t["beta1"] for t in trajectory]
    if beta1_values:
        print(f"  β₁ range: {min(beta1_values)} — {max(beta1_values)}")
        print(f"  β₁ mean: {np.mean(beta1_values):.1f}")
        print(f"  β₁ final: {beta1_values[-1]}")

    return trajectory


def run_experiment():
    """Compare β₁ trajectories across text types."""
    print("=" * 70)
    print("  Chain of Thought Topology Experiment")
    print("  Does reasoning create macro β₁ loops?")
    print("=" * 70)

    samples = {
        "DIRECT (facts)": SAMPLE_DIRECT,
        "HALLUCINATION (false)": SAMPLE_HALLUCINATION,
        "REASONING (proof)": SAMPLE_REASONING,
        "SELF-CORRECT (verify)": SAMPLE_SELF_CORRECT,
    }

    all_results = {}

    for name, text in samples.items():
        trajectory = analyze_text(name, text, window=5, step=10)
        all_results[name] = trajectory

    # Comparison
    print(f"\n{'='*70}")
    print(f"  Comparison: Final β₁")
    print(f"{'='*70}")

    for name, traj in all_results.items():
        beta1_vals = [t["beta1"] for t in traj]
        final = beta1_vals[-1] if beta1_vals else 0
        mean = np.mean(beta1_vals) if beta1_vals else 0
        peak = max(beta1_vals) if beta1_vals else 0
        print(f"  {name:30s}: final={final:4d}, mean={mean:6.1f}, peak={peak:4d}")

    # Verdict
    print(f"\n{'='*70}")
    print(f"  Verdict")
    print(f"{'='*70}")

    reasoning_beta1 = np.mean([t["beta1"] for t in all_results.get("REASONING (proof)", [])]) if all_results.get("REASONING (proof)") else 0
    halluc_beta1 = np.mean([t["beta1"] for t in all_results.get("HALLUCINATION (false)", [])]) if all_results.get("HALLUCINATION (false)") else 0
    direct_beta1 = np.mean([t["beta1"] for t in all_results.get("DIRECT (facts)", [])]) if all_results.get("DIRECT (facts)") else 0
    selfcorr_beta1 = np.mean([t["beta1"] for t in all_results.get("SELF-CORRECT (verify)", [])]) if all_results.get("SELF-CORRECT (verify)") else 0

    print(f"\n  β₁ means:")
    print(f"    Direct answers:    {direct_beta1:.1f}")
    print(f"    Hallucination:     {halluc_beta1:.1f}")
    print(f"    Reasoning (proof): {reasoning_beta1:.1f}")
    print(f"    Self-correction:   {selfcorr_beta1:.1f}")

    if reasoning_beta1 > halluc_beta1 * 1.5:
        print(f"\n  ✅ HYPOTHESIS SUPPORTED:")
        print(f"     Reasoning text creates MORE topological loops than hallucination")
        print(f"     β₁(reasoning) / β₁(hallucination) = {reasoning_beta1/max(halluc_beta1,0.1):.2f}x")
    elif reasoning_beta1 > halluc_beta1:
        print(f"\n  ⚠️  WEAK SUPPORT:")
        print(f"     Reasoning β₁ slightly higher but not decisive")
    else:
        print(f"\n  ❌ HYPOTHESIS NOT SUPPORTED:")
        print(f"     Reasoning does NOT create more loops than hallucination")

    if selfcorr_beta1 > reasoning_beta1:
        print(f"\n  📌 SELF-CORRECTION has highest β₁ = {selfcorr_beta1:.1f}")
        print(f"     → Cross-referencing ('let me check', 'wait') creates explicit loops")

    return all_results


if __name__ == "__main__":
    results = run_experiment()

    Path("results").mkdir(exist_ok=True)
    with open("results/cot_topology.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n결과 저장: results/cot_topology.json")
