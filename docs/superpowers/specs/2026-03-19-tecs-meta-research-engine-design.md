# TECS Meta-Research Engine — 설계 명세서

**작성일:** 2026-03-19
**상태:** Approved Design
**목적:** Post-LLM 아키텍처를 자율적으로 탐색, 검증, 변형, 확장하는 연구 가속 엔진

---

## 1. 목표 및 범위

### 1.1 목표

TECS/TELOS/ATDS 문서에 정의된 수학적 구성요소를 조합하여, 최적의 Post-LLM 아키텍처 후보를 **사람 개입 없이** 자율적으로 탐색한다.

### 1.2 범위

- 243가지 구성요소 조합 자동 탐색
- 소→중→대 적응형 스케일업
- 3종 벤치마크 자동 실행 (개념관계, 모순탐지, 유추추론)
- 5개 창발 지표 전수 추적 + 급등 구간 감지/인과 분석
- 약점 기반 아키텍처 자동 변형/확장
- 체크포인트마다 `claude` CLI로 리포트 자동 생성
- 결과를 GitHub에 push할 수 있는 구조 (JSONL + REPORT.md)

### 1.3 비범위

- 상용 수준 Post-LLM 시스템 자체 구현
- 하드웨어별 저수준 최적화
- 자연어 대화 인터페이스

---

## 2. 결정 사항

| 결정 | 선택 |
|------|------|
| 자율 범위 | 최대 자율 — 탐색→검증→변형→확장 전 루프 |
| 접근법 | 진화 + 인과 분석 (Evolutionary + Causal Analysis) |
| 창발 지표 | 전부 추적 — β, χ, r, Φ, λ 매 세대 |
| 벤치마크 | 전부 — 개념관계 + 모순탐지 + 유추추론 |
| 벤치마크 데이터 | 혼합 — 외부(ConceptNet/WordNet/SAT) + 자체 생성 보조 |
| 기록 | JSONL + REPORT.md → GitHub |
| 실행 규모 | 적응형 스케일업 (10²→10³→10⁴) |
| 하드웨어 | Apple Silicon (MPS + Unified Memory) |
| LLM 사용 | `claude` CLI subprocess, Phase 전환 + 창발 급등 시 리포트 생성 |

---

## 3. 전체 아키텍처

### 3.1 10개 모듈, 3개 그룹

**메인 파이프라인 (6개)**

| 모듈 | 책임 | 입력 → 출력 |
|------|------|------------|
| `ArchitectureGenerator` | 구성요소 조합, 변이, 재조합 | 구성요소 풀 → 후보 리스트 |
| `TopologySimulator` | 후보별 위상 연산 실행 | 후보 + 데이터 → 시뮬 결과 |
| `FitnessEvaluator` | 5개 창발 지표 + 벤치마크 통합 점수 | 시뮬 결과 → fitness 점수 |
| `EvolutionEngine` | 선택, 인과 기반 표적 변이, 교차 | 점수 + 인과 → 다음 세대 |
| `BenchmarkRunner` | 3종 벤치마크 자동 실행 | 후보 + 테스트셋 → 점수 |
| `ScaleController` | 적응형 스케일업 판단 | fitness 추이 → 스케일 결정 |

**횡단 관심사 (2개)**

| 모듈 | 책임 |
|------|------|
| `EmergenceDetector` | 5개 지표 매 세대 추적, 급등 시 이벤트 발화 + 스냅샷 |
| `CausalTracer` | 구성요소 변경 ↔ 지표 변화 인과 분석 (ablation-based) |

**인프라 (2개)**

| 모듈 | 책임 |
|------|------|
| `DataManager` | ConceptNet/WordNet 로드 + 자체 생성 + 복합체 변환 + 캐싱 |
| `ResultLogger` + `ClaudeReporter` | JSONL 기록 + `claude` CLI 리포트 생성 |

**전체 제어: `Orchestrator`** — Phase 전환, 종료 조건, 전체 루프 자율 제어

---

## 4. 구성요소 풀

5개 계층 × 3개 구성요소 = 243 조합

### 4.1 표현 (Representation)

| 구성요소 | 구현 기반 | 출처 |
|----------|----------|------|
| `simplicial_complex` | GUDHI SimplexTree, Vietoris-Rips | TELOS |
| `riemannian_manifold` | 이산 리만 다양체, 계량 텐서 g_ij on graph | TECS/ATDS |
| `dynamic_hypergraph` | HyperNetX 기반 다중 노드 동시 연결 | ATDS |

### 4.2 추론 (Reasoning)

| 구성요소 | 구현 기반 | 출처 |
|----------|----------|------|
| `ricci_flow` | Ollivier-Ricci curvature, GraphRicciCurvature | TECS |
| `homotopy_deformation` | K_input→K_target 연속 변형, GUDHI filtration | TELOS |
| `geodesic_bifurcation` | 불안정 임계점 다중 측지선 분기, SciPy ODE | TECS |

### 4.3 창발 (Emergence)

