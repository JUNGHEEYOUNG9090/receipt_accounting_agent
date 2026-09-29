# receipt_accounting_agent

OCR과 Vision을 활용해 영수증 정보를 분석하고, LLM으로 데이터를 구조화한 뒤 LangGraph를 통해 지출 카테고리를 분류하는 가계부 서비스입니다.

실제 영수증을 대상으로 OCR/LLM과 Vision 결과를 비교하고, AI가 생성한 데이터를 사용자가 검수·수정할 수 있도록 구현했습니다.

---

## 1. 프로젝트 소개

### 주요 목표

- 영수증 OCR 및 Vision 분석
- OCR 결과의 LLM 구조화
- OCR/LLM과 Vision 결과 비교
- LangGraph 기반 지출 카테고리 분류
- Supabase 기반 영수증 데이터 관리
- 사용자 검수 및 수정이 가능한 가계부 UI 구현

---

## 2. 주요 기능

### 영수증 분석

- PaddleOCR-VL 기반 OCR
- OpenAI LLM을 이용한 OCR 결과 구조화
- OpenAI Vision을 이용한 영수증 분석
- OCR/LLM과 Vision 결과 비교

### 가계부

- 영수증 및 품목 조회
- 영수증 및 품목 CRUD
- 카테고리별 영수증 그룹화
- 가게명 및 품목 정보 수정
- 품목 카테고리 수정
- 사용자 검수 후 저장

### AI Workflow

- LangGraph 기반 조건부 Workflow
- 이미 분류된 데이터 재사용
- 미분류 데이터만 OpenAI를 이용해 카테고리 분류

---

## 3. 서비스 구조

```text
영수증 이미지
      ↓
┌───────────────┐
│ OCR / Vision  │
└───────┬───────┘
        ↓
   LLM 구조화
        ↓
    Supabase
        ↓
   LangGraph
        ↓
   카테고리 분류
        ↓
   가계부 UI
        ↓
   사용자 검수
        ↓
      저장
```

OCR은 별도의 서버에서 처리하고, LLM 및 LangGraph Workflow는 메인 백엔드에서 처리합니다.

---

## 4. AI 분석 및 비교

실제 영수증 **35장**을 대상으로 OCR, LLM, Vision을 테스트했습니다.

### 테스트 결과

| 항목             |           결과 | 비용    |
| ---------------- | -------------: | ------- |
| OCR              |        35 / 35 |
| LLM 구조화       |   최종 35 / 35 | $0.0238 |
| Vision 분석      |   최종 35 / 35 | $0.0442 |
| OCR 총 처리 시간 | 약 1,906.303초 | $0.0680 |

OCR은 5장씩 7개 배치로 처리했으며, LLM과 Vision은 초기 실행에서 실패한 데이터만 재처리하여 최종 결과를 확보했습니다.

실제 영수증의 값을 Ground Truth로 작성하고 OCR/LLM 및 Vision 결과를 **Excel에서 비교**했습니다.

주요 비교 항목:

- 상품명
- 수량
- 단가
- 금액
- 할인금액
- 공급가액
- 부가세
- 결제금액
- 결제수단

이를 통해 상품명 오인식, 금액 오류, 할인금액 처리 등의 실제 오류 사례를 확인했습니다.

---

## 5. LangGraph Workflow

LangGraph는 OCR이나 Vision 결과의 정확도를 판단하기 위한 용도가 아니라 **지출 카테고리 분류 Workflow를 관리하기 위해 사용했습니다.**

```text
START
  ↓
영수증 조회
  ↓
DB 상태 확인
  ↓
이미 분류됨?
 ├─ YES → 기존 결과 재사용
 │
 └─ NO
      ↓
   품목 존재?
    ├─ YES → 품목 카테고리 분류
    │
    └─ NO → 영수증 카테고리 분류
```

이미 카테고리가 저장되어 있는 데이터는 다시 OpenAI를 호출하지 않고 기존 결과를 재사용하도록 구성했습니다.

