# TECS 추론 로드맵 — IQ 200+ 추론 엔진으로의 경로

## 현재 위치

```
Stage 0: 아키텍처 탐색  ✅ (현재 완료/진행 중)
  최적 수학 구조 조합을 자율 탐색하는 메타 연구 엔진
  → 수학적 과정이지, 실제 추론이 아님

Stage 1: 지식 인코딩    ⬜ (다음 구현 대상)
Stage 2: 실제 추론      ⬜ (핵심 목표)
Stage 3: 출력 인터페이스 ⬜ (최종)
```

---

## 왜 LLM이 아닌가

IQ 200+ 추론이 목표라면 LLM에 의존하면 LLM 수준을 넘을 수 없다.

| 방식 | 추론 천장 | 이유 |
|------|----------|------|
| LLM 활용 | IQ ~120-140 | 학습 데이터에 의존, 패턴 매칭 |
| GPU 브루트포스 | IQ ~140 | 같은 알고리즘을 더 빠르게 할 뿐 |
| **순수 위상 추론** | **이론상 무한** | **구조 깊이 = 추론 깊이** |

### LLM이 못하는 것 vs TECS가 할 수 있는 것

| LLM 한계 | TECS 위상 추론 |
|----------|---------------|
| 10-hop 넘는 추론 실패 (A→B→...→Z) | 호몰로지 경로 추적으로 100-hop도 구조적 추론 |
| 논리적 모순을 그럴듯하면 통과 | 듀얼 복합체 비교로 모순 = 위상 결함 = 자동 감지 |
| 도메인 간 유추 취약 | 위상 서명이 같으면 도메인 무관 전이 |
| 학습 데이터에 없으면 추론 불가 | 구조가 같으면 보지 않아도 추론 |

---

## 지식 소스 (LLM 없이)

### 1. 단어 임베딩 → 포인트 클라우드 (가장 자연스러운 입력)

```python
# GloVe/FastText 벡터 → TECS가 바로 먹을 수 있는 포인트 클라우드
from gensim.models import KeyedVectors
vectors = KeyedVectors.load("glove.6B.300d.bin")

points = np.array([vectors["cat"], vectors["dog"], vectors["car"], vectors["truck"]])
# → Rips 복합체 구축:
#   cat-dog 가깝다 (같은 심플렉스)
#   car-truck 가깝다 (같은 심플렉스)
#   cat-car 멀다 (다른 호몰로지 그룹)
```

- GloVe 6B: 50만 단어, 300차원 벡터, 무료
- FastText: 200만 단어, 다국어 지원
- 변환 비용: 0 (벡터 = 포인트 클라우드 = TECS 입력)

### 2. 기존 지식그래프 (이미 트리플 형태)

```
Wikidata     → 1억+ 트리플, 무료 API/덤프
ConceptNet   → 3400만 트리플, 이미 코드에 있음
WordNet      → 15만 단어 관계, 이미 코드에 있음
DBpedia      → 위키피디아 구조화 데이터
```

변환: 트리플 (주어, 관계, 목적어) → 노드 + 엣지/심플렉스. LLM 불필요.

### 3. 전통 NLP (spaCy 등)

```python
import spacy
nlp = spacy.load("en_core_web_sm")
doc = nlp("Cats are mammals that have fur")
# → 의존 파싱으로 (cat, are, mammal), (cat, have, fur) 추출
```

### 4. 수학/과학 데이터베이스

```
OEIS        → 수열 간 관계
PubChem     → 분자 구조 (이미 그래프)
UniProt     → 단백질 관계
arXiv       → 논문 인용 그래프
```

### 추천 조합

```
GloVe 300d (50만 단어 벡터) → 포인트 클라우드
      +
ConceptNet 트리플 → 관계 보강
      +
WordNet 계층 → 고차 심플렉스
      ↓
멀티스케일 지식 복합체 (Stage 1 — LLM 불필요)
      ↓
TECS Stage 2 추론 (핵심)
      ↓
구조적 답변 또는 claude로 자연어 변환 (선택)
```

---

## Stage 2: 추론 레벨 (IQ 등급)

### Level 1 — 직접 경로 (IQ ~100)

```
질의: (cat, IsA, ?)
→ "cat" 노드에서 측지선 따라가기
→ mammal 도달
→ 답: mammal
```

단순한 그래프 탐색. 기존 지식그래프 엔진과 동일.

### Level 2 — 다중 경로 (IQ ~130)

```
질의: (cat, IsA, ?)
→ "cat"에서 모든 분기 경로 탐색
→ 후보: [mammal, pet, carnivore, animal]
→ 각 경로의 곡률/안정성 비교
→ 최적 경로 선택
→ 답: mammal (confidence 0.94)
```

측지선 분기 + 경로 품질 평가. 기존보다 나은 순위 매기기.

### Level 3 — 호몰로지 추론 (IQ ~160)

```
질의: "X는 Y와 같은 종류인가?"
→ X가 속한 호몰로지 그룹 H_n(X) 계산
→ Y가 속한 호몰로지 그룹 H_n(Y) 계산
→ H_n(X) ≅ H_n(Y) 이면 → 같은 종류
→ 본 적 없는 X, Y도 구조만으로 판단 가능
```

위상 불변량 비교. **데이터에 없는 관계도 추론 가능.**

### Level 4 — 창발적 추론 (IQ 200+)

