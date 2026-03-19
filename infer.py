"""TECS Inference Engine -- CLI"""
import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="TECS Topological Inference")
    parser.add_argument("query", nargs="?", help="Query: 'subject relation [object]'")
    parser.add_argument("--glove", default="data/glove.6B.50d.txt", help="GloVe vectors path")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--topics", nargs="+", default=None, help="Wikipedia topics to load")
    parser.add_argument("--analogy", nargs=2, metavar=("CONCEPT", "DOMAIN"),
                        help="Find analogies: --analogy force economics")
    parser.add_argument("--compare", nargs=2, metavar=("A", "B"),
                        help="Compare two concepts: --compare gravity price")
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
    knowledge = enc.build_complex()
    engine = InferenceEngine(knowledge)
    analogy = AnalogyEngine(knowledge)
    n_entities = len(knowledge.complex.nodes)
    n_edges = len(knowledge.complex.edges)
    print(f"Knowledge loaded: {n_entities} entities, {n_edges} connections")

    # Analogy mode (non-interactive)
    if args.analogy:
        concept, domain = args.analogy
        results = analogy.find_analogy(concept, domain)
        if not results:
            print(f"No analogies found for '{concept}' in domain '{domain}'.")
        for r in results:
            print(r)
            print()
        return

    # Compare mode (non-interactive)
    if args.compare:
        a, b = args.compare
        results = analogy.find_cross_domain_pattern(a, b)
        if not results:
            print(f"No structural pattern found between '{a}' and '{b}'.")
        for r in results:
            print(r)
            print()
        return

    if args.interactive or not args.query:
        print("\nTECS Inference Engine (type 'quit' to exit)")
        print("Format: subject relation [object]")
        print("  analogy CONCEPT DOMAIN   -- find cross-domain analogies")
        print("  compare CONCEPT_A CONCEPT_B -- compare two concepts")
        print("Example: cat IsA")
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
                results = analogy.find_analogy(concept, domain)
                if not results:
                    print(f"  No analogies found for '{concept}' in '{domain}'.")
                for r in results:
                    print(f"  {r}")
                    print()
                continue

            # Compare command
            if parts[0].lower() == "compare" and len(parts) >= 3:
                a, b = parts[1], parts[2]
                results = analogy.find_cross_domain_pattern(a, b)
                if not results:
                    print(f"  No structural pattern found between '{a}' and '{b}'.")
                for r in results:
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
            print(f"  {result}")
            print(f"  Path: {' -> '.join(result.path)}")
            print()
    else:
        parts = args.query.split()
        subject = parts[0]
        relation = parts[1]
        obj = parts[2] if len(parts) > 2 else "?"
        result = engine.query(subject, relation, obj)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
