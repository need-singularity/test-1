## Gen 31 `n_hyperedges` 창발 이벤트 분석

### 핵심 결론: **Phase 2 안정화 신호 (허위 양성)**

이 이벤트는 Gen 30의 480σ 폭발과 **같은 근본 원인**을 공유하지만, 성격이 다릅니다.

### 무슨 일이 일어났는가

| 세대 | n_hyperedges | sigma | 해석 |
|------|-------------|-------|------|
| Gen 20-29 (Phase 1) | ~88-98 | - | 100노드, 안정 |
| **Gen 30 (Phase 2 진입)** | **995** | **480.8σ** | 1000노드 스케일 점프 |
| **Gen 31 (이 이벤트)** | **998** | **2.84σ** | Phase 2 내 미세 증가 |

Gen 30에서 rolling window에 995가 추가되면서, Gen 31의 윈도우 평균/분산이 재계산됩니다. 윈도우에 Phase 1 값(~90대)이 아직 남아있어서, 998이 여전히 2.84σ로 잡힌 것입니다.

### 왜 이것도 허위 신호인가

1. **스케일 오염**: rolling window(10세대)에 Phase 1 데이터(Gen 22-29, ~90대)와 Phase 2 데이터(Gen 30-31, ~995-998)가 혼재
2. **998 vs 995 = +3**: Phase 2 내에서 보면 0.3% 증가에 불과 — 통계적으로 무의미
3. **σ가 인위적으로 부풀림**: 이질적 분포(90대 vs 990대)가 섞인 윈도우에서 계산된 σ는 신뢰할 수 없음

### Gen 30과의 차이

- Gen 30 (σ=480): Phase 전환 자체에 의한 **스케일 불연속**
- Gen 31 (σ=2.84): 오염된 윈도우에 의한 **잔여 잡음** — Phase 전환 후 윈도우가 정화되기까지 ~8세대 더 필요

### Candidate 조합

동일한 엘리트 조합(`dynamic_hypergraph → geodesic_bifurcation → ising_phase_transition → shadow_manifold_audit → free_energy_annealing`)이 계속 지배적입니다. 243개 조합 중 이 하나로 완전 수렴한 상태입니다.

### 권장 조치

Gen 30 분석(`emergence_event_30.md`)에서 이미 제안된 것과 동일합니다:

1. **`EmergenceDetector`에 phase 경계 리셋 추가** — phase 전환 시 rolling window 초기화
2. **밀도 정규화** — `n_hyperedges / n_nodes`로 추적하면 phase 간 비교 가능
3. **이 이벤트는 안전하게 무시 가능** — 진짜 창발이 아닌 측정 artifact

코드 수정을 진행할까요?