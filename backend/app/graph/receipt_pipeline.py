import json
import os
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
    receipt_id: int
    merchant_name: str
    items: list
    has_items: bool
    already_classified: bool
    category_name: str
    category_id: int
    item_categories: list
    processing_type: str
    error: str


def load_receipt(state: ReceiptState):
    receipt_id = state["receipt_id"]

    receipt_result = (
        supabase
        .table("receipts")
        .select("id, merchant_name, category_id")
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

    # 영수증 자체에 category_id가 있으면 이미 최종 분류 완료
    if receipt.get("category_id") is not None:
        already_classified = True

    # 품목이 있는 경우 모든 품목에 category_id가 있으면
    # 이미 AI 분류가 끝난 것으로 판단
    elif has_items:
        already_classified = all(
            item.get("category_id") is not None
            for item in items
        )

    # 품목이 없는 경우 영수증 category_id가 있어야 분류 완료
    else:
        already_classified = False

    return {
        "merchant_name": receipt["merchant_name"],
        "items": items,
        "has_items": has_items,
        "category_id": receipt.get("category_id"),
        "already_classified": already_classified,
    }


def route_receipt(state: ReceiptState):
    # 영수증 category_id가 이미 있으면 완전히 끝난 데이터
    if state.get("category_id") is not None:
        print(
            f"[SKIP] receipt_id={state['receipt_id']} "
            "이미 분류된 영수증입니다."
        )
        return "already_classified"

    # 품목이 있고 모든 품목에 category_id가 있으면
    # OpenAI 호출 없이 기존 품목 분류 결과를 이용
    if state["has_items"] and state["already_classified"]:
        print(
            f"[RECEIPT CATEGORY] receipt_id={state['receipt_id']} "
            "기존 품목 분류 결과로 영수증 카테고리를 설정합니다."
        )
        return "set_receipt_category_from_items"

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

    result = json.loads(response.output_text)

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

    return {
        "category_name": result["category"],
        "processing_type": "receipt_classification",
    }


def save_item_categories(state: ReceiptState):
    item_categories = state.get("item_categories", [])

    category_result = (
        supabase
        .table("categories")
        .select("id, name")
        .execute()
    )

    category_map = {
        category["name"]: category["id"]
        for category in category_result.data
    }

    items = state["items"]

    for result in item_categories:
        item_name = result["item_name"]
        category_name = result["category"]

        category_id = category_map.get(category_name)

        if category_id is None:
            raise ValueError(
                f"존재하지 않는 카테고리입니다: {category_name}"
            )

        for item in items:
            if item["item_name"] == item_name:
                (
                    supabase
                    .table("receipt_items")
                    .update({
                        "category_id": category_id
                    })
                    .eq("id", item["id"])
                    .execute()
                )

    return {}


def set_receipt_category_from_items(state: ReceiptState):
    """
    이미 receipt_items에 저장된 category_id를 이용해
    receipts.category_id를 결정한다.

    가장 많이 등장한 카테고리를 대표 카테고리로 사용한다.
    """

    items = state["items"]

    category_ids = [
        item["category_id"]
        for item in items
        if item.get("category_id") is not None
    ]

    # 방금 classify_items → save_item_categories를 거친 경우
    # state["items"]에는 이전 category_id가 들어있을 수 있으므로
    # DB에서 최신 값을 다시 조회한다.
    items_result = (
        supabase
        .table("receipt_items")
        .select("id, category_id")
        .eq("receipt_id", state["receipt_id"])
        .execute()
    )

    latest_items = items_result.data or []

    category_ids = [
        item["category_id"]
        for item in latest_items
        if item.get("category_id") is not None
    ]

    if not category_ids:
        raise ValueError(
            f"receipt_id={state['receipt_id']} "
            "품목에 저장된 category_id가 없습니다."
        )

    category_id = Counter(category_ids).most_common(1)[0][0]

    category_result = (
        supabase
        .table("categories")
        .select("id, name")
        .eq("id", category_id)
        .single()
        .execute()
    )

    category = category_result.data

    if not category:
        raise ValueError(
            f"카테고리를 찾을 수 없습니다. category_id={category_id}"
        )

    return {
        "category_id": category["id"],
        "category_name": category["name"],
    }


def save_receipt_category(state: ReceiptState):
    category_name = state["category_name"]

    category_result = (
        supabase
        .table("categories")
        .select("id")
        .eq("name", category_name)
        .single()
        .execute()
    )

    category = category_result.data

    if not category:
        raise ValueError(
            f"존재하지 않는 카테고리입니다: {category_name}"
        )

    category_id = category["id"]

    (
        supabase
        .table("receipts")
        .update({
            "category_id": category_id
        })
        .eq("id", state["receipt_id"])
        .execute()
    )

    return {
        "category_id": category_id
    }


graph_builder = StateGraph(ReceiptState)

graph_builder.add_node("load_receipt", load_receipt)
graph_builder.add_node("classify_items", classify_items)
graph_builder.add_node("classify_receipt", classify_receipt)
graph_builder.add_node("save_item_categories", save_item_categories)
graph_builder.add_node(
    "set_receipt_category_from_items",
    set_receipt_category_from_items,
)
graph_builder.add_node(
    "save_receipt_category",
    save_receipt_category,
)

graph_builder.add_edge(
    START,
    "load_receipt",
)

graph_builder.add_conditional_edges(
    "load_receipt",
    route_receipt,
    {
        "already_classified": END,
        "set_receipt_category_from_items":
            "set_receipt_category_from_items",
        "classify_items":
            "classify_items",
        "classify_receipt":
            "classify_receipt",
    },
)

graph_builder.add_edge(
    "classify_items",
    "save_item_categories",
)

graph_builder.add_edge(
    "save_item_categories",
    "set_receipt_category_from_items",
)

graph_builder.add_edge(
    "set_receipt_category_from_items",
    "save_receipt_category",
)

graph_builder.add_edge(
    "classify_receipt",
    "save_receipt_category",
)

graph_builder.add_edge(
    "save_receipt_category",
    END,
)

receipt_graph = graph_builder.compile()