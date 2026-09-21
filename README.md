# Receipt Accounting Agent

영수증 이미지를 기반으로 상품 정보를 추출하고, AI를 활용해 지출 항목을 자동으로 분류하는 **AI 기반 영수증 가계부 서비스**입니다.

OCR로 추출한 영수증 데이터를 LLM으로 구조화하고, LangGraph를 이용해 **상품 분류 → 검증 → 재처리** 과정을 관리합니다.

사용자가 최종 결과를 직접 확인하고 수정할 수 있도록 하여, OCR 및 LLM의 오류를 보완하는 것을 목표로 합니다.

---

## 프로젝트 소개

마트나 식자재 매장에서 장을 본 뒤 영수증을 확인하면 식품, 생활용품 등 서로 다른 종류의 상품이 하나의 영수증에 함께 포함되어 있습니다.

기존 가계부 서비스에서는 이러한 지출을 직접 분류해야 하는 경우가 많기 때문에,

**"영수증을 사진으로 찍으면 상품별로 자동 분류해주는 가계부"**

를 목표로 프로젝트를 진행합니다.

현재는 다음과 같은 중분류를 기준으로 개발하고 있습니다.

```text
장바구니
├── 식비
├── 생활비
└── 기타
```

추후 실제 영수증 데이터를 확인한 후 필요에 따라 세부 분류를 추가할 예정입니다.

---

## 주요 기능

### 1. 영수증 이미지 업로드

사용자가 영수증 사진을 업로드하여 자동 분석을 시작할 수 있습니다.

모바일 환경에서 사진을 촬영하거나 이미지를 선택할 수 있도록 반응형 UI로 구성합니다.

### 2. 영수증 OCR

기존에 구축한 OCR 서버를 활용하여 영수증 이미지에서 텍스트를 추출합니다.

```text
영수증 이미지
      ↓
PaddleOCR-VL
      ↓
OCR 결과
```

### 3. LLM 기반 데이터 구조화

OCR 결과를 OpenAI API를 이용해 분석하여 상품명, 가격, 수량 등의 정보를 구조화합니다.

```text
OCR 결과
   ↓
OpenAI
   ↓
상품 정보
├── 상품명
├── 가격
├── 수량
└── 금액
```

OCR 과정에서 발생할 수 있는 상품명 오류나 불완전한 데이터를 문맥을 기반으로 보정하는 것도 함께 검토합니다.

### 4. 상품 카테고리 분류

추출된 상품을 지출 목적에 따라 분류합니다.

```text
농심)짜왕멀티 4입
→ 식비

LG)사프란핑크용기 3.1L
→ 생활비
```

### 5. LangGraph 기반 검증 및 재처리

단순히 LLM을 한 번 호출하고 끝내지 않고, LangGraph를 이용하여 처리 상태와 분기 흐름을 관리합니다.

```text
OCR
 ↓
상품 추출
 ↓
상품 분류
 ↓
검증
 ├── 정상 → 사용자 확인
 │
 └── 문제 있음 → 재분류 / 재처리
                       ↓
                    검증
                       ↓
                  사용자 확인
                       ↓
                     저장
```

LangGraph를 통해 LLM을 포함한 여러 작업을 상태(State)와 조건에 따라 연결하고 관리합니다.

### 6. 사용자 수정

OCR이나 LLM의 결과가 항상 정확하지 않을 수 있기 때문에 최종 저장 전에 사용자가 결과를 확인하고 수정할 수 있도록 구성합니다.

예:

```text
상품명
[ CJ)스팸라이트 120g ]

금액
[ 4,950원 ]

분류
[ 식비 ▼ ]

[ 수정 완료 ]
```

### 7. 지출 내역 저장

최종적으로 확인된 상품 및 분류 정보를 PostgreSQL/Supabase에 저장합니다.

---

## 전체 구조

```text
┌──────────────┐
│   React      │
│  모바일 UI   │
└──────┬───────┘
       │
       ↓
┌──────────────┐
│   FastAPI    │
│   Backend    │
└──────┬───────┘
       │
       ↓
┌──────────────────────┐
│      LangGraph       │
│                      │
│ OCR                  │
│  ↓                   │
│ 데이터 추출           │
│  ↓                   │
│ 상품 분류             │
│  ↓                   │
│ 검증                 │
│  ↓                   │
│ 재처리 / 사용자 확인  │
└──────┬───────────────┘
       │
       ├──────────────→ OCR Server
       │
       ├──────────────→ OpenAI API
       │
       └──────────────→ Supabase
```

