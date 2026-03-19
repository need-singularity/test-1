"""Synthetic State Tracking Benchmark Generator

LLM이 가중치에 암기한 지식으로 절대 풀 수 없는 동적 상태 추적 문제를
무한대로 생성한다. 시드 기반이므로 재현 가능.

5종 문제 유형:
  1. array_ops   — 배열에 SWAP/ADD/REVERSE/SHIFT 다중 연산
  2. coin_flip   — N개 코인의 조건부 뒤집기
  3. register    — 3-레지스터 머신 연산
  4. conditional — IF-ELSE 조건 분기가 포함된 변수 추적
  5. stack_queue — 스택/큐 자료구조 연산 추적

Usage:
    .venv/bin/python synthetic_gen.py --type all --n 20 --steps 12 --seed 2026
    .venv/bin/python synthetic_gen.py --type array_ops --n 50 --steps 8 --difficulty hard
"""
import argparse
import json
import random
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal


# ═══════════════════════════════════════════════════════════════════
#  난이도 프리셋
# ═══════════════════════════════════════════════════════════════════

DIFFICULTY_PRESETS = {
    "easy":   {"steps": 5,  "array_size": 4, "n_coins": 4, "n_regs": 3, "n_vars": 3, "stack_ops": 6},
    "medium": {"steps": 8,  "array_size": 5, "n_coins": 6, "n_regs": 3, "n_vars": 4, "stack_ops": 8},
    "hard":   {"steps": 12, "array_size": 6, "n_coins": 8, "n_regs": 4, "n_vars": 5, "stack_ops": 12},
    "brutal": {"steps": 18, "array_size": 7, "n_coins": 10, "n_regs": 5, "n_vars": 6, "stack_ops": 16},
}


# ═══════════════════════════════════════════════════════════════════
#  1. 배열 다중 연산 (Array Ops)
# ═══════════════════════════════════════════════════════════════════

def gen_array_ops(seed: int, steps: int = 12, array_size: int = 5) -> dict:
    """배열에 SWAP, ADD, REVERSE, SHIFT 연산을 적용하는 문제."""
    r = random.Random(seed)
    state = [r.randint(1, 9) for _ in range(array_size)]
    initial = list(state)

    operations = []
    cot_trace = [f"Initial: {initial}"]

    for _ in range(steps):
        op = r.choice(["SWAP", "ADD", "REVERSE", "SHIFT", "SET", "NEGATE"])

        if op == "SWAP":
            i, j = r.sample(range(array_size), 2)
            operations.append(f"Swap elements at index {i} and {j}")
            state[i], state[j] = state[j], state[i]
            cot_trace.append(f"Swap idx {i},{j} -> {list(state)}")

        elif op == "ADD":
            i = r.randint(0, array_size - 1)
            v = r.randint(1, 5)
            operations.append(f"Add {v} to element at index {i}")
            state[i] += v
            cot_trace.append(f"Add {v} to idx {i} -> {list(state)}")

        elif op == "REVERSE":
            operations.append("Reverse the entire array")
            state.reverse()
            cot_trace.append(f"Reverse -> {list(state)}")

        elif op == "SHIFT":
            direction = r.choice(["left", "right"])
            operations.append(f"Shift array {direction} by 1 (wrap around)")
            if direction == "left":
                state = state[1:] + [state[0]]
            else:
                state = [state[-1]] + state[:-1]
            cot_trace.append(f"Shift {direction} -> {list(state)}")

        elif op == "SET":
            i = r.randint(0, array_size - 1)
            j = r.randint(0, array_size - 1)
            if i != j:
                operations.append(f"Set element at index {i} to the value at index {j}")
                state[i] = state[j]
                cot_trace.append(f"Set idx {i} = idx {j} -> {list(state)}")
            else:
                v = r.randint(1, 9)
                operations.append(f"Set element at index {i} to {v}")
                state[i] = v
                cot_trace.append(f"Set idx {i} = {v} -> {list(state)}")

        elif op == "NEGATE":
            i = r.randint(0, array_size - 1)
            operations.append(f"Negate the element at index {i}")
            state[i] = -state[i]
            cot_trace.append(f"Negate idx {i} -> {list(state)}")

    q_lines = [f"Consider an array initially set to {initial}. "
               f"Perform the following operations in exact order:"]
    for idx, op in enumerate(operations, 1):
        q_lines.append(f"{idx}. {op}")
    q_lines.append(f"What is the final array? Answer strictly as {['a'] * array_size} format.")

    answer = str(state)

    return {
        "id": f"array_{seed}",
        "type": "array_ops",
        "question": "\n".join(q_lines),
        "answer": answer,
        "accept": [answer, answer.replace(" ", "")],
        "cot": "\n".join(cot_trace),
        "difficulty": {"steps": steps, "array_size": array_size},
    }


