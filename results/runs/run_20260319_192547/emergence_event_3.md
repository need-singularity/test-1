## 창발 급등 이벤트 분석

### 이벤트 요약

| 항목 | 값 | 의미 |
|------|-----|------|
| **generation** | 3 | 진화 초기 (3세대) |
| **metric** | magnetization | Ising 모델 스핀 정렬도 |
| **value** | 0.934 | 거의 완전 정렬 (max=1.0) |
| **sigma** | `Infinity` | 통계적 이상치 — 표준편차가 0 |
| **type** | sigma_spike | `\|value - μ\| / σ` 기반 탐지 |

---

### 왜 sigma가 Infinity인가

`EmergenceDetector`는 최근 `window_size=10` 세대의 이력으로 sigma를 계산합니다:

```
sigma = |value - mean(window)| / std(window)
```

3세대에서는 이력이 `min_generations=3`을 겨우 충족하는 수준이라, 이전 세대들의 magnetization 값이 **모두 동일**(std=0)이었을 가능성이 높습니다. 분모가 0이면 sigma는 `Infinity`가 됩니다.

**결론: 이것은 진짜 창발이 아니라 통계적 아티팩트입니다.** 이력 윈도우가 너무 짧아서 의미 있는 편차 계산이 불가능한 상태에서 발생한 허위 양성(false positive)입니다.

---

### 후보 아키텍처 분석

```
dynamic_hypergraph → geodesic_bifurcation → ising_phase_transition → shadow_manifold_audit → free_energy_annealing
```

이 조합은 hall_of_fame에서 **20회 이상 반복 등장**하는 지배적 아키텍처입니다. 최고 fitness=0.7410까지 도달했습니다. 그러나 이 지배력 자체가 문제를 시사합니다:

1. **다양성 부족** — 243개 가능한 조합 중 하나가 hall_of_fame을 독점
2. **Ising + Ising 자기참조** — emergence 레이어가 `ising_phase_transition`인 후보의 magnetization을 emergence metric으로 다시 측정하므로, **측정 대상과 측정 도구가 동일**합니다. 높은 magnetization이 나올 수밖에 없는 구조적 편향입니다.

---

### 권장 개선사항

1. **`min_generations` 올리기** — 현재 3은 너무 낮습니다. 최소 5~7로 올리면 초기 `Infinity` sigma 문제를 제거할 수 있습니다.
2. **std=0 방어** — `emergence_detector.py`에서 `std < epsilon` 일 때 스파이크를 무시하는 로직 추가
3. **자기참조 제거** — emergence 레이어가 `ising_phase_transition`인 후보는 magnetization 기반 스파이크 탐지에서 제외하거나, 교차 메트릭만 사용하도록 변경

이 중 수정을 진행할까요?