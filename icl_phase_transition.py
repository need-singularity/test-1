"""ICL Phase Transition Detector

Few-shot 예시 수(k=0..8)를 늘리며 실제 LLM 정답률과
CoT 텍스트의 위상 구조(β₁)를 동시 측정한다.
두 지표가 동시에 불연속 점프하는 임계점 = 상전이.

Usage:
    .venv/bin/python icl_phase_transition.py [--trials 5] [--max-k 8] [--output results/icl_phase.json]
"""
import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import networkx as nx
import numpy as np

# 동시 호출 제한 (claude CLI가 터지지 않도록)
MAX_CONCURRENT = 5


# ═══════════════════════════════════════════════════════════════════
#  1. 벤치마크 태스크 (정답이 확정된 문제들)
# ═══════════════════════════════════════════════════════════════════

TASKS = [
    # ── 모듈러 산술 / 정수론 ──
    {
        "id": "hard_01",
        "type": "number_theory",
        "question": "What is the remainder when 2^2026 is divided by 7?",
        "answer": "2",
        "accept": ["2"],
    },
    {
        "id": "hard_02",
        "type": "number_theory",
        "question": "How many trailing zeros are in 100! (100 factorial)?",
        "answer": "24",
        "accept": ["24"],
    },
    {
        "id": "hard_03",
        "type": "number_theory",
        "question": "What is the last digit of 3^4567?",
        "answer": "7",
        "accept": ["7"],
    },
    # ── 기호 대수 ──
    {
        "id": "hard_04",
        "type": "algebra",
        "question": "If x + 1/x = 3, what is the value of x^3 + 1/x^3?",
        "answer": "18",
        "accept": ["18"],
    },
    {
        "id": "hard_05",
        "type": "algebra",
        "question": "The area of a triangle with sides 13, 14, and 15 is?",
        "answer": "84",
        "accept": ["84"],
    },
    # ── 조합론 / 확률 ──
    {
        "id": "hard_06",
        "type": "combinatorics",
        "question": "How many diagonals does a regular icosagon (20-sided polygon) have?",
        "answer": "170",
        "accept": ["170"],
    },
    {
        "id": "hard_07",
        "type": "combinatorics",
        "question": "A bag has 3 red and 4 blue marbles. Two are drawn without replacement. The probability they are the same color is P/Q in simplest form. What is P+Q?",
        "answer": "10",
        "accept": ["10"],
    },
    # ── 논리 퍼즐 (비자명) ──
    {
        "id": "hard_08",
        "type": "logic",
        "question": "A says 'We are both knaves'. B says nothing. In a knights-and-knaves puzzle where knights always tell the truth and knaves always lie, who is the knight? Answer with just 'A' or 'B'.",
        "answer": "B",
        "accept": ["B", "b"],
    },
    {
        "id": "hard_09",
        "type": "logic",
        "question": "Five people A,B,C,D,E are ranked by height. A>B, C<A, C>B, D>C, E<B. Who is the shortest? Answer with a single letter.",
        "answer": "E",
        "accept": ["E", "e"],
    },
    # ── 다단계 응용 ──
    {
        "id": "hard_10",
        "type": "multihop",
        "question": "In 10 years, John will be twice as old as he was 5 years ago. How old is John now?",
        "answer": "20",
        "accept": ["20"],
    },
]


# ═══════════════════════════════════════════════════════════════════
#  2. Few-shot 예시 풀 (태스크와 다른 문제들)
# ═══════════════════════════════════════════════════════════════════

EXEMPLARS = [
    {
        "type": "number_theory",
        "q": "What is the remainder when 7^100 is divided by 5?",
        "a": "7 mod 5 = 2. Powers of 2 mod 5 cycle: 2,4,3,1 (period 4). 100 mod 4 = 0, so 7^100 mod 5 = 2^100 mod 5 = 1. Answer: 1",
    },
    {
        "type": "number_theory",
        "q": "How many trailing zeros are in 50!?",
        "a": "Count factors of 5: floor(50/5)=10, floor(50/25)=2. Total=12. Answer: 12",
    },
    {
        "type": "algebra",
        "q": "If x + 1/x = 5, what is x^2 + 1/x^2?",
        "a": "Square both sides: (x+1/x)^2 = x^2 + 2 + 1/x^2 = 25. So x^2+1/x^2 = 23. Answer: 23",
    },
    {
        "type": "combinatorics",
        "q": "How many diagonals does a regular 12-sided polygon have?",
        "a": "Formula: n(n-3)/2. 12(12-3)/2 = 12*9/2 = 54. Answer: 54",
    },
    {
        "type": "logic",
        "q": "On an island, A says 'I am a knave'. Is A a knight or a knave?",
        "a": "If A is a knight, he tells truth, but a knight can't say 'I am a knave' (contradiction). If A is a knave, he lies, so 'I am a knave' is false, meaning he's a knight (contradiction). This statement is a paradox — but in standard puzzles, A cannot make this statement, so we deduce A is a knave. Answer: knave",
    },
    {
        "type": "combinatorics",
        "q": "A box has 5 red, 3 blue balls. Draw 2 without replacement. Probability both red?",
        "a": "P = C(5,2)/C(8,2) = 10/28 = 5/14. Answer: 5/14",
    },
]


