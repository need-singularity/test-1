# TECS Meta-Research Engine — 사용법

---

## 실행 모드 3가지

### 1. 아키텍처 탐색 (run_loop)

243가지 수학적 구성요소 조합을 진화 알고리즘으로 탐색. 4단계 검증 파이프라인 포함.

```bash
./run.sh
```

또는:
```bash
.venv/bin/python run_loop.py                    # 무한 반복 + git push
.venv/bin/python run_loop.py --rounds 10        # 10회
.venv/bin/python run_loop.py --no-git-push      # push 없이
```

### 2. 자동 연구 (auto_research)

가설 생성 → 코드 작성 → 실행 → 검증 → 수정을 자동 반복.

```bash
.venv/bin/python auto_research.py --cycles 5

# 커스텀 목표
.venv/bin/python auto_research.py \
  --target "트랜스포머 어텐션에서 β₁ 감소율과 모델 성능의 관계" \
  --cycles 10
```

### 3. 추론 엔진 (infer)

위키피디아/arXiv 지식 로드 → 위상 추론 + 검증.

```bash
# 유추 추론
.venv/bin/python3 infer.py --topics "Gravity" "Economics" --analogy gravity economics

# 구조 비교
.venv/bin/python3 infer.py --topics "Schrodinger equation" "Black-Scholes model" \
  --compare "schrodinger equation" "blackscholes model"

# 대화형
.venv/bin/python3 infer.py --topics "Riemann hypothesis" "Quantum chaos" --interactive

# arXiv 논문 포함
.venv/bin/python3 infer.py --arxiv "quantum chaos random matrix" --interactive
```

### 동시 실행

```bash
# 터미널 1: 아키텍처 탐색
./run.sh

# 터미널 2: 자동 연구
.venv/bin/python auto_research.py --cycles 10
```

---

## 수학 실험

### 트랜스포머 어텐션 위상 분석

```bash
.venv/bin/python3 tecs/math/attention_topology.py \
  --text "your text here" \
  --model gpt2
```

### 3-SAT 해 공간 호몰로지

```bash
.venv/bin/python3 tecs/math/riemann_pslq.py --zeros 10000 --order 8
```

### Deep Solve (수식 반복 검증)

```bash
.venv/bin/python deep_solve.py --problem problems/pdl1_bft.json --max-iter 10
```

---

## 설치

```bash
git clone https://github.com/need-singularity/test-1
cd test-1
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Rust 가속 (선택)
cd rust_core && PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 maturin develop --release && cd ..

# PyTorch (GPU 가속, 선택)
.venv/bin/pip install torch

# Transformers (어텐션 분석, 선택)
.venv/bin/pip install transformers
```

---

## 설정 (config.yaml)

| 섹션 | 파라미터 | 기본값 | 설명 |
|------|---------|--------|------|
| search | population_size | 50 | 세대당 후보 수 |
| search | seed | 42 | 재현성 시드 |
| scaling | phase1_nodes | 100 | Phase 1 노드 수 |
| scaling | phase1_max_gen | 30 | Phase 1 최대 세대 |
| fitness | w_emergence | 0.4 | 창발 가중치 |
| fitness | w_benchmark | 0.4 | 벤치마크 가중치 |
| termination | max_hours | 48 | 최대 실행 시간 |
| reporting | claude_cli | true | Claude 리포트 생성 |

---

## 결과 구조

```
results/
├── runs/run_YYYYMMDD_HHMMSS/
│   ├── evolution.jsonl         # 세대별 지표
│   ├── emergence_events.jsonl  # 창발 이벤트
│   ├── checkpoint.json         # 복구용
│   └── REPORT.md              # 리포트
├── hall_of_fame/               # 역대 최고 후보
├── attention_topology.json     # GPT-2 어텐션 β₁ 데이터
├── 3sat_homology.json          # 3-SAT 위상 전이 데이터
├── auto_research.json          # 자동 연구 결과
└── run_history.jsonl           # 라운드 이력
```

---

## 검증 파이프라인 (v4)

모든 후보는 4단계 검증을 거침:

| 단계 | 검증 | 실패 시 |
|------|------|--------|
| A. 형식 | NaN/Inf, 의심스러운 완벽 점수, 모순 지표 | 즉시 탈락 |
| B. 반례 | 노이즈 입력에 높은 점수 = 비신뢰 | 즉시 탈락 |
| C. 재현 | 3개 시드 분산 > 0.1 = 불안정 | 점수 감점 |
| D. 예측 | 실제 태스크 성능 | 점수 반영 |

실패율 > 30% → **fitness = 0 (즉시 탈락)**

---

## 실증적 결과 (2026-03-19)

| 실험 | 결과 | 파일 |
|------|------|------|
| GPT-2 어텐션 β₁ | Layer 0→10: β₁ = 43→0 (붕괴) | attention_topology.json |
| 3-SAT 위상 전이 | α=4.75에서 β₁=0 | 3sat_homology.json |
| 27개 매핑 자체 검증 | Tier 1: 2개, Tier 3 폐기: 5개 | MAPPING_DATABASE.md |

---

## 문서

| 문서 | 내용 |
|------|------|
| [설계 명세서](docs/superpowers/specs/2026-03-19-tecs-meta-research-engine-design.md) | v4 아키텍처 |
| [구현 계획](docs/superpowers/plans/2026-03-19-tecs-meta-research-engine.md) | 18 태스크 |
| [성능 가이드](docs/PERFORMANCE.md) | Python/Rust/GPU 벤치마크 |
| [추론 로드맵](docs/INFERENCE_ROADMAP.md) | Stage 0→3 |
| [매핑 DB](docs/MAPPING_DATABASE.md) | 27건 티어 분류 |
| [자체 검증](docs/papers/self_audit_report.md) | 4단계 검증 결과 |
