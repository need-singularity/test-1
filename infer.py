"""TECS Inference Engine -- CLI with verification pipeline"""
import argparse
import json


def verify_result(result, result_type="query"):
    """Run verification on inference result."""
    from tecs.inference.dimension_checker import DimensionChecker

    checks = []

    # 1. Formal check: confidence bounds
    if hasattr(result, 'confidence'):
        if result.confidence <= 0:
            checks.append("❌ FORMAL: confidence = 0 (no basis)")
        elif result.confidence >= 0.99 and hasattr(result, 'level') and result.level <= 1:
            checks.append("⚠️  FORMAL: perfect confidence on direct lookup only")
        else:
            checks.append("✅ FORMAL: confidence in valid range")

    # 2. Verification flag
    if hasattr(result, 'verified'):
        if result.verified:
            checks.append("✅ VERIFIED: structural consistency confirmed")
        else:
            checks.append("❌ VERIFIED: structural consistency FAILED")

    return checks


def verify_analogy(result):
    """Run verification on analogy result."""
    checks = []

    # 1. Wasserstein threshold
    if result.similarity < 0.60:
        checks.append("❌ REJECT: similarity < 0.60 (insufficient structural match)")
        return checks, False

    # 2. Betti number check
    if "β₀β₁β₂" in result.reasoning:
        betti_part = result.reasoning.split("β₀β₁β₂:")[1][:50]
        parts = betti_part.split(" vs ")
        if len(parts) == 2:
            b1 = parts[0].strip()
            b2 = parts[1].strip().split(";")[0].strip()
            if b1 == b2:
                checks.append(f"✅ BETTI: exact match {b1}")
            elif b1.startswith("(1,0,0)") and b2.startswith("(1,0,0)"):
                checks.append("⚠️  BETTI: both (1,0,0) — low information, may be graph-size artifact")
            else:
                checks.append(f"⚠️  BETTI: approximate {b1} ≈ {b2}")

    # 3. Mapping quality
    if result.mapping:
        n_mapped = len(result.mapping)
        if n_mapped < 2:
            checks.append("⚠️  MAPPING: only 1 pair — weak evidence")
        elif n_mapped >= 4:
            checks.append(f"✅ MAPPING: {n_mapped} pairs — strong evidence")
        else:
            checks.append(f"✅ MAPPING: {n_mapped} pairs")

    # 4. Verification flag
    if result.verified:
        checks.append("✅ STRUCTURAL: edge pattern preserved across mapping")
    else:
        checks.append("⚠️  STRUCTURAL: edge pattern NOT fully preserved")

    # Overall pass/fail
    passed = result.similarity >= 0.60 and len(checks) > 0
    has_reject = any("REJECT" in c for c in checks)

    return checks, not has_reject


def print_verified_result(result, result_type="query"):
    """Print result with verification status."""
    print(f"  {result}")
    if hasattr(result, 'path') and result.path:
        print(f"  Path: {' -> '.join(result.path)}")

    checks = verify_result(result, result_type)
    if checks:
        print(f"  ─── Verification ───")
        for c in checks:
            print(f"  {c}")
    print()


def print_verified_analogy(result):
    """Print analogy result with verification status."""
    checks, passed = verify_analogy(result)

    verdict = "PASS" if passed else "REJECT"
    icon = "✅" if passed else "❌"

    print(f"  {result}")
    print(f"  ─── Verification [{icon} {verdict}] ───")
    for c in checks:
        print(f"  {c}")

    if not passed:
        print(f"  ⛔ This result did NOT pass verification and should not be cited.")
    print()


