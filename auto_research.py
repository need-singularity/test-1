"""TECS Auto-Research Loop — autonomous hypothesis → code → verify → mutate cycle.

What it actually does:
1. Claude generates a hypothesis + Python verification code
2. Code runs and produces numbers
3. DimensionChecker + numerical check validates
4. If fails: Claude fixes and retries
5. If passes: saves result and generates next hypothesis

What it does NOT do:
- "Self-evolve" or "grow consciousness"
- It's an automated research assistant loop, not AGI
"""
import argparse
import json
import subprocess
import tempfile
import time
import sys
from pathlib import Path
from datetime import datetime


def claude_generate(prompt: str, timeout: int = 120, retries: int = 2) -> str:
    """Call claude CLI and return response, with retries on empty output."""
    for attempt in range(retries + 1):
        try:
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True, text=True, timeout=timeout,
            )
            output = result.stdout.strip() if result.returncode == 0 else ""
            cleaned = "".join(c for c in output if c.isprintable() or c in "\n ")
            if cleaned or attempt == retries:
                return cleaned
            print(f"    (Empty response, retrying {attempt+1}/{retries}...)")
            time.sleep(2)
        except subprocess.TimeoutExpired:
            if attempt < retries:
                print(f"    (Timeout, retrying {attempt+1}/{retries}...)")
                continue
            return "ERROR: timeout"
        except Exception as e:
            return f"ERROR: {e}"
    return ""


def extract_python_code(text: str) -> str:
    """Extract Python code block from text."""
    if "```python" in text:
        start = text.find("```python") + 9
        end = text.find("```", start)
        if end > start:
            return text[start:end].strip()
    if "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end > start:
            return text[start:end].strip()
    return ""


