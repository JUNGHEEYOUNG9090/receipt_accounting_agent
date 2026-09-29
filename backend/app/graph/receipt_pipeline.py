import json
import os
from pathlib import Path
from collections import Counter
from typing import TypedDict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from openai import OpenAI

from app.supabase_client import supabase


BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

load_dotenv(os.path.join(BASE_DIR, ".env"))

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def load_vision_receipt(filename: str):
    path = (
        Path(__file__).resolve().parents[3]
        / "evaluation"
        / "vision_results.json"
    )

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    for result in data["vision_results"]:
        if result["filename"] == filename:
            receipt = result["receipt"]

            items = [
                {
                    "id": index,
                    "item_name": item["name"],
                    "quantity": item.get("quantity"),
                    "unit_price": item.get("unit_price"),
                    "amount": item.get("amount"),
                    "category_id": None,
                }
                for index, item in enumerate(
                    receipt.get("items", []),
                    start=1,
                )
            ]

            return {
                "source": "vision",
                "receipt_id": None,

                "merchant_name": receipt["merchant_name"],
                "transaction_date": receipt["transaction_date"],
                "supply_amount": receipt.get("supply_amount"),
                "vat": receipt.get("vat"),
                "total_amount": receipt["total_amount"],
                "discount_amount": receipt.get("discount_amount") or 0,
                "payment_method": None,
                "category_id": None,

                "items": items,

                # LangGraph route_receipt()에서 사용하는 값
                "has_items": bool(items),
                "already_classified": False,

                "item_categories": [],
            }

    raise ValueError(
        f"Vision 결과를 찾을 수 없습니다: {filename}"
    )

CATEGORIES = [
    "식사",
    "카페/음료",
    "식료품",
    "주유",
    "교통",
    "생활용품",
    "위생용품",
    "의류",
    "문구/사무용품",
    "철물/공구",
    "의료/약품",
    "담배",
    "기타",
]


class ReceiptState(TypedDict, total=False):
    source: str
    receipt_id: int

    merchant_name: str
    transaction_date: str
    supply_amount: int
    vat: int
    total_amount: int
    discount_amount: int
    payment_method: str

    items: list

    has_items: bool
    already_classified: bool

    category_name: str
    category_id: int

    item_categories: list

    categories: list

    processing_type: str
    error: str


def load_receipt(state: ReceiptState):

    if state.get("source") == "vision":
        return state

    receipt_id = state["receipt_id"]

    receipt_result = (
        supabase
        .table("receipts")
        .select(
            "id, merchant_name, transaction_date, "
            "supply_amount, vat, total_amount, "
            "discount_amount, payment_method, category_id"
        )
        .eq("id", receipt_id)
        .single()
        .execute()
    )

    receipt = receipt_result.data

    if not receipt:
        raise ValueError(
            f"영수증을 찾을 수 없습니다. receipt_id={receipt_id}"
        )

    items_result = (
        supabase
        .table("receipt_items")
        .select(
            "id, item_name, quantity, unit_price, amount, category_id"
        )
        .eq("receipt_id", receipt_id)
        .execute()
    )

    items = items_result.data or []
    has_items = len(items) > 0

    if receipt.get("category_id") is not None:
        already_classified = True

    elif has_items:
        already_classified = all(
            item.get("category_id") is not None
            for item in items
        )

    else:
        already_classified = False

    return {
        "merchant_name": receipt["merchant_name"],
        "transaction_date": receipt["transaction_date"],
        "supply_amount": receipt.get("supply_amount"),
        "vat": receipt.get("vat"),
        "total_amount": receipt["total_amount"],
        "discount_amount": receipt.get("discount_amount") or 0,
        "payment_method": receipt.get("payment_method"),
        "items": items,
        "has_items": has_items,
        "category_id": receipt.get("category_id"),
        "already_classified": already_classified,
    }