def main():
    parser = argparse.ArgumentParser(description="TECS Topological Inference (with verification)")
    parser.add_argument("query", nargs="?", help="Query: 'subject relation [object]'")
    parser.add_argument("--glove", default="data/glove.6B.50d.txt", help="GloVe vectors path")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--topics", nargs="+", default=None, help="Wikipedia topics to load")
    parser.add_argument("--arxiv", nargs="+", default=None, help="arXiv search queries")
    parser.add_argument("--analogy", nargs=2, metavar=("CONCEPT", "DOMAIN"),
                        help="Find analogies: --analogy force economics")
    parser.add_argument("--compare", nargs=2, metavar=("A", "B"),
                        help="Compare two concepts: --compare gravity price")
    parser.add_argument("--no-verify", action="store_true", help="Skip verification")
    args = parser.parse_args()

    from tecs.inference.knowledge_encoder import KnowledgeEncoder
    from tecs.inference.inference_engine import InferenceEngine
    from tecs.inference.analogy_engine import AnalogyEngine

    print("Loading knowledge...")
    enc = KnowledgeEncoder()
    enc.load_glove(args.glove)
    enc.load_conceptnet_triples()
    enc.load_wordnet()
    if args.topics:
        enc.load_wikipedia(args.topics, depth=1, max_related=10)
    if args.arxiv:
        for query in args.arxiv:
            enc.load_arxiv(query, max_papers=20)
    knowledge = enc.build_complex()
    engine = InferenceEngine(knowledge)
    analogy_engine = AnalogyEngine(knowledge)
    n_entities = len(knowledge.complex.nodes)
    n_edges = len(knowledge.complex.edges)
    print(f"Knowledge loaded: {n_entities} entities, {n_edges} connections")
    if not args.no_verify:
        print("Verification: ENABLED (use --no-verify to disable)")
    print()

    do_verify = not args.no_verify

    # Analogy mode
    if args.analogy:
        concept, domain = args.analogy
        results = analogy_engine.find_analogy(concept, domain)
        if not results:
            print(f"No analogies found for '{concept}' in domain '{domain}'.")
        for r in results:
            if do_verify:
                print_verified_analogy(r)
            else:
                print(r)
                print()
        return

    # Compare mode
    if args.compare:
        a, b = args.compare
        results = analogy_engine.find_cross_domain_pattern(a, b)
        if not results:
            print(f"No structural pattern found between '{a}' and '{b}'.")
        for r in results:
            if do_verify:
                print_verified_analogy(r)
            else:
                print(r)
                print()
        return

    # Interactive / single query
    if args.interactive or not args.query:
        print("TECS Inference Engine (type 'quit' to exit)")
        print("Commands:")
        print("  subject relation [object]     — knowledge query")
        print("  analogy CONCEPT DOMAIN        — find cross-domain analogies")
        print("  compare CONCEPT_A CONCEPT_B   — compare two concepts")
        print()
        while True:
            try:
                query = input(">> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                break
            if query.lower() in ("quit", "exit", "q"):
                break
            if not query:
                continue

            parts = query.split()

            # Analogy command
            if parts[0].lower() == "analogy" and len(parts) >= 3:
                concept, domain = parts[1], parts[2]
                results = analogy_engine.find_analogy(concept, domain)
                if not results:
                    print(f"  No analogies found for '{concept}' in '{domain}'.")
                for r in results:
                    if do_verify:
                        print_verified_analogy(r)
                    else:
                        print(f"  {r}")
                        print()
                continue

            # Compare command
            if parts[0].lower() == "compare" and len(parts) >= 3:
                a, b = parts[1], parts[2]
                results = analogy_engine.find_cross_domain_pattern(a, b)
                if not results:
                    print(f"  No structural pattern found between '{a}' and '{b}'.")
                for r in results:
                    if do_verify:
                        print_verified_analogy(r)
                    else:
                        print(f"  {r}")
                        print()
                continue

            if len(parts) < 2:
                print("Format: subject relation [object]")
                continue
            subject = parts[0]
            relation = parts[1]
            obj = parts[2] if len(parts) > 2 else "?"
            result = engine.query(subject, relation, obj)
            if do_verify:
                print_verified_result(result)
            else:
                print(f"  {result}")
                print(f"  Path: {' -> '.join(result.path)}")
                print()
    else:
        parts = args.query.split()
        subject = parts[0]
        relation = parts[1]
        obj = parts[2] if len(parts) > 2 else "?"
        result = engine.query(subject, relation, obj)
        d = result.to_dict()
        if do_verify:
            checks = verify_result(result)
            d["verification"] = checks
        print(json.dumps(d, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