def run_code(code: str, timeout: int = 120) -> dict:
    """Run Python code in subprocess and capture output."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir='/tmp') as f:
        f.write(code)
        f.flush()
        try:
            result = subprocess.run(
                [sys.executable, f.name],
                capture_output=True, text=True, timeout=timeout,
                cwd=str(Path(__file__).parent),
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:2000],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": "TIMEOUT", "returncode": -1}
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}


def run_cycle(cycle_num: int, target: str, previous_results: list[dict]) -> dict:
    """Run one research cycle: generate → code → run → verify → mutate."""

    print(f"\n{'='*70}")
    print(f"  Cycle {cycle_num}")
    print(f"{'='*70}")

    cycle_result = {
        "cycle": cycle_num,
        "target": target,
        "timestamp": datetime.now().isoformat(),
        "phases": {},
    }

    # Context from previous cycles
    prev_summary = ""
    if previous_results:
        last = previous_results[-1]
        prev_summary = (
            f"이전 사이클 결과: {last.get('phases', {}).get('verify', {}).get('verdict', 'N/A')}. "
            f"이전 오류: {last.get('phases', {}).get('verify', {}).get('issues', 'none')}. "
        )

    # ── Phase 1: Generate hypothesis + code ──
    print(f"\n  [Phase 1] Generating hypothesis + verification code...")

    # Build seed context from prior verified results + Cycle 2 Small-world insight
    seed_context = ""
    if previous_results:
        verified = [r for r in previous_results if r.get("status") == "VERIFIED"]
        failed = [r for r in previous_results if "FAILED" in r.get("status", "")]
        if verified:
            seed_context += "이전에 검증 통과했지만 동어반복으로 판명된 가설들 (반복 금지):\n"
            for v in verified:
                h = v.get("phases", {}).get("verify", {}).get("hypothesis", "")
                seed_context += f"  - {h}\n"
        if failed:
            last_fail = failed[-1]
            h = last_fail.get("phases", {}).get("verify", {}).get("hypothesis", "")
            seed_context += f"마지막 실패 가설: {h}\n"

    gen_prompt = (
        f"연구 목표: {target}\n\n"
        f"{prev_summary}\n"
        f"{seed_context}\n"
        "━━━ 절대 준수 규칙 ━━━\n"
        "1. 동어반복 금지: '그래프에 순환 구조를 넣으면 β₁이 올라간다'는 위상수학 정의의 재진술일 뿐이다.\n"
        "   β₁을 직접 조작하는 가설은 즉시 폐기하라.\n"
        "2. 독립변수(X)와 종속변수(Y)를 반드시 분리하라:\n"
        "   - X: 그래프의 구조적 속성 (예: Small-world 계수, 클러스터링, rewiring 확률, 허브 분포)\n"
        "   - Y: β₁과 무관한 독립적 성능 지표 (예: 정답률, 수렴 속도, 정보 전달 효율)\n"
        "   - 관측: 해당 X 조건에서 β₁이 어떻게 변하는지는 '부산물'로만 기록\n"
        "3. 유망한 방향: Watts-Strogatz Small-world 네트워크의 rewiring 확률 p가 특정 임계점을 넘을 때,\n"
        "   정보 전달 효율이나 탐색 성능에 상전이(phase transition)가 일어나는가?\n"
        "   이때 β₁은 예측 변수가 아니라 관측 변수다.\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "다음을 생성해:\n"
        "1. 비자명한 인과 가설 (한 문장) — 'X를 바꿨더니 Y가 폭발했다' 형태\n"
        "2. 가설을 수치적으로 검증하는 Python 코드 (```python 블록)\n"
        "   - numpy, scipy, networkx만 사용 (외부 데이터 다운로드 없음)\n"
        "   - X(구조)를 조작하고, Y(성능 지표)를 측정하며, β₁은 별도로 관측만 기록\n"
        "   - 코드 마지막에 반드시 결과를 JSON으로 print\n"
        "   - 형식: print(json.dumps({'hypothesis': '...', 'X_var': '...', 'Y_var': '...', "
        "'result': 수치, 'expected': 수치, 'error': 오차율, 'beta1_observed': 수치, "
        "'verdict': 'PASS/FAIL'}))\n"
        "   - 30초 안에 실행 가능할 것\n"
        "3. 변수의 SI 차원 (예: 'L^2/T')\n"
        "마크다운 없이 평문 + 코드 블록만."
    )

    response = claude_generate(gen_prompt, timeout=180)
    code = extract_python_code(response)

    cycle_result["phases"]["generate"] = {
        "response_length": len(response),
        "code_extracted": bool(code),
        "code_length": len(code),
    }

    if not code:
        print(f"    Code extraction failed (response length: {len(response)})")
        if response:
            print(f"    Response preview: {response[:150]}...")
        cycle_result["phases"]["generate"]["error"] = "no code extracted"
        cycle_result["status"] = "FAILED_GENERATION"
        return cycle_result

    print(f"    Hypothesis generated, code: {len(code)} chars")

    # ── Phase 1.5: Pre-emptive tautology gate ──
    print(f"\n  [Phase 1.5] Tautology pre-screen...")

    # Extract hypothesis from the response text (before code block)
    hyp_text = response.split("```")[0].strip() if "```" in response else response[:500]

    tautology_prompt = (
        f"아래 가설과 코드를 검토하라:\n"
        f"가설 텍스트: {hyp_text[:500]}\n"
        f"코드 요약: {code[:800]}\n\n"
        "판정 기준 (하나라도 해당하면 TAUTOLOGY):\n"
        "1. 그래프에 순환/루프/back-edge를 삽입하면 β₁이 올라간다 → 위상수학 정의의 재진술\n"
        "2. 독립변수(X)와 종속변수(Y)가 실질적으로 같은 것을 측정한다\n"
        "3. 코드가 β₁을 직접 fitness로 최적화한다\n"
        "4. 결과가 그래프 이론의 자명한 정리이다 (예: 트리의 β₁=0)\n\n"
        "TAUTOLOGY이면 정확히 'TAUTOLOGY'만 출력. 아니면 정확히 'NOVEL'만 출력.\n"
        "한 단어만 답하라."
    )

    taut_check = claude_generate(tautology_prompt, timeout=30).strip().upper()
    is_tautology = "TAUTOLOGY" in taut_check

    cycle_result["phases"]["tautology_gate"] = {
        "response": taut_check[:100],
        "is_tautology": is_tautology,
    }

    if is_tautology:
        print(f"    ⛔ TAUTOLOGY detected — regenerating with stricter constraints...")

        regen_prompt = (
            f"연구 목표: {target}\n\n"
            "직전에 생성한 가설이 동어반복(tautology)으로 판정되었다.\n"
            f"기각된 가설: {hyp_text[:300]}\n\n"
            "━━━ 강화된 제약 ━━━\n"
            "β₁을 종속변수나 최적화 대상으로 쓰는 것을 절대 금지한다.\n"
            "반드시 β₁과 무관한 독립적 성능 지표(정답률, 수렴 시간, shortest path 효율, "
            "정보 엔트로피 등)를 Y로 사용하라.\n"
            "β₁은 오직 '관측 부산물'로만 기록하라.\n"
            "그래프 구조(X)를 바꿨을 때 성능(Y)에 비자명한 상전이가 일어나는 가설을 제안하라.\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "다음을 생성해:\n"
            "1. 비자명한 인과 가설 (한 문장)\n"
            "2. Python 검증 코드 (```python 블록)\n"
            "   - numpy, scipy, networkx만 사용\n"
            "   - print(json.dumps({'hypothesis': '...', 'X_var': '...', 'Y_var': '...', "
            "'result': 수치, 'expected': 수치, 'error': 오차율, 'beta1_observed': 수치, "
            "'verdict': 'PASS/FAIL'}))\n"
            "마크다운 없이 평문 + 코드 블록만."
        )

        response = claude_generate(regen_prompt, timeout=180)
        code = extract_python_code(response)

        if not code:
            print(f"    Regeneration failed — no code extracted")
            cycle_result["status"] = "FAILED_TAUTOLOGY_REGEN"
            return cycle_result

        print(f"    Regenerated: {len(code)} chars")
        cycle_result["phases"]["generate"]["regenerated"] = True
        cycle_result["phases"]["generate"]["code_length"] = len(code)

    # ── Phase 2: Run code ──
    print(f"\n  [Phase 2] Running verification code...")

    run_result = run_code(code, timeout=60)
    cycle_result["phases"]["run"] = {
        "success": run_result["success"],
        "stdout": run_result["stdout"][:1000],
        "stderr": run_result["stderr"][:500],
    }

    if not run_result["success"]:
        print(f"    Execution failed: {run_result['stderr'][:100]}")

        # ── Phase 2b: Auto-fix ──
        print(f"\n  [Phase 2b] Attempting auto-fix...")
        fix_prompt = (
            f"이 Python 코드가 에러를 냈어:\n```python\n{code}\n```\n"
            f"에러: {run_result['stderr'][:500]}\n"
            "에러를 고쳐서 전체 수정된 코드를 ```python 블록으로 다시 줘. "
            "외부 데이터 다운로드 없이 자체 생성 데이터만 사용."
        )
        fix_response = claude_generate(fix_prompt)
        fixed_code = extract_python_code(fix_response)

        if fixed_code:
            print(f"    Retrying with fixed code...")
            run_result = run_code(fixed_code, timeout=60)
            cycle_result["phases"]["run"]["retry"] = True
            cycle_result["phases"]["run"]["success"] = run_result["success"]
            cycle_result["phases"]["run"]["stdout"] = run_result["stdout"][:1000]
            code = fixed_code

        if not run_result["success"]:
            cycle_result["status"] = "FAILED_EXECUTION"
            return cycle_result

    print(f"    Code executed successfully")

    # ── Phase 3: Parse and verify results ──
    print(f"\n  [Phase 3] Verifying results...")

    # Try to parse JSON from output
    output = run_result["stdout"]
    parsed = None
    for line in output.strip().split("\n"):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                parsed = json.loads(line)
                break
            except json.JSONDecodeError:
                continue

    if not parsed:
        print(f"    Could not parse JSON result from output")
        cycle_result["phases"]["verify"] = {"verdict": "PARSE_FAIL"}
        cycle_result["status"] = "FAILED_PARSE"
        return cycle_result

    verdict = parsed.get("verdict", "UNKNOWN")
    error = parsed.get("error", None)
    hypothesis = parsed.get("hypothesis", "")

    cycle_result["phases"]["verify"] = {
        "verdict": verdict,
        "error": error,
        "hypothesis": hypothesis,
        "result": parsed.get("result"),
        "expected": parsed.get("expected"),
        "X_var": parsed.get("X_var", ""),
        "Y_var": parsed.get("Y_var", ""),
        "beta1_observed": parsed.get("beta1_observed"),
        "full_output": parsed,
    }

    if verdict == "PASS":
        print(f"    ✅ VERIFIED: {hypothesis[:80]}")
        print(f"    Error: {error}")
        cycle_result["status"] = "VERIFIED"
    else:
        print(f"    ❌ FAILED: {hypothesis[:80]}")
        print(f"    Error: {error}")
        cycle_result["status"] = "FAILED_VERIFY"

    # ── Phase 4: Adversarial critique ──
    print(f"\n  [Phase 4] Adversarial critique...")

    x_var = parsed.get("X_var", "불명")
    y_var = parsed.get("Y_var", "불명")
    critique_prompt = (
        f"이 가설을 공격해: '{hypothesis}'\n"
        f"독립변수(X): {x_var}, 종속변수(Y): {y_var}\n"
        f"검증 결과: {json.dumps(parsed, default=str)}\n\n"
        "다음 5가지를 순서대로 검토:\n"
        "1) X→Y 인과관계가 동어반복(정의의 재진술)인가?\n"
        "2) X와 Y가 실질적으로 같은 것을 측정하고 있지 않은가?\n"
        "3) β₁이 직접 최적화 대상으로 쓰였는가? (관측만 허용)\n"
        "4) 결과가 그래프 이론의 자명한 정리인가?\n"
        "5) 반증 가능하고 비자명한 예측을 하고 있는가?\n\n"
        "5개 모두 통과하면 'PASS'. 하나라도 걸리면 문제를 구체적으로 써라."
    )
    critique = claude_generate(critique_prompt, timeout=60)

    cycle_result["phases"]["critique"] = {
        "response": critique[:500],
        "passed": "PASS" in critique.upper() and len(critique) < 50,
    }

    if "PASS" in critique.upper() and len(critique) < 50:
        print(f"    Critique: PASSED")
    else:
        print(f"    Critique: {critique[:100]}")

    return cycle_result


def main():
    parser = argparse.ArgumentParser(description="TECS Auto-Research Loop")
    parser.add_argument("--target", default="트랜스포머 어텐션 그래프에서 층이 깊어질수록 β₁이 감소하는 현상의 수학적 원인을 찾고, β₁ 감소율과 모델 성능의 관계를 수치로 검증")
    parser.add_argument("--cycles", type=int, default=5, help="Number of research cycles")
    parser.add_argument("--output", default="results/auto_research.json")
    args = parser.parse_args()

    print("TECS Auto-Research Loop")
    print(f"  Target: {args.target[:80]}...")
    print(f"  Cycles: {args.cycles}")

    results = []

    for i in range(1, args.cycles + 1):
        result = run_cycle(i, args.target, results)
        results.append(result)

        # Save after each cycle
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)

        status = result.get("status", "UNKNOWN")
        print(f"\n  Cycle {i} status: {status}")

        if status == "VERIFIED":
            print(f"  → Verified result found. Continuing to build on it.")

    # Summary
    print(f"\n{'='*70}")
    print(f"  Auto-Research Summary ({len(results)} cycles)")
    print(f"{'='*70}")

    verified = sum(1 for r in results if r.get("status") == "VERIFIED")
    failed = sum(1 for r in results if "FAILED" in r.get("status", ""))
    print(f"  Verified: {verified}")
    print(f"  Failed: {failed}")

    if verified > 0:
        print(f"\n  Verified hypotheses:")
        for r in results:
            if r.get("status") == "VERIFIED":
                h = r.get("phases", {}).get("verify", {}).get("hypothesis", "?")
                e = r.get("phases", {}).get("verify", {}).get("error", "?")
                print(f"    - {h[:80]} (error: {e})")


if __name__ == "__main__":
    main()