def route_receipt(state: ReceiptState):
    # 영수증 자체에 이미 category_id가 있으면
    # 기존 DB 결과를 사용한다.
    if state.get("category_id") is not None:
        print(
            f"[SKIP] receipt_id={state['receipt_id']} "
            "이미 분류된 영수증입니다."
        )
        return "already_classified"

    # 품목이 있고 모든 품목에 category_id가 있으면
    # OpenAI를 다시 호출하지 않는다.
    if state["has_items"] and state["already_classified"]:
        print(
            f"[RECEIPT CATEGORY] receipt_id={state['receipt_id']} "
            "기존 품목 분류 결과를 사용합니다."
        )
        return "build_result"

    # 품목이 있으면 상품명 기준 AI 분류
    if state["has_items"]:
        print(
            f"[CLASSIFY] receipt_id={state['receipt_id']} "
            "품목 기준으로 분류합니다."
        )
        return "classify_items"

    # 품목이 없으면 가맹점명 기준 AI 분류
    print(
        f"[CLASSIFY] receipt_id={state['receipt_id']} "
        "가맹점명 기준으로 분류합니다."
    )
    return "classify_receipt"


def classify_items(state: ReceiptState):
    items = state["items"]

    item_names = [
        item["item_name"]
        for item in items
        if item.get("item_name")
    ]

    if not item_names:
        return {
            "error": "품목명은 존재하지 않습니다.",
            "processing_type": "item_classification",
        }

    prompt = f"""
영수증의 상품명을 보고 지출 카테고리를 분류하세요.

사용 가능한 카테고리는 반드시 다음 13개 중 하나입니다.

{json.dumps(CATEGORIES, ensure_ascii=False)}

상품명:
{json.dumps(item_names, ensure_ascii=False)}

각 상품에 대해 가장 적절한 카테고리를 하나씩 선택하세요.

반드시 JSON 배열만 반환하세요.

형식:
[
  {{
    "item_name": "상품명",
    "category": "카테고리"
  }}
]
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    try:
        result = json.loads(response.output_text)
    except json.JSONDecodeError:
        raise ValueError(
            f"LLM이 올바른 JSON을 반환하지 않았습니다: "
            f"{response.output_text!r}"
        )

    print("LLM 응답:", repr(response.output_text))

    return {
        "item_categories": result,
        "processing_type": "item_classification",
    }


def classify_receipt(state: ReceiptState):
    merchant_name = state["merchant_name"]

    prompt = f"""
영수증의 가맹점명을 보고 지출 카테고리를 분류하세요.

사용 가능한 카테고리는 반드시 다음 13개 중 하나입니다.

{json.dumps(CATEGORIES, ensure_ascii=False)}

가맹점명:
{merchant_name}

상품 정보가 없는 영수증이므로 가맹점명을 중심으로 판단하세요.

예:
시골밥상 → 식사
하나철물 → 철물/공구
연희연세약국 → 의료/약품
고양(하)주유소 → 주유

반드시 JSON 객체 하나만 반환하세요.

형식:
{{
  "category": "카테고리"
}}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    result = json.loads(response.output_text)

    print("LLM 분류 결과:", result)

    return {
        "category_name": result["category"],
        "processing_type": "receipt_classification",
    }


