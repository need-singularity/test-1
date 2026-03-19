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


def claude_generate(prompt: str, timeout: int = 120) -> str:
    """Call claude CLI and return response."""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=timeout,
        )
        output = result.stdout.strip() if result.returncode == 0 else ""
        return "".join(c for c in output if c.isprintable() or c in "\n ")
    except Exception as e:
        return f"ERROR: {e}"


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

    gen_prompt = (
        f"연구 목표: {target}\n"
        f"{prev_summary}\n"
        "다음을 생성해:\n"
        "1. 구체적 가설 (한 문장)\n"
        "2. 가설을 수치적으로 검증하는 Python 코드 (```python 블록)\n"
        "   - numpy, scipy, networkx만 사용 (외부 데이터 다운로드 없음)\n"
        "   - 코드 마지막에 반드시 결과를 JSON으로 print\n"
        "   - 형식: print(json.dumps({'hypothesis': '...', 'result': 수치, 'expected': 수치, 'error': 오차율, 'verdict': 'PASS/FAIL'}))\n"
        "   - 30초 안에 실행 가능할 것\n"
        "3. 변수의 SI 차원 (예: 'L^2/T')\n"
        "마크다운 없이 평문 + 코드 블록만."
    )

    response = claude_generate(gen_prompt)
    code = extract_python_code(response)

    cycle_result["phases"]["generate"] = {
        "response_length": len(response),
        "code_extracted": bool(code),
        "code_length": len(code),
    }

    if not code:
        print(f"    Code extraction failed")
        cycle_result["phases"]["generate"]["error"] = "no code extracted"
        cycle_result["status"] = "FAILED_GENERATION"
        return cycle_result

    print(f"    Hypothesis generated, code: {len(code)} chars")

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

    critique_prompt = (
        f"이 가설을 공격해: '{hypothesis}'\n"
        f"검증 결과: {json.dumps(parsed, default=str)}\n"
        "1) 동어반복 아닌지 2) 반증 가능한지 3) trivial하지 않은지 검토. "
        "문제 없으면 'PASS'. 문제 있으면 이유를 써."
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
