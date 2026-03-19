"""TECS Inference Engine -- CLI"""
import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="TECS Topological Inference")
    parser.add_argument("query", nargs="?", help="Query: 'subject relation [object]'")
    parser.add_argument("--glove", default="data/glove.6B.50d.txt", help="GloVe vectors path")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--topics", nargs="+", default=None, help="Wikipedia topics to load")
    args = parser.parse_args()

    from tecs.inference.knowledge_encoder import KnowledgeEncoder
    from tecs.inference.inference_engine import InferenceEngine

    print("Loading knowledge...")
    enc = KnowledgeEncoder()
    enc.load_glove(args.glove)
    enc.load_conceptnet_triples()
    enc.load_wordnet()
    if args.topics:
        enc.load_wikipedia(args.topics, depth=1, max_related=10)
    knowledge = enc.build_complex()
    engine = InferenceEngine(knowledge)
    n_entities = len(knowledge.complex.nodes)
    n_edges = len(knowledge.complex.edges)
    print(f"Knowledge loaded: {n_entities} entities, {n_edges} connections")

    if args.interactive or not args.query:
        print("\nTECS Inference Engine (type 'quit' to exit)")
        print("Format: subject relation [object]")
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
