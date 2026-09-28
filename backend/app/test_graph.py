from app.graph.receipt_pipeline import receipt_graph
from app.supabase_client import supabase


result = (
    supabase
    .table("receipts")
    .select("id")
    .order("id")
    .execute()
)

receipt_ids = [row["id"] for row in result.data]

print(f"총 {len(receipt_ids)}개 영수증 처리")


for receipt_id in receipt_ids:
    print(f"\n--- receipt_id={receipt_id} ---")

    result = receipt_graph.invoke({
        "receipt_id": receipt_id
    })

    print(result)