현재 사용 중인 카테고리는 총 13개입니다.

```text
식사 / 카페·음료 / 식료품 / 주유 / 교통
생활용품 / 위생용품 / 의류 / 문구·사무용품
철물·공구 / 의료·약품 / 담배 / 기타
```

---

## 6. 가계부 UI

React 기반으로 사용자가 AI 결과를 확인하고 수정할 수 있는 가계부 화면을 구현했습니다.

동일한 날짜에 같은 카테고리의 영수증이 여러 개 존재하는 경우 하나의 카테고리 아래에 영수증을 묶어서 표시합니다.

```text
의류
 ├─ 영수증 A
 │   ├─ 품목
 │   └─ 품목
 │
 └─ 영수증 B
     ├─ 품목
     └─ 품목

식료품
 └─ 영수증 C
     ├─ 품목
     └─ 품목
```

영수증 자체는 합치지 않고 각각의 `receiptId`를 유지하여 개별적으로 수정할 수 있도록 했습니다.

---

## 7. 데이터 구조

Supabase PostgreSQL을 사용하여 다음 데이터를 관리합니다.

```text
receipts
 └─ 영수증 정보

receipt_items
 └─ 품목 정보

categories
 └─ 지출 카테고리
```

영수증과 품목은 REST API를 통해 조회 및 수정할 수 있습니다.

---

## 8. 기술 스택

### Frontend

- React
- Vite
- Tailwind CSS

### Backend

- Python
- FastAPI
- LangGraph
- OpenAI API

### AI

- PaddleOCR-VL v1.6
- OpenAI LLM
- OpenAI Vision

### Database

- PostgreSQL
- Supabase

### Infrastructure

- Docker
- 별도 OCR 서버

---

## 9. 개발 과정

### 2026-09-25

- OCR 서버 구축
- PaddleOCR-VL 연동
- OCR → LLM 구조화
- Vision 분석 구현

### 2026-09-26

- 실제 영수증 35장 OCR 테스트
- LLM / Vision 분석
- 실패 데이터 재처리
- OCR/LLM/Vision 결과 비교

### 2026-09-27

- Ground Truth 작성
- Excel 비교 결과 정리
- AI 분석 오류 사례 확인

### 2026-09-28

- Supabase DB 구성
- 13개 카테고리 구성
- LangGraph 분류 Workflow 구현
- 기존 분류 결과 재사용

### 2026-09-29

- 영수증 조회/수정/삭제 API
- 영수증 및 품목 CRUD
- 카테고리별 영수증 그룹화
- 사용자 검수 및 수정 UI
- 품목 추가/수정/삭제
- 가게명 및 카테고리 수정

---

## 10. 현재 상태

### 완료

- OCR 분석
- LLM 구조화
- Vision 분석
- OCR/LLM/Vision 비교
- Ground Truth 및 Excel 비교
- Supabase 데이터 관리
- LangGraph 카테고리 분류
- 영수증 및 품목 CRUD
- 카테고리별 가계부 UI
- 사용자 검수 및 수정

### 향후 작업

- 사용자 이미지 업로드
- 이미지 저장(S3 등)
- 모바일 UI 추가 개선
- 서비스 배포

---

## 11. 프로젝트에서 확인한 점

실제 영수증을 대상으로 테스트하면서 OCR과 Vision 모두 모든 정보를 항상 정확하게 추출하지는 않는다는 점을 확인했습니다.

따라서 AI 결과를 그대로 확정하기보다,

```text
AI 분석
  ↓
데이터 저장
  ↓
사용자 검수
  ↓
수정
  ↓
최종 가계부 데이터
```

형태로 구성했습니다.

또한 LangGraph를 이용해 이미 처리된 데이터는 재사용하고, 필요한 경우에만 AI 분류를 수행하도록 구성했습니다.

이를 통해 **AI 분석 자체뿐만 아니라 AI 결과를 실제 서비스 Workflow에 연결하는 과정**까지 구현했습니다.
