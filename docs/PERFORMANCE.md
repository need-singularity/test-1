# TECS Performance Guide

## 성능 최적화 이력

### v1 → v2 → v2+Rust 속도 비교

| 버전 | 세대당 시간 | 조합 수 | 병렬화 | 비고 |
|------|-----------|---------|--------|------|
| v1 (초기) | ~69s | 28/243 (11%) | 순차 | 대부분 비호환으로 0점 |
| v2 (타입 변환) | ~19s | 243/243 (100%) | ProcessPoolExecutor spawn | 전 조합 실행 가능 |
| v2+Rust | ~2-4s (예상) | 243/243 | Rust rayon + Python spawn | 핫루프 7.2x 가속 |

### 벤치마크 결과 (Ricci Flow)

```
1000 노드, 4975 엣지, 20 steps:
  Python:  448ms
  Rust:     62ms
  Speedup: 7.2x

34 노드 (karate club), 50 steps:
  Python:  8.0ms
  Rust:    5.0ms
  Speedup: 1.6x (작은 데이터에서는 오버헤드 비율 큼)
```

---

## 아키텍처 선택지

### A. 전체 Rust 재작성

| 항목 | Python 현재 | Rust 예상 |
|------|-----------|----------|
| 세대당 시간 | 19s | **0.5-2s** |
| 병렬화 | spawn (프로세스 간 오버헤드) | **rayon (GIL 없음, 네이티브 스레드)** |
| 메모리 | ~500MB | **~50MB** |
| 10⁴ 노드 | 분 단위 | **초 단위** |

장점:
- 최대 성능 (10-50x)
- 네이티브 멀티스레딩
- 메모리 효율

단점:
- GUDHI, NetworkX, HyperNetX 대체재 필요
- 개발 기간 수 주
- `claude` CLI 호출은 동일 (subprocess)

### B. 하이브리드: Python + Rust 핫루프 (현재 적용)

PyO3/maturin으로 가장 느린 부분만 Rust로 교체:

```
Python (유지)                     Rust (교체)
─────────────                    ──────────
Orchestrator                     ricci_flow 내부 루프
Evolution Engine                 kuramoto ODE 솔버
Config/Logging                   ising Monte Carlo
claude CLI 호출                  persistent homology 계산
                                 그래프 변환 (graph↔simplicial)
```

| 항목 | 현재 Python | 하이브리드 |
|------|-----------|-----------|
| 세대당 | 19s | 2-4s |
| 개발 기간 | 완료 | 2-3일 |
| 기존 코드 | 유지 | 90% 유지 |

---

## Rust 바인딩 구조

### 빌드

```bash
# 사전 조건: Rust + maturin
pip install maturin

# 빌드 (Python 3.14 호환)
cd rust_core
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 maturin develop --release
```

### rust_core/src/lib.rs 제공 함수

| 함수 | 용도 | Python 대비 속도 |
|------|------|-----------------|
| `ricci_flow_step(n, edges, weights, steps, dt)` | Ollivier-Ricci 곡률 + 가중치 갱신 | 7.2x @ 1000노드 |
| `node_curvatures(n, edges, adj)` | 노드별 곡률 계산 | ~5x |
| `kuramoto_step(phases, freqs, adj, n, K, dt, steps)` | 결합 진동자 동역학 | ~10x |
| `kuramoto_order_parameter(phases)` | 순서 매개변수 r | ~3x |
| `ising_monte_carlo(spins, adj, n, T, sweeps, seed)` | 메트로폴리스 MC | ~15x |
| `ising_observables(spins, adj, n)` | 자화율 + 에너지 | ~5x |
| `edges_to_adj_flat(n, edges)` | 엣지 → 인접행렬 | ~2x |
| `all_pairs_bfs(n, edges)` | 전쌍 BFS 최단경로 | ~10x |

### Python 측 사용법

```python
# 자동 감지 — Rust 있으면 사용, 없으면 Python 폴백
from tecs.components.reasoning.ricci_flow import RicciFlowComponent

comp = RicciFlowComponent()
# 내부적으로 _RUST_AVAILABLE 체크하여 자동 선택
result = comp.execute(state)
```

```python
# 직접 호출
import tecs_rust

new_weights = tecs_rust.ricci_flow_step(
    n_nodes=1000,
    edges=[(0,1), (0,2), ...],
    weights=[1.0, 1.0, ...],
    n_steps=20,
    step_size=0.1,
)
```

---

## 병렬화 전략

### 현재: ProcessPoolExecutor (spawn)

```
메인 프로세스 (Orchestrator)
  ├── Worker 1 (CPU only) → 후보 1~7 평가
  ├── Worker 2 (CPU only) → 후보 8~14 평가
  ├── ...
  └── Worker 8 (CPU only) → 후보 43~50 평가
```

- `spawn` 컨텍스트 (fork는 PyTorch MPS와 충돌하여 SIGSEGV)
- 워커에서 GPU 비활성화 (`PYTORCH_MPS_DISABLE=1`)
- Rust rayon은 워커 내부에서 추가 병렬화

### 향후: 전체 Rust 시 가능한 구조

```
메인 스레드 (Orchestrator)
  └── rayon::par_iter over 50 candidates
        각 후보 내부도 rayon으로 병렬
        → 네스티드 병렬화, GIL 없음
```

---

## 캐싱

### 표현 레이어 캐시

동일한 representation 구성요소 + 동일한 입력 데이터 → 동일한 출력.
50개 후보 중 ~15개가 같은 representation을 공유하면 15번이 아닌 1번만 계산.

```python
# TopologySimulator 내부
cache_key = f"{repr_name}_{points.shape}_{hash(points.tobytes()[:256])}"
if cache_key in self._repr_cache:
    state = copy(cached_state)  # 캐시 히트
else:
    state = repr_comp.execute(state)  # 캐시 미스 → 저장
```

최대 10개 캐시 엔트리, LRU 방식.

---

## 메모리 예산

| 스케일 | 노드 수 | 후보당 메모리 | 50 후보 총 |
|--------|---------|-------------|-----------|
| Phase 1 | 100 | ~50MB | ~2.5GB |
| Phase 2 | 1,000 | ~500MB | 순차 필요 |
| Phase 5 | 10,000 | ~5GB | 순차 + 디스크 |

ScaleController가 `psutil.virtual_memory().percent`로 모니터링, 80% 초과 시 자동 종료.

---

## 향후 최적화 방향

1. **Rust로 persistent homology 이식** — GUDHI 대체, 가장 무거운 연산
2. **GPU (Metal/MPS) 직접 사용** — Rust의 `metal-rs` 크레이트
3. **WASM 빌드** — 브라우저에서 시뮬레이션 시각화
4. **분산 실행** — 여러 머신에서 후보 평가 분산