# ═══════════════════════════════════════════════════════════════════
#  2. 코인 뒤집기 (Coin Flip)
# ═══════════════════════════════════════════════════════════════════

def gen_coin_flip(seed: int, steps: int = 10, n_coins: int = 6) -> dict:
    """N개 코인의 조건부 뒤집기 문제."""
    r = random.Random(seed)
    coins = ["H"] * n_coins
    ops = []
    cot_trace = [f"Initial: {coins}"]

    for _ in range(steps):
        kind = r.choice(["flip", "flip_range", "flip_if", "set_all", "flip_every_other"])

        if kind == "flip":
            idx = r.randint(0, n_coins - 1)
            ops.append(f"Flip coin {idx}")
            coins[idx] = "T" if coins[idx] == "H" else "H"
            cot_trace.append(f"Flip coin {idx} -> {coins}")

        elif kind == "flip_range":
            a = r.randint(0, n_coins - 2)
            b = r.randint(a + 1, n_coins - 1)
            ops.append(f"Flip all coins from {a} to {b}")
            for i in range(a, b + 1):
                coins[i] = "T" if coins[i] == "H" else "H"
            cot_trace.append(f"Flip range [{a},{b}] -> {coins}")

        elif kind == "flip_if":
            target = r.choice(["H", "T"])
            ops.append(f"Flip every coin that is currently {target}")
            coins = [("T" if c == "H" else "H") if c == target else c for c in coins]
            cot_trace.append(f"Flip all {target} -> {coins}")

        elif kind == "set_all":
            val = r.choice(["H", "T"])
            ops.append(f"Set all coins to {val}")
            coins = [val] * n_coins
            cot_trace.append(f"Set all to {val} -> {coins}")

        elif kind == "flip_every_other":
            start = r.choice([0, 1])
            label = "even" if start == 0 else "odd"
            ops.append(f"Flip every coin at {label}-indexed positions")
            for i in range(start, n_coins, 2):
                coins[i] = "T" if coins[i] == "H" else "H"
            cot_trace.append(f"Flip {label}-idx -> {coins}")

    q_lines = [f"You have {n_coins} coins, all starting as H (heads)."]
    for step, op in enumerate(ops, 1):
        q_lines.append(f"Step {step}: {op}")
    q_lines.append("How many coins show H at the end? Answer with just the number.")
    answer = str(coins.count("H"))

    return {
        "id": f"coin_{seed}",
        "type": "coin_flip",
        "question": "\n".join(q_lines),
        "answer": answer,
        "accept": [answer],
        "cot": "\n".join(cot_trace),
        "difficulty": {"steps": steps, "n_coins": n_coins},
    }


# ═══════════════════════════════════════════════════════════════════
#  3. 레지스터 머신 (Register Machine)
# ═══════════════════════════════════════════════════════════════════

