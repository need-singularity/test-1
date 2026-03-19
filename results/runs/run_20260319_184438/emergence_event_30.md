## 분석 결과

### 원인: Phase 2 스케일 전환

이건 버그가 아니라 **시스템 설계상의 artifact**입니다.

- **Gen 1-29** (Phase 1): 100개 노드 네트워크 → `n_hyperedges`가 88~98 범위에서 안정
- **Gen 30** (Phase 2): **1000개 노드**로 점프 → `n_hyperedges`가 995로 폭증

sigma 계산은 직전 10세대의 rolling window를 사용합니다 (`emergence_detector.py:78-89`):

```
sigma = |value - mean_recent| / std_recent
```

Gen 20-29의 평균이 ~94, std가 ~1.87이었으므로:

```
sigma = |995 - 94| / 1.87 ≈ 480.77
```

**480σ는 진짜 통계적 이상치가 아닙니다.** 측정 스케일 자체가 바뀐 것입니다.

### 문제점

`EmergenceDetector`가 **phase 전환 경계에서 스케일 불연속을 감지하지 못합니다.** 100-node 네트워크와 1000-node 네트워크의 raw `n_hyperedges`를 동일 윈도우에서 비교하고 있어서 의미 없는 spike를 기록합니다.

### 이 candidate의 구성

모든 12개 엘리트 candidate가 동일한 5-layer 조합으로 수렴했습니다:

| Layer | Component | 역할 |
|-------|-----------|------|
| representation | `dynamic_hypergraph` | 포인트 클라우드 → 거리 기반 hyperedge 생성 |
| reasoning | `geodesic_bifurcation` | 측지선 분기 탐색 |
| emergence | `ising_phase_transition` | 자기화 기반 질서/무질서 전이 |
| verification | `shadow_manifold_audit` | 그림자 다양체 검증 |
| optimization | `free_energy_annealing` | 자유 에너지 어닐링 |

### 권장 조치

1. **정규화**: `n_hyperedges`를 노드 수로 나눠서 `hyperedge_density = n_hyperedges / n_nodes`로 추적하면 phase 간 비교가 가능
2. **윈도우 리셋**: phase 전환 시 `EmergenceDetector`의 rolling window를 초기화
3. **이 이벤트는 무시해도 안전**: 진짜 창발이 아니라 스케일 변경에 의한 허위 신호입니다