| 구성요소 | 구현 기반 | 출처 |
|----------|----------|------|
| `kuramoto_oscillator` | 3계층 결합 진동자, 쿠라모토 순서 매개변수 r | TECS |
| `ising_phase_transition` | 정보 온도, 결합 강도 J_ij, Monte Carlo | TELOS |
| `lyapunov_bifurcation` | 리아프노프 지수 양수 강제, 비선형 연산자 주입 | ATDS |

### 4.4 검증 (Verification)

| 구성요소 | 구현 기반 | 출처 |
|----------|----------|------|
| `persistent_homology_dual` | K_out vs K_out* 듀얼, Defect(r) = Σ\|Δβ_n\| | TELOS |
| `shadow_manifold_audit` | M + M* 이중 다양체, halluc = \|Ric_M\|·c/\|Ric_M*\| | TECS |
| `stress_tensor_zero` | 인지적 응력 텐서, 다양체 찢김/교차 탐지 | ATDS |

### 4.5 최적화 (Optimization)

| 구성요소 | 구현 기반 | 출처 |
|----------|----------|------|
| `min_description_topology` | MDT(D) = argmin[Σβ_n + λ·d_GH], Gromov-Hausdorff | TELOS |
| `fisher_distillation` | 피셔 정보 행렬 I(θ), g_ij += α·I_ij(θ), 압축률 10⁻³~10⁻⁵ | TECS |
| `free_energy_annealing` | F_s = C(K) - T_s·H(K), 시뮬레이티드 어닐링 | ATDS |

---

## 5. 시뮬레이션 파이프라인

1개 후보를 평가하는 과정:

```
Step 1: DataManager      → 외부 데이터 → 표현 구성요소로 복합체 변환
Step 2: TopologySimulator → 추론 구성요소 적용 (예: ricci_flow 100 steps)
Step 3: TopologySimulator → 창발 구성요소 적용 (예: ising 임계 결합 유도)
Step 4: TopologySimulator → 검증 구성요소 적용 (예: persistent_homology Defect(r))
Step 5: TopologySimulator → 최적화 구성요소 적용 (예: fisher_distillation 압축)
Step 6: FitnessEvaluator  → β,χ,r,Φ,λ 측정 → 통합 fitness 계산
Step 7: EmergenceDetector → 이전 세대 대비 급등 여부 판정
Step 8: BenchmarkRunner   → 3종 벤치마크 → 개별 + 통합 점수
```

---

## 6. 진화 엔진

### 6.1 세대 루프

1. **선택**: 토너먼트 선택 (tournament_size=3), 상위 20% 엘리트 보존
2. **인과 기반 표적 변이**: CausalTracer가 약점 계층 지목 → 해당 계층만 교체
3. **교차**: uniform crossover, 인과 분석 기반 강한 계층 보존 확률 상향
4. **다양성 보호**: 해밍 거리 중복 제거, 수렴 시 무작위 이민자 주입

### 6.2 인과 추적 (CausalTracer)

- **방법**: Ablation-based causal attribution
- 세대 간 변경된 구성요소 식별
- Δmetric_i / Δcomponent_j → 인과 강도 행렬
- 다수 세대 누적 → 통계적 유의성 검증 (p < 0.05)
- **비용**: 추가 시뮬레이션 0회 (이미 실행된 데이터만 분석)

---

## 7. 창발 감지

### 7.1 5개 지표 + 급등 판정 기준

| 지표 | 계산 방법 | 급등 판정 | 의미 |
|------|----------|----------|------|
| β (베티수) | GUDHI persistent homology | \|Δβ_n\| > 2σ | 새 위상 구조 출현 |
| χ (오일러 특성) | Σ(-1)^n · β_n | \|Δχ\| > 2σ | 전역 위상 복잡도 변화 |
| r (순서 매개변수) | 쿠라모토 order parameter | dr/dt > threshold | 동기화 상전이 |
| Φ (통합 정보) | pyphi 또는 근사 계산 | Φ > Φ_critical | 정보 통합도 임계 초과 |
| λ (리아프노프) | 궤적 발산률 수치 추정 | λ: 음→양 전환 | 혼돈 진입 (분기점) |

### 7.2 급등 시 자동 동작

1. 해당 세대 전체 상태 스냅샷 저장
2. CausalTracer에 즉시 인과 분석 요청
3. `emergence_events.jsonl`에 이벤트 기록
4. `claude` CLI 호출 → 급등 분석 리포트 자동 생성
5. 해당 조합을 `hall_of_fame`에 등록

---

## 8. Orchestrator: Phase 전환 + 종료 조건

### 8.1 5개 Phase

```
Phase 1 (조합 탐색, 10², 세대 30)
  → Phase 2 (중규모 검증, 10³, 세대 50)
  → Phase 3 (3종 벤치마크)
  → Phase 4 (약점 보완 + 인과 기반 변이)
  → Phase 2로 복귀 (루프) 또는 Phase 5 (대규모 확인, 10⁴)
  → 종료
```