def gen_register(seed: int, steps: int = 10, n_regs: int = 3) -> dict:
    """N개 레지스터에 대한 산술 연산 추적."""
    r = random.Random(seed)
    names = [chr(ord("A") + i) for i in range(n_regs)]
    regs = {n: r.randint(1, 9) for n in names}
    regs[names[-1]] = 0  # 마지막 레지스터는 0으로 시작
    init = dict(regs)

    ops = []
    cot_trace = [f"Initial: {init}"]

    for _ in range(steps):
        kind = r.choice(["add", "sub", "mov", "swap", "inc", "mul", "mod"])

        if kind == "add":
            dst, src = r.sample(names, 2)
            ops.append(f"{dst} = {dst} + {src}")
            regs[dst] = regs[dst] + regs[src]
        elif kind == "sub":
            dst, src = r.sample(names, 2)
            ops.append(f"{dst} = {dst} - {src}")
            regs[dst] = regs[dst] - regs[src]
        elif kind == "mov":
            dst, src = r.sample(names, 2)
            ops.append(f"{dst} = {src}")
            regs[dst] = regs[src]
        elif kind == "swap":
            a, b = r.sample(names, 2)
            ops.append(f"Swap {a} and {b}")
            regs[a], regs[b] = regs[b], regs[a]
        elif kind == "inc":
            dst = r.choice(names)
            val = r.randint(1, 5)
            ops.append(f"{dst} = {dst} + {val}")
            regs[dst] = regs[dst] + val
        elif kind == "mul":
            dst, src = r.sample(names, 2)
            ops.append(f"{dst} = {dst} * {src}")
            regs[dst] = regs[dst] * regs[src]
        elif kind == "mod":
            dst = r.choice(names)
            val = r.randint(2, 7)
            ops.append(f"{dst} = {dst} mod {val}")
            regs[dst] = regs[dst] % val

        cot_trace.append(f"{ops[-1]} -> {dict(regs)}")

    target = r.choice(names)
    q_lines = [f"Registers start as: {', '.join(f'{n}={init[n]}' for n in names)}"]
    for step, op in enumerate(ops, 1):
        q_lines.append(f"Step {step}: {op}")
    q_lines.append(f"What is the value of {target}? Answer with just the number.")
    answer = str(regs[target])

    return {
        "id": f"reg_{seed}",
        "type": "register",
        "question": "\n".join(q_lines),
        "answer": answer,
        "accept": [answer],
        "cot": "\n".join(cot_trace),
        "difficulty": {"steps": steps, "n_regs": n_regs},
    }


# ═══════════════════════════════════════════════════════════════════
#  4. 조건부 분기 (Conditional)
# ═══════════════════════════════════════════════════════════════════

def gen_conditional(seed: int, steps: int = 10, n_vars: int = 4) -> dict:
    """IF-ELSE 조건 분기가 포함된 변수 추적 문제."""
    r = random.Random(seed)
    var_names = [f"x{i}" for i in range(n_vars)]
    state = {v: r.randint(0, 9) for v in var_names}
    init = dict(state)

    ops = []
    cot_trace = [f"Initial: {init}"]

    for _ in range(steps):
        kind = r.choice(["assign", "add", "if_gt", "if_eq", "swap"])

        if kind == "assign":
            dst = r.choice(var_names)
            val = r.randint(0, 9)
            ops.append(f"Set {dst} = {val}")
            state[dst] = val

        elif kind == "add":
            dst = r.choice(var_names)
            val = r.randint(-5, 5)
            sign = f"+{val}" if val >= 0 else str(val)
            ops.append(f"{dst} = {dst} {sign}")
            state[dst] += val

        elif kind == "if_gt":
            a, b = r.sample(var_names, 2)
            target = r.choice(var_names)
            v_true = r.randint(0, 9)
            v_false = r.randint(0, 9)
            ops.append(f"If {a} > {b}, set {target} = {v_true}; else set {target} = {v_false}")
            if state[a] > state[b]:
                state[target] = v_true
                cot_trace.append(f"{a}({state[a]}) > {b}({state[b]})? YES -> {target}={v_true}")
            else:
                state[target] = v_false
                cot_trace.append(f"{a}({state[a]}) > {b}({state[b]})? NO -> {target}={v_false}")
            # cot already appended, skip the generic one below
            ops_text = ops[-1]
            cot_trace[-1] = f"{ops_text} | {cot_trace[-1]} -> {dict(state)}"
            continue

        elif kind == "if_eq":
            a = r.choice(var_names)
            val = r.randint(0, 9)
            target = r.choice(var_names)
            v_true = r.randint(0, 9)
            ops.append(f"If {a} == {val}, set {target} = {v_true}; else {target} unchanged")
            if state[a] == val:
                state[target] = v_true
                cot_trace.append(f"{a}=={val}? YES -> {target}={v_true} -> {dict(state)}")
            else:
                cot_trace.append(f"{a}=={val}? NO -> no change -> {dict(state)}")
            continue

        elif kind == "swap":
            a, b = r.sample(var_names, 2)
            ops.append(f"Swap {a} and {b}")
            state[a], state[b] = state[b], state[a]

        cot_trace.append(f"{ops[-1]} -> {dict(state)}")

    target = r.choice(var_names)
    q_lines = [f"Variables start as: {', '.join(f'{v}={init[v]}' for v in var_names)}"]
    for step, op in enumerate(ops, 1):
        q_lines.append(f"Step {step}: {op}")
    q_lines.append(f"What is the value of {target}? Answer with just the number.")
    answer = str(state[target])

    return {
        "id": f"cond_{seed}",
        "type": "conditional",
        "question": "\n".join(q_lines),
        "answer": answer,
        "accept": [answer],
        "cot": "\n".join(cot_trace),
        "difficulty": {"steps": steps, "n_vars": n_vars},
    }


