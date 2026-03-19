## 분석: Generation 30 `n_hyperedges` 338σ 급등

### 핵심 원인: Phase 1 → Phase 2 전환

evolution.jsonl에서 generation 30이 **`"phase": 2`** 로 전환된 것이 확인됩니다. 이전 29세대는 모두 phase 1이었습니다.

### 수치 비교

| 메트릭 | Gen 0-29 (Phase 1) | Gen 30 (Phase 2) | 배율 |
|---|---|---|---|
| `n_hyperedges` | 88~98 | **995** | ~10.5x |
| `mean_hyperedge_size` | 7.5~11.6 | **90.3** | ~8-12x |
| `max_hyperedge_size` | 17~28 | **216** | ~8-12x |
| `energy` | -920 ~ -1630 | **-202,260** | ~130x |
| `free_energy` | 23~41 | **5,092** | ~130x |

### 해석

**이건 진짜 "창발"이 아니라 스케일 점프입니다.** Phase 2로 전환되면서 하이퍼그래프 생성 코드가 훨씬 큰 규모의 구조를 만들기 시작한 것입니다.

근거:
1. **338σ는 통계적으로 불가능한 값** — 실제 분포에서의 이상치가 아니라, 기저 분포 자체가 바뀐 것 (regime change)
2. **모든 구조적 메트릭이 동시에 ~10x 증가** — 독립적인 급등이 아니라 단일 원인(N 또는 노드 수 증가)으로 설명됨
3. **fitness는 거의 변하지 않음** (0.733 vs 이전 최고 0.735) — 구조가 10배 커졌지만 성능은 동일
4. **`acceptance_rate`가 0.4로 급락** — 더 큰 탐색 공간에서 수렴이 어려워졌음을 시사

### 결론

sigma spike 탐지기가 phase 1의 running statistics (평균 ~93, std ~2.7)로 phase 2의 값(995)을 평가하고 있어서 338σ로 기록된 것입니다. Phase 전환 시 통계를 리셋하거나, phase별로 별도의 baseline을 유지하는 것이 더 정확한 탐지를 할 수 있습니다.

**권장사항**: emergence 탐지 로직에서 phase 전환 시점에 sigma 계산의 baseline을 리셋하도록 수정하면, 이런 false positive를 걸러낼 수 있습니다.