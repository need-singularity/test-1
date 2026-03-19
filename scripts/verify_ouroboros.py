#!/usr/bin/env python3
"""CLI wrapper for Ouroboros geometric verification."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx
from tecs.inference.ouroboros_geometry import FuchsianGroup
from tecs.inference.poincare_utils import generate_poincare_embeddings
from tecs.inference.verification import run_verification, run_sweep


def main():
    parser = argparse.ArgumentParser(description="Ouroboros Geometric Verification")
    parser.add_argument("--checkpoint", help="Path to checkpoint JSON")
    parser.add_argument("--eval-only", action="store_true")
    parser.add_argument("--sweep-depth", help="Comma-separated depths")
    parser.add_argument("--sweep-sigma", help="Comma-separated sigmas")
    parser.add_argument("--output", default="results/ouroboros_verification.json")
    args = parser.parse_args()

    if args.eval_only:
        from tecs.inference.eval_set import EVAL_KNOWLEDGE
        G = nx.Graph()
        es = set()
        for h, r, t in EVAL_KNOWLEDGE: es.add(h); es.add(t)
        ei = {}
        for i, e in enumerate(sorted(es)): G.add_node(i); ei[e] = i
        for h, r, t in EVAL_KNOWLEDGE:
            if h in ei and t in ei: G.add_edge(ei[h], ei[t])
        emb = generate_poincare_embeddings(G)
        fg = FuchsianGroup(dim=2)
    else:
        G = nx.karate_club_graph()
        emb = generate_poincare_embeddings(G)
        fg = FuchsianGroup(dim=2)

    report = run_verification(G, emb, fg)

    if args.sweep_depth and args.sweep_sigma:
        depths = [int(d) for d in args.sweep_depth.split(",")]
        sigmas = [float(s) for s in args.sweep_sigma.split(",")]
        report["sweep"] = run_sweep(emb, depths, sigmas)

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
