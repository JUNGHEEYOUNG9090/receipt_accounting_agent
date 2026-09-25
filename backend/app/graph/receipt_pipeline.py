import base64
import json
import os
import time
from typing import TypedDict

import requests
from dotenv import load_dotenv
from openai import OpenAI
from langgraph.graph import StateGraph, START, END


load_dotenv()


OCR_SERVER_URL = os.getenv("OCR_SERVER_URL")

if not OCR_SERVER_URL:
    raise RuntimeError(
        "OCR_SERVER_URL이 .env에 설정되지 않았습니다."
    )


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


MODEL = "gpt-4.1-mini"


class ReceiptState(TypedDict):
    image_paths: list[str]
    ocr_results: list[dict]
    receipts: list[dict]
    vision_results: list[dict]


# ============================================================
# OCR
# ============================================================

def process_receipt(state: ReceiptState):
    files = []

    try:
        for image_path in state["image_paths"]:
            file = open(image_path, "rb")

            files.append(
                (
                    "files",
                    (
                        os.path.basename(image_path),
                        file,
                        "image/jpeg",
                    ),
                )
            )

        response = requests.post(
            OCR_SERVER_URL,
            files=files,
            timeout=180,
        )

        response.raise_for_status()

        ocr_data = response.json()

        return {
            "ocr_results": ocr_data["files"]
        }

    finally:
        for _, (_, file, _) in files:
            file.close()


# ============================================================
# OCR → LLM
# ============================================================

def extract_receipt_data(state: ReceiptState):
    receipts = []

    for ocr in state["ocr_results"]:

        prompt = f"""
다음은 영수증 OCR 결과입니다.

OCR 결과:
{ocr["ocr_text"]}

OCR 결과를 분석하여 영수증 정보를 JSON으로 정리하세요.

다음 정보를 추출하세요.

- merchant_name: 가맹점명
- transaction_date: 거래일시
- items: 상품 목록
  - name: 상품명
  - unit_price: 단가
  - quantity: 수량
  - amount: 금액
- supply_amount: 공급가액
- vat: 부가세
- total_amount: 합계금액

중요한 규칙:

1. items는 반드시 배열([])로 반환하세요.
2. 상품이 없거나 확인하기 어려운 경우 items는 빈 배열 []을 사용하세요.
3. OCR 결과에 상품 항목이 확인되면 포함하세요.
4. 상품명, 단가, 수량, 금액 중 확인할 수 없는 값은 null로 처리하세요.
5. OCR 결과에 없는 정보를 임의로 만들어내지 마세요.
6. supply_amount, vat, total_amount는 계산하지 말고 OCR에서 확인되는 값을 사용하세요.
7. JSON 객체 하나만 반환하세요.
8. 설명이나 추가 문장을 출력하지 마세요.

반환 형식:

{{
  "merchant_name": "...",
  "transaction_date": "...",
  "items": [
    {{
      "name": "...",
      "unit_price": 0,
      "quantity": 1,
      "amount": 0
    }}
  ],
  "supply_amount": 0,
  "vat": 0,
  "total_amount": 0
}}
"""

        start = time.perf_counter()

        response = client.responses.create(
            model=MODEL,
            input=prompt,
        )

        result_text = response.output_text

        receipt = json.loads(result_text)

        llm_time = time.perf_counter() - start

        usage = response.usage

        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens

        input_cost = (
            input_tokens / 1_000_000
        ) * 0.40

        output_cost = (
            output_tokens / 1_000_000
        ) * 1.60

        llm_cost = input_cost + output_cost

        receipts.append({
            "filename": ocr["filename"],
            "receipt": receipt,
            "llm_time": round(llm_time, 3),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "llm_cost": round(llm_cost, 8),
        })

    return {
        "receipts": receipts
    }


# ============================================================
# Vision
# ============================================================

def extract_receipt_with_vision(state: ReceiptState):
    vision_results = []

    for image_path in state["image_paths"]:

        filename = os.path.basename(image_path)

        print(
            f"\n[Vision 시작] {filename}"
        )

        start = time.perf_counter()

        with open(image_path, "rb") as image_file:
            image_base64 = base64.b64encode(
                image_file.read()
            ).decode("utf-8")

        prompt = """
이미지에 있는 영수증을 직접 보고 정보를 추출하세요.

다음 정보를 JSON으로 정리하세요.

- merchant_name: 가맹점명
- transaction_date: 거래일시
- items: 상품 목록
  - name: 상품명
  - unit_price: 단가
  - quantity: 수량
  - amount: 금액
- supply_amount: 공급가액
- vat: 부가세
- total_amount: 합계금액

중요한 규칙:

1. 이미지에 실제로 보이는 정보만 사용하세요.
2. OCR 결과를 참고하지 말고 이미지 자체를 기준으로 판단하세요.
3. items는 반드시 배열([])로 반환하세요.
4. 상품명, 단가, 수량, 금액 중 확인할 수 없는 값은 null로 처리하세요.
5. 숫자는 이미지에 표시된 값을 사용하세요.
6. supply_amount, vat, total_amount를 임의로 계산하지 마세요.
7. 이미지에서 확인할 수 없는 값은 null로 처리하세요.
8. JSON 객체 하나만 반환하세요.
9. 설명이나 추가 문장을 출력하지 마세요.

반환 형식:

{
  "merchant_name": "...",
  "transaction_date": "...",
  "items": [
    {
      "name": "...",
      "unit_price": 0,
      "quantity": 1,
      "amount": 0
    }
  ],
  "supply_amount": 0,
  "vat": 0,
  "total_amount": 0
}
"""

        response = client.responses.create(
            model=MODEL,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        },
                        {
                            "type": "input_image",
                            "image_url": (
                                f"data:image/jpeg;base64,"
                                f"{image_base64}"
                            ),
                            "detail": "high",
                        },
                    ],
                }
            ],
        )

        result_text = response.output_text

        vision_receipt = json.loads(result_text)

        vision_time = time.perf_counter() - start

        usage = response.usage

        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens

        input_cost = (
            input_tokens / 1_000_000
        ) * 0.40

        output_cost = (
            output_tokens / 1_000_000
        ) * 1.60

        vision_cost = input_cost + output_cost

        vision_results.append({
            "filename": filename,
            "receipt": vision_receipt,
            "vision_time": round(vision_time, 3),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "vision_cost": round(vision_cost, 8),
        })

        print(
            f"[Vision 완료] {filename} "
            f"| {vision_time:.3f}초 "
            f"| 비용: ${vision_cost:.8f}"
        )

    return {
        "vision_results": vision_results
    }


# ============================================================
# Graph
# ============================================================

graph = StateGraph(ReceiptState)


graph.add_node(
    "process_receipt",
    process_receipt
)

graph.add_node(
    "extract_receipt_data",
    extract_receipt_data
)

graph.add_node(
    "extract_receipt_with_vision",
    extract_receipt_with_vision
)


graph.add_edge(
    START,
    "process_receipt"
)

graph.add_edge(
    "process_receipt",
    "extract_receipt_data"
)

graph.add_edge(
    "extract_receipt_data",
    "extract_receipt_with_vision"
)

graph.add_edge(
    "extract_receipt_with_vision",
    END
)


receipt_pipeline = graph.compile()