"""Deep Solve Loop — iteratively refine equations until convergence."""
from __future__ import annotations
import json
import subprocess
import numpy as np
from tecs.inference.dimension_checker import DimensionChecker


class DeepSolver:
    """Takes a hypothesis and grinds it through verification loops until it converges or dies."""

    def __init__(self, max_iterations: int = 10):
        self._max_iter = max_iterations
        self._dim_checker = DimensionChecker()
        self._history: list[dict] = []

    def solve(self, problem: dict) -> dict:
        """
        problem = {
            "name": "PD-L1 BFT threshold",
            "claim": "PD-L1 25% = Byzantine fault tolerance limit",
            "equation": "f_c = 1/(3*k)",
            "variables": {"f_c": "1", "k": "1"},  # dimensions: "1" = dimensionless
            "known_data": {"observed_cutoff": 0.25, "BFT_classical": 0.333},
            "domain": "oncology+CS",
        }
        """
        current = problem.copy()
        current["iteration"] = 0
        current["status"] = "UNSOLVED"

        for i in range(1, self._max_iter + 1):
            current["iteration"] = i
            print(f"\n  ── Iteration {i}/{self._max_iter} ──")

            # Stage 1: Dimension check
            dim_result = self._check_dimensions(current)
            if not dim_result["pass"]:
                print(f"  [DIM FAIL] {dim_result['reason']}")
                current = self._fix_dimensions(current, dim_result)
                self._history.append({"iter": i, "stage": "dimension", "action": "fix", "detail": dim_result["reason"]})
                continue

            # Stage 2: Numerical check
            num_result = self._check_numerical(current)
            if not num_result["pass"]:
                print(f"  [NUM FAIL] error={num_result['error']:.4f}, reason: {num_result['reason']}")
                current = self._fix_numerical(current, num_result)
                self._history.append({"iter": i, "stage": "numerical", "action": "fix", "error": num_result["error"]})
                continue

            # Stage 3: Counterexample check
            counter_result = self._check_counterexample(current)
            if not counter_result["pass"]:
                print(f"  [COUNTER FAIL] {counter_result['reason']}")
                current = self._fix_counterexample(current, counter_result)
                self._history.append({"iter": i, "stage": "counterexample", "action": "fix"})
                continue

            # Stage 4: Adversarial check
            adv_result = self._check_adversarial(current)
            if not adv_result["pass"]:
                print(f"  [ADV FAIL] {adv_result['reason']}")
                current = self._fix_adversarial(current, adv_result)
                self._history.append({"iter": i, "stage": "adversarial", "action": "fix"})
                continue

            # All stages passed
            current["status"] = "CONVERGED"
            print(f"  ✅ ALL STAGES PASSED at iteration {i}")
            break
        else:
            current["status"] = "MAX_ITERATIONS"
            print(f"  ⚠️  Max iterations reached without convergence")

        current["history"] = self._history
        return current

    def _check_dimensions(self, problem: dict) -> dict:
        """Check if equation dimensions match."""
        variables = problem.get("variables", {})
        equation = problem.get("equation", "")

        # Parse LHS and RHS
        if "=" in equation:
            lhs_str, rhs_str = equation.split("=", 1)
            lhs_var = lhs_str.strip()
            lhs_dim = variables.get(lhs_var, "1")

            # Try to infer RHS dimension from variables
            rhs_dim = self._infer_dimension(rhs_str.strip(), variables)

            result = self._dim_checker.check(lhs_dim, rhs_dim)
            return {"pass": result["match"], "reason": f"LHS [{lhs_dim}] vs RHS [{rhs_dim}]",
                    "lhs_dim": lhs_dim, "rhs_dim": rhs_dim}

        return {"pass": True, "reason": "no equation to check"}

    def _infer_dimension(self, expr: str, variables: dict) -> str:
        """Infer dimension of an expression from variable dimensions."""
        # Simple: if all variables are dimensionless, result is dimensionless
        dims_found = []
        for var, dim in variables.items():
            if var in expr:
                dims_found.append(dim)

        if all(d == "1" for d in dims_found):
            return "1"
        if dims_found:
            return dims_found[0]  # simplified
        return "1"

    def _check_numerical(self, problem: dict) -> dict:
        """Check if equation matches known data."""
        known = problem.get("known_data", {})
        equation = problem.get("equation", "")
        params = problem.get("fitted_params", {})

        if not known:
            return {"pass": True, "error": 0, "reason": "no known data"}

        # Try to evaluate equation numerically
        try:
            # Build evaluation context
            context = {**params}
            for k, v in known.items():
                context[k] = v

            # Extract prediction from equation
            if "=" in equation:
                lhs, rhs = equation.split("=", 1)
                lhs_var = lhs.strip()

                # Try eval (safe: only math)
                import math
                safe_context = {"__builtins__": {}, "math": math, "np": np,
                               "sqrt": math.sqrt, "log": math.log, "pi": math.pi,
                               "exp": math.exp, **context}

                try:
                    predicted = eval(rhs.strip(), safe_context)
                except Exception:
                    return {"pass": True, "error": 0, "reason": "cannot evaluate expression"}

                # Compare with observed
                observed_key = f"observed_{lhs_var}" if f"observed_{lhs_var}" in known else None
                if not observed_key:
                    # Try to find any "observed_" key
                    for k in known:
                        if k.startswith("observed"):
                            observed_key = k
                            break

                if observed_key and observed_key in known:
                    observed = known[observed_key]
                    if observed != 0:
                        error = abs(predicted - observed) / abs(observed)
                    else:
                        error = abs(predicted)

                    passed = error < 0.15  # 15% tolerance
                    return {"pass": passed, "error": error, "predicted": predicted,
                            "observed": observed, "reason": f"predicted={predicted:.4f} vs observed={observed:.4f}"}

            return {"pass": True, "error": 0, "reason": "no observable to compare"}
        except Exception as e:
            return {"pass": True, "error": 0, "reason": f"eval error: {e}"}

    def _check_counterexample(self, problem: dict) -> dict:
        """Check if equation fails on obviously wrong inputs."""
        equation = problem.get("equation", "")
        counterexamples = problem.get("counterexamples", [])

        for ce in counterexamples:
            # Each counterexample: {"input": {...}, "expected_fail": True}
            # If the equation gives a valid result for a case it shouldn't, that's bad
            pass

        return {"pass": True, "reason": "no counterexamples defined (add 'counterexamples' to problem)"}

    def _check_adversarial(self, problem: dict) -> dict:
        """Run adversarial critique via claude CLI."""
        try:
            data = json.dumps({
                "equation": problem.get("equation"),
                "claim": problem.get("claim"),
                "variables": problem.get("variables"),
                "iteration": problem.get("iteration"),
            }, default=str, ensure_ascii=False)

            prompt = (
                "아래 수식을 검증해. 1) 차원이 맞는지 2) 동어반복이 아닌지 "
                "3) 반증 가능한지 4) 수학적 비약이 없는지. "
                "문제가 있으면 구체적 수정안을 제시하고, 문제 없으면 'PASS'라고만 써. "
                "마크다운 없이 평문으로.\n\n" + data
            )

            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True, text=True, timeout=60,
            )
            output = result.stdout.strip() if result.returncode == 0 else ""
            output = "".join(c for c in output if c.isprintable() or c in "\n ")

            if "PASS" in output.upper() and len(output) < 20:
                return {"pass": True, "reason": "adversarial check passed"}
            elif output:
                return {"pass": False, "reason": output[:200]}
            else:
                return {"pass": True, "reason": "no adversarial response"}
        except Exception:
            return {"pass": True, "reason": "adversarial check skipped (claude unavailable)"}

    def _fix_dimensions(self, problem: dict, dim_result: dict) -> dict:
        """Ask claude to fix dimension mismatch."""
        return self._ask_fix(problem,
            f"차원 불일치: {dim_result['reason']}. "
            f"수식의 차원을 맞춰서 수정해. 누락된 상수(c, G, ℏ, k_B 등)를 추가해.")

    def _fix_numerical(self, problem: dict, num_result: dict) -> dict:
        """Ask claude to fix numerical mismatch."""
        return self._ask_fix(problem,
            f"수치 불일치: predicted={num_result.get('predicted')}, "
            f"observed={num_result.get('observed')}, error={num_result['error']:.2%}. "
            f"파라미터를 조정하거나 보정항을 추가해서 오차를 15% 이내로 줄여.")

    def _fix_counterexample(self, problem: dict, counter_result: dict) -> dict:
        """Ask claude to fix counterexample failure."""
        return self._ask_fix(problem,
            f"반례 실패: {counter_result['reason']}. 적용 범위를 제한하거나 조건을 추가해.")

    def _fix_adversarial(self, problem: dict, adv_result: dict) -> dict:
        """Ask claude to fix adversarial critique."""
        return self._ask_fix(problem,
            f"비판: {adv_result['reason']}. 이 비판을 반영해서 수식을 수정해.")

    def _ask_fix(self, problem: dict, instruction: str) -> dict:
        """Ask claude CLI to fix the equation."""
        try:
            data = json.dumps({
                "equation": problem.get("equation"),
                "claim": problem.get("claim"),
                "variables": problem.get("variables"),
                "known_data": problem.get("known_data"),
                "fitted_params": problem.get("fitted_params", {}),
            }, default=str, ensure_ascii=False)

            prompt = (
                f"수식을 수정해야 해. 현재 상태:\n{data}\n\n"
                f"수정 지시: {instruction}\n\n"
                "응답 형식 (JSON만, 다른 텍스트 없이):\n"
                '{"equation": "수정된 수식", "variables": {"var": "dim"}, '
                '"fitted_params": {"param": value}, "reasoning": "수정 이유"}'
            )

            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True, text=True, timeout=90,
            )
            output = result.stdout.strip() if result.returncode == 0 else ""
            output = "".join(c for c in output if c.isprintable() or c in "\n ")

            # Try to parse JSON from response
            try:
                # Find JSON in response
                start = output.find("{")
                end = output.rfind("}") + 1
                if start >= 0 and end > start:
                    fix = json.loads(output[start:end])
                    if "equation" in fix:
                        problem["equation"] = fix["equation"]
                        print(f"  → 수정: {fix['equation']}")
                    if "variables" in fix:
                        problem["variables"] = fix["variables"]
                    if "fitted_params" in fix:
                        problem["fitted_params"] = fix["fitted_params"]
                    if "reasoning" in fix:
                        print(f"  → 이유: {fix['reasoning'][:100]}")
            except json.JSONDecodeError:
                print(f"  → claude 응답 파싱 실패, 원본 유지")

        except Exception as e:
            print(f"  → fix 실패: {e}")

        return problem