### 8.2 Phase 전환 규칙

| 전환 | 조건 | 자동 동작 |
|------|------|----------|
| 1→2 | 세대 수렴 또는 max_gen 도달, 상위 5개 선별 | 스케일 10²→10³, claude → phase1_report.md |
| 2→3 | 중규모 재수렴, 상위 2개 선별 | 벤치마크 데이터 로드, claude → phase2_report.md |
| 3→4 | 3종 벤치마크 완료 | 약점 식별 + 인과 분석, claude → phase3_report.md |
| 4→2 | 인과 변이로 개선 후보 생성 | 변이 후보로 Phase 2 재진입 |
| 4→5 | 루프 N회 또는 개선 없음 | 최적 후보로 대규모 검증, 스케일 10³→10⁴ |
| 5→종료 | 대규모 검증 완료 | claude → REPORT.md 최종, hall_of_fame 갱신 |

### 8.3 종료 조건

| 종류 | 조건 |
|------|------|
| 성공 종료 | 환각률 < 0.01 + 창발률 > 0.8 + 벤치마크 > 0.7 동시 충족 |
| 수렴 종료 | 5세대 연속 fitness 개선 < 0.01 |
| 자원 한계 | 총 실행 시간 > 48h 또는 메모리 > 80% |
| 루프 한계 | Phase 4→2 루프 > 10회 |

---

## 9. 데이터 + 기록

### 9.1 벤치마크 데이터

| 태스크 | 외부 소스 | 자체 생성 |
|--------|----------|----------|
| 개념관계 추론 | ConceptNet 관계 트리플 | 지식 그래프에서 자동 추출 |
| 모순 탐지 | ConceptNet 부정 쌍 | 긍정 트리플 자동 부정 변환 |
| 유추 추론 | SAT analogy dataset | 구조적 유사성 자동 생성 |

### 9.2 결과 기록 구조

```
results/runs/run_YYYYMMDD_HHMMSS/
├── config.yaml
├── evolution.jsonl          # 매 세대 전체 지표
├── emergence_events.jsonl   # 창발 급등 이벤트
├── benchmarks.jsonl         # 벤치마크 결과
├── phase_log.jsonl          # Phase 전환 기록
├── causal_graph.json        # 인과 분석 결과
└── REPORT.md                # claude CLI 생성 최종 리포트

results/hall_of_fame/
└── best_candidates.jsonl    # 역대 최고 후보 누적
```

---

## 10. 실행 흐름

```bash
# 설치
pip install -r requirements.txt
python -m tecs.data.data_manager --download

# 실행 — 이것 하나면 끝
python run.py

# 결과 확인 + GitHub push
cat results/runs/run_*/REPORT.md
git add results/ && git commit && git push
```

---

## 11. 기술 스택

| 범주 | 패키지 |
|------|--------|
| TDA + 수치 | gudhi, giotto-tda, numpy, scipy, networkx, hypernetx |
| Apple Silicon 가속 | jax-metal, torch (MPS backend), GraphRicciCurvature |
| 데이터 | nltk (WordNet), requests (ConceptNet API), pyyaml |
| 리포팅 | claude CLI (subprocess), jinja2 |

---

## 12. 공통 인터페이스

```python
class Component(Protocol):
    name: str
    layer: str

    def execute(self, state: TopologyState) -> TopologyState: ...
    def measure(self, state: TopologyState) -> dict[str, float]: ...
    def cost(self) -> float: ...

@dataclass
class TopologyState:
    complex: Any           # SimplexTree | graph | hypergraph
    curvature: np.ndarray  # 곡률 텐서 (이산 근사)
    metrics: dict          # 현재 지표
    history: list          # 변형 경로 기록
    metadata: dict         # 추가 정보
```

---

## 13. Apple Silicon 최적화

- **Unified Memory**: CPU↔GPU 데이터 복사 없음, 복합체를 한 번만 메모리에 올리고 CPU(TDA) + MPS(행렬 연산) 혼용
- **병렬 후보 평가**: multiprocessing으로 후보 분산, MPS는 행렬 연산 집중 모듈만
- **스케일별 메모리 예산**: 10² 노드 ~50MB, 10³ 노드 ~500MB, 10⁴ 노드 ~5GB
- **JAX-Metal 백엔드**: 자동 미분 + GPU 가속, 리치 흐름/쿠라모토에 적용

---

## 14. 리스크 및 대응

| 리스크 | 대응 |
|--------|------|
| 계산비용 급증 | 전역이 아닌 국소 복합체만 갱신, 적응형 스케일업 |
| 수학 지표와 의미 품질 불일치 | 벤치마크 태스크로 실제 추론 성능 병행 측정 |
| 창발 재현성 부족 | 시드 고정 + 전체 상태 스냅샷 + config.yaml 기록 |
| `claude` CLI 호출 실패 | fallback으로 JSON-only 리포트 생성, 엔진은 중단 없이 계속 |
