# TECS Meta-Research Engine — 사용법

Post-LLM 아키텍처를 자율 탐색하는 연구 가속 엔진.

---

## 설치

```bash
git clone https://github.com/need-singularity/test-1
cd test-1
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

---

## 실행

### 1회 실행

```bash
.venv/bin/python run.py
```

설정 파일 지정:
```bash
.venv/bin/python run.py --config config.yaml
```

결과 디렉토리 지정:
```bash
.venv/bin/python run.py --results-dir my_results
```

### 체크포인트에서 복구

중간에 중단된 실행을 이어서:
```bash
.venv/bin/python run.py --resume results/runs/run_20260319_115818
```

---

## 반복 실행

### 기본 (무한 반복, Ctrl+C로 중단)

```bash
.venv/bin/python run_loop.py
```

### 횟수 지정

```bash
.venv/bin/python run_loop.py --rounds 5
```

### 라운드 간 대기 시간 (초)

```bash
.venv/bin/python run_loop.py --rounds 10 --interval 60
```

### 매 라운드마다 GitHub push

```bash
.venv/bin/python run_loop.py --rounds 10 --git-push
```

### 전체 옵션 조합

```bash
.venv/bin/python run_loop.py \
  --config config.yaml \
  --results-dir results \
  --rounds 10 \
  --interval 30 \
  --git-push
```

---

## 설정 (config.yaml)

| 섹션 | 주요 파라미터 | 기본값 | 설명 |
|------|-------------|--------|------|
| `search` | `population_size` | 50 | 세대당 후보 수 |
| | `seed` | 42 | 재현성을 위한 시드 |
| `scaling` | `phase1_nodes` | 100 | Phase 1 노드 수 |
| | `phase2_nodes` | 1000 | Phase 2 노드 수 |
| | `phase5_nodes` | 10000 | Phase 5 노드 수 |
| | `phase1_max_gen` | 30 | Phase 1 최대 세대 |
| `fitness` | `w_emergence` | 0.4 | 창발 지표 가중치 |
| | `w_benchmark` | 0.4 | 벤치마크 가중치 |
| | `w_efficiency` | 0.2 | 효율 가중치 |
| `emergence` | `sigma_threshold` | 2.0 | 급등 판정 시그마 |
| | `window_size` | 10 | 슬라이딩 윈도우 크기 |
| `termination` | `max_hours` | 48 | 최대 실행 시간 |
| | `max_loops` | 10 | Phase 4→2 최대 루프 |
| | `plateau_generations` | 5 | 수렴 판정 세대 수 |
| `reporting` | `claude_cli` | true | claude CLI 리포트 생성 |

---

## 결과 구조

```
results/
├── runs/
│   └── run_YYYYMMDD_HHMMSS/
│       ├── evolution.jsonl          # 매 세대 지표
│       ├── emergence_events.jsonl   # 창발 급등 이벤트
│       ├── benchmarks.jsonl         # 벤치마크 점수
│       ├── phase_log.jsonl          # Phase 전환 기록
│       ├── causal_graph.json        # 인과 분석 결과
│       ├── checkpoint.json          # 체크포인트 (복구용)
│       └── REPORT.md               # 최종 리포트
│
└── hall_of_fame/
    └── best_candidates.jsonl       # 역대 최고 후보 누적
```

---

## 실행 흐름

```
python run.py 실행
    │
    ▼
Phase 1: 조합 탐색 (243가지, 노드 10²)
    │  진화 알고리즘 + 인과 분석
    │  → 상위 5개 후보 선별
    ▼
Phase 2: 중규모 검증 (노드 10³)
    │  → 상위 2개 후보 선별
    ▼
Phase 3: 벤치마크 (개념관계 + 모순탐지 + 유추추론)
    │
    ▼
Phase 4: 약점 보완 + 인과 기반 변이
    │  개선 있으면 → Phase 2로 복귀
    │  없으면 ↓
    ▼
Phase 5: 대규모 확인 (노드 10⁴)
    │
    ▼
REPORT.md 생성 + 종료
```

**종료 조건 (어느 시점에서든):**
- 환각률 < 1% + 창발률 > 80% + 벤치마크 > 0.7 → 성공 종료
- 5세대 연속 개선 없음 → 수렴 종료
- 48시간 초과 → 시간 한계
- Phase 4→2 루프 10회 초과 → 루프 한계

---

## 창발 지표 (5개)

| 지표 | 의미 | 급등 판정 |
|------|------|----------|
| β (베티수) | 새 위상 구조 출현 | Δβ > 2σ |
| χ (오일러 특성) | 전역 위상 복잡도 변화 | Δχ > 2σ |
| r (순서 매개변수) | 동기화 상전이 | Δr > 0.2/세대 |
| Φ (통합 정보) | 정보 통합도 | Φ > 1.0 |
| λ (리아프노프) | 혼돈 진입 | λ: 음→양 전환 |

---

## 테스트

```bash
.venv/bin/python -m pytest -v
```

---

## 문서

- `docs/superpowers/specs/` — 설계 명세서
- `docs/superpowers/plans/` — 구현 계획
- `2026-03-19_TECS_Architecture.md` — TECS 원본 아키텍처
- `2026-03-19_ATDS_Architecture.md` — ATDS 원본 아키텍처
- `TECS_Post-LLM_Architecture_v0.1.md` — Post-LLM v0.1 원본
