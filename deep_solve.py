"""TECS Deep Solve — iteratively refine equations until convergence."""
import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="TECS Deep Solve — grind equations to convergence")
    parser.add_argument("--problem", required=True, help="Problem JSON file or inline JSON")
    parser.add_argument("--max-iter", type=int, default=10, help="Max iterations")
    args = parser.parse_args()

    from tecs.inference.deep_solve import DeepSolver

    # Load problem
    if args.problem.endswith(".json"):
        with open(args.problem) as f:
            problem = json.load(f)
    else:
        problem = json.loads(args.problem)

    print(f"Deep Solve: {problem.get('name', 'unnamed')}")
    print(f"Claim: {problem.get('claim', '')}")
    print(f"Initial equation: {problem.get('equation', '')}")
    print(f"Max iterations: {args.max_iter}")

    solver = DeepSolver(max_iterations=args.max_iter)
    result = solver.solve(problem)

    print(f"\n{'='*60}")
    print(f"  STATUS: {result['status']}")
    print(f"  Final equation: {result.get('equation', '')}")
    print(f"  Iterations: {result.get('iteration', 0)}")
    print(f"{'='*60}")

    # Save result
    output_file = f"deep_solve_result_{problem.get('name', 'unnamed').replace(' ', '_')}.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2, default=str, ensure_ascii=False)
    print(f"Result saved to {output_file}")


if __name__ == "__main__":
    main()