# ═══════════════════════════════════════════════════════════════════
#  5. 스택/큐 연산 (Stack & Queue)
# ═══════════════════════════════════════════════════════════════════

def gen_stack_queue(seed: int, steps: int = 10, **_) -> dict:
    """스택과 큐에 대한 push/pop/peek 연산 추적."""
    r = random.Random(seed)
    stack: list[int] = []
    queue: list[int] = []

    ops = []
    cot_trace = ["Initial: stack=[], queue=[]"]

    for _ in range(steps):
        kind = r.choice(["push_s", "push_q", "pop_s", "pop_q",
                          "push_s", "push_q", "move_sq", "move_qs"])

        if kind == "push_s":
            v = r.randint(1, 9)
            ops.append(f"Push {v} onto stack")
            stack.append(v)
        elif kind == "push_q":
            v = r.randint(1, 9)
            ops.append(f"Enqueue {v} into queue")
            queue.append(v)
        elif kind == "pop_s":
            if stack:
                ops.append("Pop from stack (discard)")
                stack.pop()
            else:
                v = r.randint(1, 9)
                ops.append(f"Push {v} onto stack")
                stack.append(v)
        elif kind == "pop_q":
            if queue:
                ops.append("Dequeue from queue (discard)")
                queue.pop(0)
            else:
                v = r.randint(1, 9)
                ops.append(f"Enqueue {v} into queue")
                queue.append(v)
        elif kind == "move_sq":
            if stack:
                ops.append("Pop from stack and enqueue into queue")
                queue.append(stack.pop())
            else:
                v = r.randint(1, 9)
                ops.append(f"Push {v} onto stack")
                stack.append(v)
        elif kind == "move_qs":
            if queue:
                ops.append("Dequeue from queue and push onto stack")
                stack.append(queue.pop(0))
            else:
                v = r.randint(1, 9)
                ops.append(f"Enqueue {v} into queue")
                queue.append(v)

        cot_trace.append(f"{ops[-1]} -> stack={list(stack)}, queue={list(queue)}")

    # 질문: 스택 top 또는 큐 front 또는 크기
    q_kind = r.choice(["stack_top", "queue_front", "stack_size", "queue_size"])
    if q_kind == "stack_top" and stack:
        question_suffix = "What is the top element of the stack? Answer with just the number."
        answer = str(stack[-1])
    elif q_kind == "queue_front" and queue:
        question_suffix = "What is the front element of the queue? Answer with just the number."
        answer = str(queue[0])
    elif q_kind == "stack_size":
        question_suffix = "How many elements are in the stack? Answer with just the number."
        answer = str(len(stack))
    else:
        question_suffix = "How many elements are in the queue? Answer with just the number."
        answer = str(len(queue))

    q_lines = ["You have an empty stack and an empty queue."]
    for step, op in enumerate(ops, 1):
        q_lines.append(f"Step {step}: {op}")
    q_lines.append(question_suffix)

    return {
        "id": f"sq_{seed}",
        "type": "stack_queue",
        "question": "\n".join(q_lines),
        "answer": answer,
        "accept": [answer],
        "cot": "\n".join(cot_trace),
        "difficulty": {"steps": steps},
    }


# ═══════════════════════════════════════════════════════════════════
#  생성기 레지스트리
# ═══════════════════════════════════════════════════════════════════

GENERATORS = {
    "array_ops": gen_array_ops,
    "coin_flip": gen_coin_flip,
    "register": gen_register,
    "conditional": gen_conditional,
    "stack_queue": gen_stack_queue,
}


