"""문자열 조작 문제 생성기 — LLM의 구조적 약점을 공략한다.

출력: tasks.json (icl_phase_transition.py --tasks-file로 주입)
"""
import json
import random
from collections import Counter

WORDS = [
    "STRAWBERRY", "COMPUTATION", "INTELLIGENCE", "PHILOSOPHICAL",
    "EXTRAORDINARY", "CONSCIOUSNESS", "REPRESENTATIVE", "COMMUNICATION",
    "UNDERSTANDING", "REFRIGERATOR", "PERPENDICULAR", "SOPHISTICATED",
    "APPROXIMATELY", "ENTREPRENEURSHIP", "ACKNOWLEDGEMENT", "INFRASTRUCTURE",
]


def gen_char_at_pos(seed: int) -> dict:
    r = random.Random(seed)
    word = r.choice(WORDS)
    pos = r.randint(1, len(word))
    answer = word[pos - 1]
    return {
        "id": f"charAt_{seed}",
        "type": "string_manipulation",
        "question": f"What is the {pos}th letter of the word '{word}'? Answer with just the single letter.",
        "answer": answer,
        "accept": [answer, answer.lower()],
    }


def gen_reverse_char(seed: int) -> dict:
    r = random.Random(seed)
    word = r.choice(WORDS)
    rev = word[::-1]
    pos = r.randint(1, len(word))
    answer = rev[pos - 1]
    return {
        "id": f"revChar_{seed}",
        "type": "string_manipulation",
        "question": f"Reverse the word '{word}'. What is the {pos}th letter of the reversed word? Answer with just the single letter.",
        "answer": answer,
        "accept": [answer, answer.lower()],
    }


def gen_count_letter(seed: int) -> dict:
    r = random.Random(seed)
    word = r.choice(WORDS)
    counts = Counter(word)
    candidates = [ch for ch, cnt in counts.items() if cnt >= 2]
    if not candidates:
        candidates = list(counts.keys())
    letter = r.choice(candidates)
    answer = str(counts[letter])
    return {
        "id": f"count_{seed}",
        "type": "string_manipulation",
        "question": f"How many times does the letter '{letter}' appear in the word '{word}'? Answer with just the number.",
        "answer": answer,
        "accept": [answer],
    }


def gen_multi_extract(seed: int) -> dict:
    r = random.Random(seed)
    word = r.choice([w for w in WORDS if len(w) >= 10])
    n_picks = r.randint(3, 5)
    positions = sorted(r.sample(range(1, len(word) + 1), n_picks))
    extracted = "".join(word[p - 1] for p in positions)
    pos_str = ", ".join(str(p) for p in positions)
    return {
        "id": f"extract_{seed}",
        "type": "string_manipulation",
        "question": f"Take the letters at positions {pos_str} of the word '{word}' (1-indexed). Concatenate them in order. What do you get? Answer with just the letters.",
        "answer": extracted,
        "accept": [extracted, extracted.lower()],
    }


def gen_reverse_count(seed: int) -> dict:
    r = random.Random(seed)
    word = r.choice(WORDS)
    counts = Counter(word)
    candidates = [ch for ch, cnt in counts.items() if cnt >= 2]
    if not candidates:
        candidates = list(counts.keys())
    letter = r.choice(candidates)
    answer = str(counts[letter])
    return {
        "id": f"revCount_{seed}",
        "type": "string_manipulation",
        "question": f"Reverse the word '{word}'. In the reversed word, how many times does '{letter}' appear? Answer with just the number.",
        "answer": answer,
        "accept": [answer],
    }


# Few-shot 예시 (간단한 3~4글자 단어로)
EXEMPLARS = [
    {
        "type": "string_manipulation",
        "q": "What is the 3rd letter of the word 'HELLO'? Answer with just the single letter.",
        "a": "H-E-L-L-O. The 3rd letter is L. Answer: L",
    },
    {
        "type": "string_manipulation",
        "q": "Reverse the word 'CAT'. What is the 2nd letter of the reversed word? Answer with just the single letter.",
        "a": "CAT reversed is TAC. The 2nd letter is A. Answer: A",
    },
    {
        "type": "string_manipulation",
        "q": "How many times does 'L' appear in the word 'LLAMA'? Answer with just the number.",
        "a": "L-L-A-M-A. L appears at positions 1 and 2. Count: 2. Answer: 2",
    },
    {
        "type": "string_manipulation",
        "q": "Take the letters at positions 1, 3, 5 of the word 'ABCDE' (1-indexed). Concatenate them. What do you get?",
        "a": "Position 1=A, 3=C, 5=E. Concatenated: ACE. Answer: ACE",
    },
    {
        "type": "string_manipulation",
        "q": "Reverse the word 'BANANA'. How many times does 'A' appear? Answer with just the number.",
        "a": "BANANA reversed is ANANAB. Count A's: A-N-A-N-A-B → 3 times. Answer: 3",
    },
    {
        "type": "string_manipulation",
        "q": "What is the 4th letter of the word 'PYTHON'? Answer with just the single letter.",
        "a": "P-Y-T-H-O-N. The 4th letter is H. Answer: H",
    },
]


def main():
    generators = [gen_char_at_pos, gen_reverse_char, gen_count_letter,
                  gen_multi_extract, gen_reverse_count]
    tasks = []
    for i in range(15):
        s = 3000 + i * 17
        gen = generators[i % len(generators)]
        tasks.append(gen(s))

    output = {"tasks": tasks, "exemplars": EXEMPLARS}

    with open("problems/string_tasks.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(tasks)} tasks → problems/string_tasks.json")
    for t in tasks[:5]:
        print(f"  {t['id']}: {t['question'][:60]}... → {t['answer']}")


if __name__ == "__main__":
    main()
