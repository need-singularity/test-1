# TECS (Topological Evolution of Cognitive Structures)

## 프로젝트 개요
진화 알고리즘으로 위상수학적 인지 아키텍처를 탐색하는 실험 프로젝트.
5개 모듈(representation, reasoning, emergence, verification, optimization)의 조합을 진화시켜 최적 아키텍처를 발견한다.

## 핵심 연구 결과

### Verification 모듈 분석 (2026-03-19)

**`stress_tensor_zero`는 현재 파이프라인에서 무용지물:**
- dynamic_hypergraph가 생성하는 그래프의 엣지 가중치가 기본값(1.0)
- stress = weight - shortest_path → 직접 연결이면 항상 0
- 30세대 전부 stress_magnitude=0.0 — fitness 함수에 신호 없음

**`shadow_manifold_audit`가 fitness를 지배하는 이유:**
- 노이즈 주입으로 섀도 매니폴드 생성 → 곡률 비교 → 비영(non-zero) hallucination_score 산출
- fitness 함수에 실질적 기울기(gradient) 제공
- 역대 최고 기록(0.69~0.74) 전부 이 모듈 사용

### multihop_accuracy = 0.40 고정 문제
- inference 지표가 진화 과정에서 **전혀 변하지 않음** (Gen 0~29 동일)
- 원인: inference_engine.py가 진화 대상이 아님 (고정 BFS 3홉 탐색)
- 해결 방향: BFS 깊이 확장, eval set 점검, inference를 진화 대상에 포함

### 쌍곡 기하학(Hyperbolic Geometry) 모듈 검토
- 푸앵카레 원판 거리 기반 어텐션은 수학적으로 타당
- 현재 TECS에는 연결 지점 없음: inference가 이산 그래프 BFS, 연속 벡터 공간 미사용
- 적용하려면 inference 엔진 전체 재설계 필요

## 우승 아키텍처 (Phase 1 기준)
- representation: `dynamic_hypergraph`
- reasoning: `geodesic_bifurcation`
- emergence: `ising_phase_transition`
- verification: `shadow_manifold_audit` (필수)
- optimization: `free_energy_annealing`

## 운영 주의사항
- 장시간 실행은 백그라운드 + 주기적 보고
- Claude CLI 리포트(cfg.reporting)는 Phase 전환 블로킹 유발 — 반드시 비활성화
- 오캄 페널티: λ_bloat=0.05 (EDGE_THRESHOLD=150), λ_halluc=0.4 적용 중