# ═══════════════════════════════════════════════════════════════════
#  메인: 배치 생성 + ICL 파이프라인 호환 출력
# ═══════════════════════════════════════════════════════════════════

def generate_batch(
    task_type: str = "all",
    n: int = 20,
    seed: int = 2026,
    difficulty: str = "hard",
    custom_steps: int | None = None,
) -> list[dict]:
    """태스크 배치를 생성한다.

    Args:
        task_type: 생성할 문제 유형 ('all' 이면 균등 분배)
        n: 생성할 문제 수
        seed: 랜덤 시드
        difficulty: easy/medium/hard/brutal
        custom_steps: 지정하면 difficulty의 steps를 오버라이드
    """
    preset = DIFFICULTY_PRESETS[difficulty]
    steps = custom_steps or preset["steps"]

    if task_type == "all":
        types = list(GENERATORS.keys())
    elif "," in task_type:
        types = [t.strip() for t in task_type.split(",")]
    else:
        types = [task_type]

    tasks = []
    for i in range(n):
        t = types[i % len(types)]
        s = seed + i * 7  # 기존 icl_phase_transition.py와 동일한 시드 간격

        kwargs = {"seed": s, "steps": steps}
        if t == "array_ops":
            kwargs["array_size"] = preset["array_size"]
        elif t == "coin_flip":
            kwargs["n_coins"] = preset["n_coins"]
        elif t == "register":
            kwargs["n_regs"] = preset["n_regs"]
        elif t == "conditional":
            kwargs["n_vars"] = preset["n_vars"]

        tasks.append(GENERATORS[t](**kwargs))

    return tasks


def generate_exemplars(n_per_type: int = 2, seed: int = 9999) -> list[dict]:
    """Few-shot 예시용 짧은 문제를 CoT 포함하여 생성한다."""
    exemplars = []
    for t_name, gen_fn in GENERATORS.items():
        for i in range(n_per_type):
            s = seed + hash(t_name) % 10000 + i * 3
            kwargs = {"seed": s, "steps": 3}
            if t_name == "array_ops":
                kwargs["array_size"] = 3
            elif t_name == "coin_flip":
                kwargs["n_coins"] = 3
            elif t_name == "register":
                kwargs["n_regs"] = 3
            elif t_name == "conditional":
                kwargs["n_vars"] = 3

            task = gen_fn(**kwargs)
            exemplars.append({
                "type": task["type"],
                "q": task["question"],
                "a": task["cot"] + f"\nAnswer: {task['answer']}",
            })
    return exemplars


def main():
    parser = argparse.ArgumentParser(description="Synthetic State Tracking Benchmark Generator")
    parser.add_argument("--type", default="all",
                        help="Task type(s): all, or comma-separated e.g. conditional,stack_queue")
    parser.add_argument("--n", type=int, default=20, help="Number of tasks to generate")
    parser.add_argument("--steps", type=int, default=None, help="Override step count")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--difficulty", default="hard", choices=list(DIFFICULTY_PRESETS.keys()))
    parser.add_argument("--output", default="results/synthetic_tasks.json")
    parser.add_argument("--exemplars", action="store_true", help="Also generate few-shot exemplars")
    args = parser.parse_args()

    tasks = generate_batch(
        task_type=args.type,
        n=args.n,
        seed=args.seed,
        difficulty=args.difficulty,
        custom_steps=args.steps,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    output = {"tasks": tasks, "meta": {
        "type": args.type, "n": args.n, "seed": args.seed,
        "difficulty": args.difficulty, "steps": args.steps or DIFFICULTY_PRESETS[args.difficulty]["steps"],
    }}

    if args.exemplars:
        output["exemplars"] = generate_exemplars(seed=args.seed + 7777)

    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(tasks)} tasks -> {out_path}")
    print(f"  Types: {', '.join(set(t['type'] for t in tasks))}")
    print(f"  Difficulty: {args.difficulty} ({DIFFICULTY_PRESETS[args.difficulty]})")

    # 샘플 출력
    sample = tasks[0]
    print(f"\n--- Sample (id={sample['id']}) ---")
    print(sample["question"])
    print(f"\nAnswer: {sample['answer']}")
    print(f"\nCoT trace:\n{sample['cot']}")


if __name__ == "__main__":
    main()