def build_result(state: ReceiptState):
    """
    AI 분류 결과 또는 기존 DB 분류 결과를
    프런트에서 사용할 수 있는 형태로 만든다.

    여기서는 DB에 저장하지 않는다.
    """

    items = state.get("items", [])

    # categories 테이블 조회
    category_result = (
        supabase
        .table("categories")
        .select("id, name")
        .execute()
    )

    category_map = {
        category["id"]: category["name"]
        for category in (category_result.data or [])
    }

    category_name_to_id = {
        category["name"]: category["id"]
        for category in (category_result.data or [])
    }

    # --------------------------------------------------
    # 1. 이미 DB에 분류된 품목이 있는 경우
    # --------------------------------------------------

    if state.get("already_classified") and items:

        grouped = {}

        for item in items:
            category_id = item.get("category_id")

            if category_id is not None:
                category_name = category_map.get(
                    category_id,
                    "기타"
                )
            else:
                # 영수증 category_id만 있고
                # 품목 category_id가 없는 경우
                category_id = state.get("category_id")
                category_name = category_map.get(
                    category_id,
                    "기타"
                )

            if category_name not in grouped:
                grouped[category_name] = {
                    "name": category_name,
                    "categoryId": category_id,
                    "amount": 0,
                    "items": [],
                }

            amount = item.get("amount") or 0

            grouped[category_name]["items"].append({
                "id": item["id"],
                "name": item["item_name"],
                "merchantName": state["merchant_name"],
                "quantity": item.get("quantity"),
                "unitPrice": item.get("unit_price"),
                "amount": amount,
                "categoryId": category_id,
            })
        for category in grouped.values():
            category["amount"] = state["total_amount"]

        return {
            "merchant_name": state["merchant_name"],
            "transaction_date": state["transaction_date"],
            "supply_amount": state.get("supply_amount"),
            "vat": state.get("vat"),
            "total_amount": state["total_amount"],
            "discount_amount": state.get("discount_amount", 0),
            "payment_method": state.get("payment_method"),
            "category_id": state.get("category_id"),
            "categories": list(grouped.values()),
        }

    # --------------------------------------------------
    # 2. 새롭게 AI가 품목을 분류한 경우
    # --------------------------------------------------

    item_categories = state.get("item_categories", [])

    if item_categories:

        classification_map = {
            result["item_name"]: result["category"]
            for result in item_categories
        }

        grouped = {}

        for item in items:
            item_name = item["item_name"]

            category_name = classification_map.get(
                item_name,
                "기타"
            )

            category_id = category_name_to_id.get(
                category_name
            )

            if category_name not in grouped:
                grouped[category_name] = {
                    "name": category_name,
                    "categoryId": category_id,
                    "amount": 0,
                    "items": [],
                }

            amount = item.get("amount") or 0

            grouped[category_name]["items"].append({
                "id": item["id"],
                "name": item_name,
                "merchantName": state["merchant_name"],
                "quantity": item.get("quantity"),
                "unitPrice": item.get("unit_price"),
                "amount": amount,
                "categoryId": category_id,
            })

        for category in grouped.values():
            category["amount"] = state["total_amount"]

        return {
            "merchant_name": state["merchant_name"],
            "transaction_date": state["transaction_date"],
            "supply_amount": state.get("supply_amount"),
            "vat": state.get("vat"),
            "total_amount": state["total_amount"],
            "discount_amount": state.get("discount_amount", 0),
            "payment_method": state.get("payment_method"),
            "category_id": state.get("category_id"),
            "categories": list(grouped.values()),
        }

    # --------------------------------------------------
    # 3. 품목이 없는 영수증
    # --------------------------------------------------

    category_name = state.get(
        "category_name",
        "기타"
    )

    category_id = category_name_to_id.get(
        category_name
    )

    return {
        "merchant_name": state["merchant_name"],
        "transaction_date": state["transaction_date"],
        "supply_amount": state.get("supply_amount"),
        "vat": state.get("vat"),
        "total_amount": state["total_amount"],
        "discount_amount": state.get("discount_amount", 0),
        "payment_method": state.get("payment_method"),
        "category_id": category_id,
        "categories": [
            {
                "name": category_name,
                "categoryId": category_id,
                "amount": state["total_amount"],
                "items": [],
            }
        ],
    }


graph_builder = StateGraph(ReceiptState)

graph_builder.add_node(
    "load_receipt",
    load_receipt
)

graph_builder.add_node(
    "classify_items",
    classify_items
)

graph_builder.add_node(
    "classify_receipt",
    classify_receipt
)

graph_builder.add_node(
    "build_result",
    build_result
)


graph_builder.add_edge(
    START,
    "load_receipt",
)


graph_builder.add_conditional_edges(
    "load_receipt",
    route_receipt,
    {
        "already_classified": "build_result",
        "build_result": "build_result",
        "classify_items": "classify_items",
        "classify_receipt": "classify_receipt",
    },
)


graph_builder.add_edge(
    "classify_items",
    "build_result",
)

graph_builder.add_edge(
    "classify_receipt",
    "build_result",
)

graph_builder.add_edge(
    "build_result",
    END,
)


receipt_graph = graph_builder.compile()