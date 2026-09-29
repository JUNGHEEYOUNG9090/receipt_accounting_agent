from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

from app.supabase_client import supabase
from fastapi.middleware.cors import CORSMiddleware

from app.graph.receipt_pipeline import (
    receipt_graph,
    load_vision_receipt,
)
from datetime import date, datetime, timedelta


app = FastAPI()

class ReceiptItemUpdateRequest(BaseModel):
    id: Optional[int] = None
    name: str
    quantity: Optional[float] = None
    unitPrice: Optional[int] = None
    amount: int
    categoryId: Optional[int] = None


class ReceiptEditRequest(BaseModel):
    merchantName: str
    transactionDate: str
    supplyAmount: Optional[int] = None
    vat: Optional[int] = None
    totalAmount: int
    discountAmount: int = 0
    paymentMethod: Optional[str] = None
    categoryId: Optional[int] = None
    items: list[ReceiptItemUpdateRequest] = []


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Receipt Accounting Agent"}


@app.get("/test-agent")
def test_agent(receipt_id: int):
    result = receipt_graph.invoke({
        "receipt_id": receipt_id
    })

    return {
        "merchantName": result["merchant_name"],
        "transactionDate": result["transaction_date"],
        "supplyAmount": result.get("supply_amount"),
        "vat": result.get("vat"),
        "totalAmount": result["total_amount"],
        "discountAmount": result.get("discount_amount", 0),
        "paymentMethod": result.get("payment_method"),
        "categoryId": result.get("category_id"),
        "categories": result["categories"],
    }


@app.get("/test-vision-agent")
def test_vision_agent(filename: str):
    state = load_vision_receipt(filename)

    result = receipt_graph.invoke(state)

    return {
        "merchantName": result["merchant_name"],
        "transactionDate": result["transaction_date"],
        "supplyAmount": result.get("supply_amount"),
        "vat": result.get("vat"),
        "totalAmount": result["total_amount"],
        "discountAmount": result.get("discount_amount", 0),
        "paymentMethod": result.get("payment_method"),
        "categoryId": result.get("category_id"),
        "categories": result["categories"],
    }


@app.patch("/receipts/{receipt_id}")
def update_receipt(
    receipt_id: int,
    request: ReceiptEditRequest,
):
    # 영수증 수정
    receipt_result = (
        supabase
        .table("receipts")
        .update({
            "merchant_name": request.merchantName,
            "transaction_date": request.transactionDate,
            "supply_amount": request.supplyAmount,
            "vat": request.vat,
            "total_amount": request.totalAmount,
            "discount_amount": request.discountAmount,
            "payment_method": request.paymentMethod,
            "category_id": request.categoryId,
        })
        .eq("id", receipt_id)
        .execute()
    )

    if not receipt_result.data:
        raise RuntimeError("영수증 수정에 실패했습니다.")

    # 현재 DB에 존재하는 item
    existing_items_result = (
        supabase
        .table("receipt_items")
        .select("id")
        .eq("receipt_id", receipt_id)
        .execute()
    )

    existing_item_ids = {
        item["id"]
        for item in (existing_items_result.data or [])
    }

    # 프론트에서 현재 남아있는 item
    request_item_ids = {
        item.id
        for item in request.items
    }

    # 프론트에서 삭제된 item
    deleted_item_ids = existing_item_ids - request_item_ids

    # 삭제된 item 삭제
    for item_id in deleted_item_ids:
        supabase \
            .table("receipt_items") \
            .delete() \
            .eq("id", item_id) \
            .eq("receipt_id", receipt_id) \
            .execute()

    # 남아있는 item 수정
    # item 수정 또는 추가
    for item in request.items:

        # 새로 추가된 item
        if item.id is None:
            insert_result = (
                supabase
                .table("receipt_items")
                .insert({
                    "receipt_id": receipt_id,
                    "item_name": item.name,
                    "quantity": item.quantity,
                    "unit_price": item.unitPrice,
                    "amount": item.amount,
                    "category_id": item.categoryId,
                })
                .execute()
            )

            if not insert_result.data:
                raise RuntimeError("아이템 추가에 실패했습니다.")

            continue

        # 기존 item 수정
        item_result = (
            supabase
            .table("receipt_items")
            .update({
                "item_name": item.name,
                "quantity": item.quantity,
                "unit_price": item.unitPrice,
                "amount": item.amount,
                "category_id": item.categoryId,
            })
            .eq("id", item.id)
            .eq("receipt_id", receipt_id)
            .execute()
        )

        if not item_result.data:
            raise RuntimeError(
                f"아이템 수정에 실패했습니다. item_id={item.id}"
            )

    # 아이템이 하나도 남지 않았다면 영수증도 삭제
    if len(request.items) == 0:
        delete_result = (
            supabase
            .table("receipts")
            .delete()
            .eq("id", receipt_id)
            .execute()
        )

        if not delete_result.data:
            raise RuntimeError(
                f"영수증 삭제에 실패했습니다. receipt_id={receipt_id}"
            )

        return {
            "id": receipt_id,
            "message": "영수증이 삭제되었습니다.",
        }

    return {
        "id": receipt_id,
        "message": "영수증이 저장되었습니다.",
    }


@app.delete("/receipts/{receipt_id}")
def delete_receipt(receipt_id: int):
    # 1. 품목 삭제
    supabase \
        .table("receipt_items") \
        .delete() \
        .eq("receipt_id", receipt_id) \
        .execute()

    # 2. 영수증 삭제
    receipt_result = (
        supabase
        .table("receipts")
        .delete()
        .eq("id", receipt_id)
        .execute()
    )

    if not receipt_result.data:
        raise RuntimeError(
            f"영수증 삭제에 실패했습니다. receipt_id={receipt_id}"
        )

    return {
        "id": receipt_id,
        "message": "영수증이 삭제되었습니다.",
    }

@app.get("/receipts")
def get_receipts(target_date: date):
    receipts_result = (
        supabase
        .table("receipts")
        .select(
            "id, merchant_name, transaction_date, "
            "supply_amount, vat, total_amount, "
            "discount_amount, payment_method, category_id"
        )
        .gte("transaction_date", target_date.isoformat())
        .lt(
            "transaction_date",
            (target_date + timedelta(days=1)).isoformat(),
        )
        .order("id")
        .execute()
    )

    receipts = receipts_result.data or []

    result = []

    for receipt in receipts:
        items_result = (
            supabase
            .table("receipt_items")
            .select(
                "id, item_name, quantity, unit_price, "
                "amount, category_id"
            )
            .eq("receipt_id", receipt["id"])
            .execute()
        )

        items = items_result.data or []

        result.append({
            "receiptId": receipt["id"],
            "merchantName": receipt["merchant_name"],
            "transactionDate": receipt["transaction_date"],
            "supplyAmount": receipt.get("supply_amount"),
            "vat": receipt.get("vat"),
            "totalAmount": receipt["total_amount"],
            "discountAmount": receipt.get("discount_amount") or 0,
            "paymentMethod": receipt.get("payment_method"),
            "categoryId": receipt.get("category_id"),
            "items": [
                {
                    "id": item["id"],
                    "name": item["item_name"],
                    "quantity": item.get("quantity"),
                    "unitPrice": item.get("unit_price"),
                    "amount": item.get("amount"),
                    "categoryId": item.get("category_id"),
                }
                for item in items
            ],
        })

    return {
        "date": target_date.isoformat(),
        "totalAmount": sum(
            receipt.get("total_amount") or 0
            for receipt in receipts
        ),
        "receipts": result,
    }