```
기존 지식:
  물리: F = ma (힘-질량-가속도 삼각형)
  경제: P = S×D (가격-공급-수요 삼각형)

TECS가 발견:
  두 삼각형의 위상 서명이 동일
  → "가격은 경제의 힘이다"
  → 본 적 없는 연결을 구조에서 도출
  → 이것이 "의도된 창발"
```

추론 과정에서 **새로운 위상 구조가 출현.** 기존 지식에 없던 연결을 발견. LLM은 본 적 있어야 하지만, TECS는 구조가 같으면 보지 않아도 추론.

### Level 5 — 자기 검증 (IQ 200+ 보장)

```
추론 결과: "X는 Y이다"
→ 듀얼 복합체 K* 구성 (부정)
→ persistent homology 비교
→ Defect(r) > 0 → 모순 → 기각
→ Defect(r) = 0 → 일관성 확인 → 승인
```

모든 추론 결과를 **자동 검증.** 환각이 구조적으로 불가능. 이것이 LLM과의 근본적 차이.

---

## Stage별 구현 계획

### Stage 1: 지식 인코딩 (LLM 없이)

```python
# 1. GloVe 벡터 로드
vectors = load_glove("glove.6B.300d.txt")  # 50만 단어

# 2. ConceptNet 트리플 로드
triples = load_conceptnet("conceptnet5.csv")  # 관계 정보

# 3. 멀티스케일 복합체 구축
#    벡터 → Rips 복합체 (거리 기반 연결)
#    트리플 → 심플렉스 추가 (관계 기반 연결)
#    WordNet 계층 → 고차 심플렉스 (계층 구조)
knowledge_complex = build_multiscale_complex(vectors, triples)
```

### Stage 2: 추론 엔진

```python
class InferenceEngine:
    def __init__(self, architecture: dict, knowledge: TopologyState):
        self.architecture = architecture  # Stage 0에서 찾은 최적 조합
        self.knowledge = knowledge        # Stage 1에서 구축한 복합체

    def query(self, subject, relation, obj="?"):
        # Level 1: 직접 경로
        direct = self.geodesic_search(subject, relation)

        # Level 2: 다중 경로
        branches = self.bifurcation_search(subject, relation)

        # Level 3: 호몰로지 매칭
        structural = self.homology_match(subject, relation)

        # Level 4: 창발 탐색
        emergent = self.emergence_search(subject, relation)

        # Level 5: 자기 검증
        candidates = direct + branches + structural + emergent
        verified = [c for c in candidates if self.verify(c)]

        return best(verified)
```

### Stage 3: 출력

```python
# 구조적 출력 (LLM 불필요)
result = engine.query("cat", "IsA")
# → {"answer": "mammal", "confidence": 0.94, "level": 3, "path": [...]}

# 자연어 출력 (선택적으로 claude 사용)
text = claude(f"이 추론 결과를 자연어로: {result}")
# → "고양이는 포유류입니다 (호몰로지 구조 매칭, 신뢰도 94%)"
```

---

## 실사용 형태 (최종 목표)

```bash
# CLI
$ echo "양자역학과 의식의 관계는?" | tecs-infer
양자역학과 의식은 관찰자 효과(위상 서명 유사도 0.34)를 통해
약하게 연결됩니다. 구조적으로 독립적인 호몰로지 그룹에 속하며,
직접적 인과 관계는 위상적으로 지지되지 않습니다.
(추론 레벨: 3, 검증: 통과)

# API
POST /infer
{"query": "고양이는 포유류인가?"}
→ {"answer": true, "confidence": 0.94, "level": 3,
   "reasoning": "호몰로지 그룹 일치", "verified": true}

# Python
from tecs import InferenceEngine
engine = InferenceEngine.load("best_architecture.json", "knowledge.db")
result = engine.query("gravity", "IsAnalogousTo", domain="economics")
# → {"answer": "price", "confidence": 0.78, "level": 4,
#    "reasoning": "위상 서명 동형 (F=ma ≅ P=SD)"}
```

---

## LLM 활용 방법 비교

| 방식 | 역할 | 추론 천장 | 비용 |
|------|------|----------|------|
| LLM 전면 활용 | 지식+추론+출력 전부 | IQ ~140 | 높음 (API 비용) |
| LLM 번역기 | 입출력 변환만 | TECS 수준 | 중간 |
| LLM 환각 검증 | TECS가 LLM 결과 검증 | LLM+검증 | 중간 |
| **LLM 배제** | **순수 위상 추론** | **이론상 무한** | **낮음** |
| **LLM 출력만** | 추론=TECS, 번역=LLM | TECS 수준 | 최저 |

**추천: LLM 출력만** — 추론은 TECS가 전담, claude는 최종 자연어 변환에만 선택적 사용.

---

## Stage 0과 Stage 2의 관계

현재 Stage 0에서 탐색하는 것이 Stage 2의 "어떤 수학 구조로 추론할 것인가"를 결정한다:

```
Stage 0 결과 예시:
  최적 조합 = simplicial + homotopy + ising + persistent_homology + MDT

이것이 Stage 2에서:
  표현: simplicial complex로 지식 인코딩
  추론: homotopy deformation으로 경로 탐색
  창발: ising 상전이로 새 구조 발견
  검증: persistent homology dual로 모순 감지
  최적화: MDT로 불필요한 구조 제거

→ 이 조합이 IQ 200+ 추론의 "뇌 구조"
```