---

## LangGraph Workflow

이 프로젝트에서 LangGraph는 단순히 LLM을 호출하기 위한 용도가 아니라, **영수증 처리 과정을 하나의 상태 기반 Workflow로 관리하기 위해 사용합니다.**

각 단계는 Node로 구성하고, 처리 결과에 따라 다음 단계가 결정됩니다.

```text
START
  ↓
OCR
  ↓
Extract
  ↓
Classify
  ↓
Validate
  ├── 정상 ─────→ Review
  │
  └── 문제 있음 → Reprocess
                       ↓
                    Validate
                       ↓
                     Review
                       ↓
                      Save
                       ↓
                      END
```

### 주요 개념

| 개념             | 역할                                 |
| ---------------- | ------------------------------------ |
| State            | 영수증 처리 과정에서 공유되는 데이터 |
| Node             | OCR, 분류, 검증 등의 개별 처리       |
| Edge             | 다음 처리 단계로 이동                |
| Conditional Edge | 검증 결과에 따른 분기                |
| Graph            | 전체 영수증 처리 Workflow            |

---

## OCR / LLM 처리 방향

현재 OCR 서버는 PaddleOCR-VL을 이용하고 있으며, OCR 결과를 OpenAI API를 통해 구조화하는 방식으로 구성합니다.

OCR 결과의 한글 상품명 인식 품질을 확인한 후, 필요할 경우 이미지 자체를 OpenAI Vision 모델에 전달하는 방식도 비교할 예정입니다.

### 비교 예정

동일한 영수증을 대상으로 다음 두 방식을 비교합니다.

```text
A. OCR 기반

영수증 이미지
    ↓
PaddleOCR-VL
    ↓
OCR Text
    ↓
OpenAI
    ↓
구조화 결과
```

```text
B. Vision 기반

영수증 이미지
    ↓
OpenAI Vision
    ↓
구조화 결과
```

다음 항목을 비교하여 실제 프로젝트에 적합한 방식을 선택할 예정입니다.

- 상품명 인식 오류
- 가격 및 수량 인식
- 전체 처리 시간
- API 비용

---

## 기술 스택

### Frontend

- React
- Vite
- Tailwind CSS

### Backend

- Python
- FastAPI
- LangGraph
- LangChain

### AI

- PaddleOCR-VL
- OpenAI API

### Database

- PostgreSQL
- Supabase

### Infrastructure

- Docker
- Git / GitHub

---

## 프로젝트 구조

```text
receipt_accounting_agent/
├── backend/
│   ├── venv/
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       └── graph/
│           └── receipt_graph.py
│
├── frontend/
│   └── ...
│
└── README.md
```

---

## 현재 개발 상태

### 완료

- [x] FastAPI 기본 서버 구성
- [x] LangGraph 기본 Workflow 구성
- [x] React + Vite 프로젝트 구성
- [x] Tailwind CSS 적용
- [x] 영수증 결과 UI 구성
- [x] 카테고리 아코디언 UI 구현
- [x] 모바일 환경 접속 테스트

### 개발 예정

- [ ] 영수증 이미지 업로드 API 연결
- [ ] 기존 OCR 서버 연동
- [ ] 실제 OCR 결과 분석
- [ ] OpenAI 기반 영수증 데이터 구조화
- [ ] 상품 카테고리 자동 분류
- [ ] LangGraph 검증 및 재처리 Workflow 구현
- [ ] 사용자 수정 기능
- [ ] Supabase 저장
- [ ] OCR / Vision 비교 실험
- [ ] 실제 모바일 환경 테스트
- [ ] Vercel 배포

---

## 실행 방법

### Backend

```bash
cd backend

# 가상환경 활성화
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn app.main:app --reload
```

FastAPI 서버:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

### Frontend

```bash
cd frontend

npm install
npm run dev
```

개발 환경에서 모바일 기기로 접속할 경우:

```bash
npm run dev -- --host
```

실제 배포 환경에서는 Vercel을 이용할 예정입니다.

---

## 향후 개선

- OCR 인식 품질 개선
- 상품 세부 카테고리 추가
- 사용자 수정 데이터를 활용한 분류 개선
- 영수증별 지출 통계
- 월별 / 카테고리별 지출 분석
- 모바일 환경 최적화
- PWA 적용 검토
- OCR 및 Vision 방식의 비용/성능 비교