# ═══════════════════════════════════════════════════════════════════
#  3. Claude CLI 호출 (async 병렬)
# ═══════════════════════════════════════════════════════════════════

_semaphore: asyncio.Semaphore | None = None


async def claude_call_async(prompt: str, timeout: int = 90) -> str:
    """Claude CLI를 비동기로 호출한다. semaphore로 동시성 제한."""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async with _semaphore:
        try:
            proc = await asyncio.create_subprocess_exec(
                "claude", "-p", prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            if proc.returncode != 0:
                return ""
            return stdout.decode().strip()
        except (asyncio.TimeoutError, Exception):
            return ""


def claude_call(prompt: str, timeout: int = 60) -> str:
    """동기 호출 (fallback용)."""
    try:
        r = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode != 0:
            return ""
        return r.stdout.strip()
    except (subprocess.TimeoutExpired, Exception):
        return ""


# ═══════════════════════════════════════════════════════════════════
#  4. 프롬프트 조립
# ═══════════════════════════════════════════════════════════════════

def build_prompt(question: str, task_type: str, k: int) -> str:
    """k개의 few-shot 예시를 포함한 프롬프트를 조립한다."""

    # 태스크 타입에 맞는 예시 우선, 부족하면 다른 타입에서 보충
    typed = [e for e in EXEMPLARS if e["type"] == task_type]
    others = [e for e in EXEMPLARS if e["type"] != task_type]
    pool = typed + others
    examples = pool[:k]

    parts = []
    parts.append("다음 문제를 단계별로 풀어라. 최종 답을 반드시 '답: ...' 형식으로 마지막에 써라.")

    if examples:
        parts.append("\n--- 예시 ---")
        for i, ex in enumerate(examples, 1):
            parts.append(f"\n예시 {i}:")
            parts.append(f"문제: {ex['q']}")
            parts.append(f"풀이: {ex['a']}")
        parts.append("\n--- 본 문제 ---")

    parts.append(f"\n문제: {question}")
    parts.append("풀이:")

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════
#  5. 정답 판정
# ═══════════════════════════════════════════════════════════════════

def check_answer(response: str, task: dict) -> bool:
    """응답에서 정답 포함 여부를 확인한다."""
    resp_lower = response.lower().strip()
    for acc in task["accept"]:
        if acc.lower() in resp_lower:
            return True
    return False


# ═══════════════════════════════════════════════════════════════════
#  6. CoT → 방향 그래프 변환 + β₁ 측정
# ═══════════════════════════════════════════════════════════════════

# 자기참조/교정을 나타내는 패턴
BACKREF_PATTERNS = [
    r"앞서|위에서|이전|다시\s*보면|돌아가|재확인|검토|검증",
    r"그런데|하지만|아니[,.]|잠깐|틀렸|수정|실수|다시\s*계산",
    r"따라서|그러므로|결론|정리하면|종합하면",
    r"step\s*\d|단계\s*\d|\d단계|\(\d\)",
]
BACKREF_RE = re.compile("|".join(BACKREF_PATTERNS), re.IGNORECASE)

# 명시적 단계 참조 (e.g., "1단계에서", "step 2")
STEP_REF_RE = re.compile(r"(?:step\s*|단계\s*|)(\d+)(?:단계|에서|의|번)", re.IGNORECASE)


def cot_to_graph(text: str) -> nx.DiGraph:
    """CoT 텍스트를 방향 그래프로 변환한다.

    - 각 문장 = 노드
    - 순차 연결 (i → i+1)
    - 역참조/자기교정 패턴 감지 시 역방향 엣지 추가
    - 명시적 단계 참조 시 해당 노드로 엣지 추가
    """
    # 문장 분리 (마침표, 줄바꿈 기준)
    sentences = re.split(r'[.\n!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 3]

    if not sentences:
        return nx.DiGraph()

    G = nx.DiGraph()
    for i, sent in enumerate(sentences):
        G.add_node(i, text=sent[:80])

    # 순차 엣지
    for i in range(len(sentences) - 1):
        G.add_edge(i, i + 1, type="sequential")

    # 역참조/교정 엣지
    for i, sent in enumerate(sentences):
        if BACKREF_RE.search(sent):
            # 최근 3~5개 노드 중 하나로 역방향 엣지
            for j in range(max(0, i - 5), i):
                # 간단한 휴리스틱: 교정 패턴이면 역방향
                if any(kw in sent for kw in ["다시", "틀렸", "수정", "아니", "잠깐", "하지만", "그런데"]):
                    G.add_edge(i, j, type="correction")
                    break  # 가장 가까운 노드 하나만
                elif any(kw in sent for kw in ["따라서", "그러므로", "종합", "결론"]):
                    # 종합은 여러 이전 노드 참조
                    G.add_edge(i, j, type="synthesis")

        # 명시적 단계 참조
        refs = STEP_REF_RE.findall(sent)
        for ref_num in refs:
            target = int(ref_num) - 1  # 1-indexed → 0-indexed
            if 0 <= target < len(sentences) and target != i:
                G.add_edge(i, target, type="explicit_ref")

    return G


def compute_betti_1(G: nx.DiGraph) -> int:
    """β₁ = E - V + C (무방향 변환 후). 독립 루프 수."""
    if G.number_of_nodes() == 0:
        return 0
    U = G.to_undirected()
    V = U.number_of_nodes()
    E = U.number_of_edges()
    C = nx.number_connected_components(U)
    return max(0, E - V + C)


def graph_metrics(G: nx.DiGraph) -> dict:
    """그래프의 위상적 메트릭들을 계산한다."""
    if G.number_of_nodes() == 0:
        return {"nodes": 0, "edges": 0, "betti_1": 0, "correction_edges": 0,
                "synthesis_edges": 0, "density": 0.0, "avg_path": 0.0}

    correction = sum(1 for _, _, d in G.edges(data=True) if d.get("type") == "correction")
    synthesis = sum(1 for _, _, d in G.edges(data=True) if d.get("type") == "synthesis")
    explicit = sum(1 for _, _, d in G.edges(data=True) if d.get("type") == "explicit_ref")

    U = G.to_undirected()
    try:
        if nx.is_connected(U):
            avg_path = nx.average_shortest_path_length(U)
        else:
            components = [U.subgraph(c) for c in nx.connected_components(U)]
            avg_path = np.mean([nx.average_shortest_path_length(c)
                                for c in components if c.number_of_nodes() > 1]) if components else 0.0
    except Exception:
        avg_path = 0.0

    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "betti_1": compute_betti_1(G),
        "correction_edges": correction,
        "synthesis_edges": synthesis,
        "explicit_ref_edges": explicit,
        "non_sequential_edges": correction + synthesis + explicit,
        "density": nx.density(G),
        "avg_path": round(float(avg_path), 3),
    }


# ═══════════════════════════════════════════════════════════════════
#  7. 상전이 감지
# ═══════════════════════════════════════════════════════════════════

def detect_phase_transition(k_values: list[int], metric_values: list[float]) -> dict | None:
    """인접 k 값 사이의 최대 점프를 찾는다. 유의미한 점프가 있으면 반환."""
    if len(k_values) < 3:
        return None

    max_jump = 0
    transition_k = None

    for i in range(1, len(metric_values)):
        jump = metric_values[i] - metric_values[i - 1]
        if jump > max_jump:
            max_jump = jump
            transition_k = k_values[i]

    # 전체 범위 대비 점프 크기
    total_range = max(metric_values) - min(metric_values)
    if total_range == 0:
        return None

    jump_ratio = max_jump / total_range

    if jump_ratio > 0.3:  # 전체 변화의 30% 이상이 한 구간에서 발생
        return {
            "transition_k": transition_k,
            "jump_magnitude": round(max_jump, 4),
            "jump_ratio": round(jump_ratio, 4),
            "is_sharp": jump_ratio > 0.5,
        }
    return None


# ═══════════════════════════════════════════════════════════════════
#  8. 메인 실험 루프 (async 병렬)
# ═══════════════════════════════════════════════════════════════════

async def eval_single(k: int, trial: int, task: dict) -> dict:
    """단일 (k, trial, task) 조합을 평가한다."""
    prompt = build_prompt(task["question"], task["type"], k)
    t0 = time.monotonic()
    response = await claude_call_async(prompt)
    elapsed = time.monotonic() - t0

    if not response:
        return {
            "k": k, "trial": trial, "task_id": task["id"], "task_type": task["type"],
            "correct": False, "betti_1": 0, "correction_edges": 0,
            "nodes": 0, "edges": 0, "non_sequential": 0,
            "response_length": 0, "response_text": "", "elapsed": round(elapsed, 1),
            "empty": True,
        }

    is_correct = check_answer(response, task)
    G = cot_to_graph(response)
    metrics = graph_metrics(G)

    return {
        "k": k, "trial": trial, "task_id": task["id"], "task_type": task["type"],
        "correct": is_correct,
        "betti_1": metrics["betti_1"],
        "correction_edges": metrics["correction_edges"],
        "nodes": metrics["nodes"],
        "edges": metrics["edges"],
        "non_sequential": metrics["non_sequential_edges"],
        "response_length": len(response),
        "response_text": response,
        "elapsed": round(elapsed, 1),
        "empty": False,
    }


async def run_k_batch(k: int, trials: int, tasks: list[dict]) -> list[dict]:
    """k값 하나에 대해 모든 (trial × task) 조합을 병렬 실행한다."""
    jobs = []
    for trial in range(trials):
        for task in tasks:
            jobs.append(eval_single(k, trial, task))

    # 동시에 발사 (semaphore가 MAX_CONCURRENT로 제한)
    return await asyncio.gather(*jobs)


async def run_experiment_async(max_k: int = 8, trials: int = 5, output_path: str = "results/icl_phase.json",
                               k_values: list[int] | None = None):
    """k값들에 대해 병렬 실행, 정답률과 β₁을 측정한다."""
    if k_values is None:
        k_values = list(range(0, max_k + 1))
    total_calls = len(k_values) * trials * len(TASKS)

    print("=" * 70)
    print("  ICL Phase Transition Experiment (ASYNC)")
    print(f"  k = {k_values}, trials = {trials}, tasks = {len(TASKS)}")
    print(f"  총 LLM 호출: {total_calls}회, 동시 {MAX_CONCURRENT}개")
    est_min = max(1, total_calls * 15 // MAX_CONCURRENT // 60)
    print(f"  예상 시간: ~{est_min}분 (직렬 대비 {MAX_CONCURRENT}x 가속)")
    print("=" * 70)

    results = {
        "config": {"max_k": max_k, "trials": trials, "n_tasks": len(TASKS),
                    "max_concurrent": MAX_CONCURRENT, "mode": "async"},
        "data": [],
        "raw": [],
        "transitions": {},
    }

    k_accuracy = {}
    k_betti = {}
    k_corrections = {}

    t_start = time.monotonic()

    for k in k_values:
        print(f"\n{'─'*50}")
        print(f"  k = {k} (few-shot examples) — {trials * len(TASKS)}건 병렬 발사")
        print(f"{'─'*50}")

        t_k = time.monotonic()
        batch_results = await run_k_batch(k, trials, TASKS)
        elapsed_k = time.monotonic() - t_k

        # 결과 집계
        results["raw"].extend(batch_results)

        empties = sum(1 for r in batch_results if r["empty"])
        if empties:
            print(f"    [!] {empties}건 빈 응답")

        # trial별 집계
        trial_accuracies = []
        trial_betti = []
        trial_corrections = []

        for trial in range(trials):
            trial_data = [r for r in batch_results if r["trial"] == trial and not r["empty"]]
            if not trial_data:
                continue
            acc = sum(r["correct"] for r in trial_data) / len(trial_data)
            avg_b = sum(r["betti_1"] for r in trial_data) / len(trial_data)
            avg_c = sum(r["correction_edges"] for r in trial_data) / len(trial_data)

            trial_accuracies.append(acc)
            trial_betti.append(avg_b)
            trial_corrections.append(avg_c)

            print(f"    trial {trial+1}: acc={acc:.0%}, β₁={avg_b:.2f}, corr={avg_c:.1f}")

        mean_acc = float(np.mean(trial_accuracies)) if trial_accuracies else 0
        mean_betti = float(np.mean(trial_betti)) if trial_betti else 0
        mean_corr = float(np.mean(trial_corrections)) if trial_corrections else 0
        std_acc = float(np.std(trial_accuracies)) if trial_accuracies else 0

        k_accuracy[k] = mean_acc
        k_betti[k] = mean_betti
        k_corrections[k] = mean_corr

        results["data"].append({
            "k": k,
            "accuracy_mean": round(mean_acc, 4),
            "accuracy_std": round(std_acc, 4),
            "betti_1_mean": round(mean_betti, 4),
            "corrections_mean": round(mean_corr, 4),
            "elapsed_sec": round(elapsed_k, 1),
        })

        print(f"  → k={k}: acc={mean_acc:.0%} ± {std_acc:.0%}, β₁={mean_betti:.3f} [{elapsed_k:.0f}s]")

        # 중간 저장
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    total_elapsed = time.monotonic() - t_start

    # ── 상전이 감지 ──
    print(f"\n{'='*70}")
    print(f"  Phase Transition Analysis (total: {total_elapsed:.0f}s)")
    print(f"{'='*70}")

    ks = k_values
    accs = [k_accuracy[k] for k in ks]
    bettis = [k_betti[k] for k in ks]
    corrs = [k_corrections[k] for k in ks]

    acc_transition = detect_phase_transition(ks, accs)
    betti_transition = detect_phase_transition(ks, bettis)
    corr_transition = detect_phase_transition(ks, corrs)

    results["transitions"] = {
        "accuracy": acc_transition,
        "betti_1": betti_transition,
        "corrections": corr_transition,
    }
    results["total_elapsed_sec"] = round(total_elapsed, 1)

    if acc_transition:
        print(f"\n  정답률 상전이: k={acc_transition['transition_k']}에서 점프")
        print(f"    크기: {acc_transition['jump_magnitude']:.4f} ({acc_transition['jump_ratio']:.0%} of range)")
        print(f"    급격한 전이: {'YES' if acc_transition['is_sharp'] else 'no'}")
    else:
        print(f"\n  정답률: 뚜렷한 상전이 없음 (점진적 변화)")

    if betti_transition:
        print(f"\n  β₁ 상전이: k={betti_transition['transition_k']}에서 점프")
        print(f"    크기: {betti_transition['jump_magnitude']:.4f} ({betti_transition['jump_ratio']:.0%} of range)")
        print(f"    급격한 전이: {'YES' if betti_transition['is_sharp'] else 'no'}")
    else:
        print(f"\n  β₁: 뚜렷한 상전이 없음")

    # 동시 전이 확인
    if acc_transition and betti_transition:
        if acc_transition["transition_k"] == betti_transition["transition_k"]:
            print(f"\n  ★ 동시 상전이 발견! k={acc_transition['transition_k']}")
            print(f"    정답률과 위상 복잡도가 같은 임계점에서 동시에 점프")
            results["transitions"]["simultaneous"] = True
            results["transitions"]["critical_k"] = acc_transition["transition_k"]
        else:
            delta = abs(acc_transition["transition_k"] - betti_transition["transition_k"])
            print(f"\n  정답률 전이(k={acc_transition['transition_k']})와 "
                  f"β₁ 전이(k={betti_transition['transition_k']}) 간격: {delta}")
            results["transitions"]["simultaneous"] = False

    # ── ASCII 그래프 ──
    print(f"\n{'─'*50}")
    print("  accuracy by k")
    print(f"{'─'*50}")
    for k in ks:
        bar_len = int(k_accuracy[k] * 40)
        bar = "█" * bar_len + "░" * (40 - bar_len)
        print(f"  k={k}: {bar} {k_accuracy[k]:.0%}")

    print(f"\n{'─'*50}")
    print("  β₁ by k")
    print(f"{'─'*50}")
    max_b = max(bettis) if max(bettis) > 0 else 1
    for k in ks:
        bar_len = int((k_betti[k] / max_b) * 40) if max_b > 0 else 0
        bar = "█" * bar_len + "░" * (40 - bar_len)
        print(f"  k={k}: {bar} {k_betti[k]:.2f}")

    # 최종 저장
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n  Results saved to {output_path}")
    print(f"  Total time: {total_elapsed:.0f}s ({total_calls} calls, {MAX_CONCURRENT} concurrent)")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ICL Phase Transition Detector")
    parser.add_argument("--max-k", type=int, default=6, help="Maximum few-shot examples")
    parser.add_argument("--k-values", type=str, default=None, help="Specific k values, e.g. '0,2,4,6'")
    parser.add_argument("--trials", type=int, default=5, help="Trials per k value")
    parser.add_argument("--concurrency", type=int, default=5, help="Max concurrent CLI calls")
    parser.add_argument("--output", default="results/icl_phase_hard.json")
    args = parser.parse_args()

    MAX_CONCURRENT = args.concurrency
    k_vals = [int(x) for x in args.k_values.split(",")] if args.k_values else None
    asyncio.run(run_experiment_async(
        max_k=args.max_k, trials=args.trials,
        output_path=args.output, k_values=k_vals,
    ))
