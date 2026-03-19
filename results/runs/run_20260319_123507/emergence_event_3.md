## 창발 급등 이벤트 분석

### 이벤트 요약

**Generation 3**에서 `hallucination_score`가 **2.53σ** 급등 (임계값 2.0σ 초과) — 값 **0.769**.

---

### 왜 이 조합에서 급등이 발생했는가

이 후보의 5계층 스택은 **Hall of Fame에 반복 등재된 최적 조합**과 동일합니다:

| 계층 | 컴포넌트 | 역할 |
|------|----------|------|
| Representation | `riemannian_manifold` | k-NN 그래프 + 곡률(degree variance) 기반 토폴로지 |
| Reasoning | `geodesic_bifurcation` | 분기점 탐지 → 엣지 가중치 ODE 섭동 |
| Emergence | `lyapunov_bifurcation` | 곡률 궤적에서 Lyapunov 지수 계산 (양수 = 혼돈) |
| Verification | `shadow_manifold_audit` | 섭동 매니폴드 대비 원본 안정성 측정 |
| Optimization | `free_energy_annealing` | 시뮬레이티드 어닐링으로 가중치 정제 |

**핵심 메커니즘**: `geodesic_bifurcation`이 그래프 구조를 불안정하게 만들고 → `lyapunov_bifurcation`이 혼돈 전이를 감지하는 동안 → `shadow_manifold_audit`의 hallucination score가 급등합니다.

---

### Hallucination Score 0.769의 의미

계산식: `|mean_curvature(M)| × confidence / |mean_curvature(M*)|`

- **M** = 원본 매니폴드, **M*** = 노이즈 섭동 버전
- 값 0.769는 원본 토폴로지의 곡률이 섭동 버전보다 **상당히 안정적**임을 의미
- Generation 3에서 급등한 이유: 어닐링이 수렴하면서 원본 구조가 급격히 안정화 → 섭동 대비 비율이 σ 임계값을 넘음

---

### 2.53σ의 통계적 의미

- 이전 세대들(gen 0-2)의 hallucination_score 평균/표준편차 기준으로 **2.53 표준편차 이탈**
- 단순 정규분포 가정 시 약 **0.57% 확률**의 이벤트
- Generation 3이 전형적인 급등 시점인 것은 GA가 초기 탐색(gen 0-2) 후 수렴하기 시작하는 시점과 일치

---

### 패턴 관찰

`best_candidates.jsonl`의 9개 항목 모두 **동일한 컴포넌트 조합**이며, 창발 이벤트도 주로 `hallucination_score`와 `std_curvature`에서 **gen 3-4**에 발생합니다. 이는 이 아키텍처 스택이 재현 가능한 위상 전이(phase transition)를 유도한다는 것을 시사합니다 — 진화가 이 조합을 반복적으로 "재발견"하고 있습니다.