import json

from app.graph.receipt_pipeline import receipt_pipeline
from create_excel import create_excel


result = receipt_pipeline.invoke({
    "image_paths": [
        "receipt_test_01.jpg",
        "receipt_test_02.jpg",
        "receipt_test_03.jpg",
        "receipt_test_04.jpg",
        "receipt_test_05.jpg",
    ],
    "ocr_results": [],
    "receipts": [],
    "vision_results": [],
})


print("\n========== OCR 결과 ==========\n")

for result_item in result["ocr_results"]:
    print(
        f"{result_item['filename']} "
        f"| OCR: {result_item['ocr_time']}초"
    )


print("\n========== LLM 결과 ==========\n")

for receipt in result["receipts"]:
    print(
        f"{receipt['filename']} "
        f"| LLM: {receipt['llm_time']}초 "
        f"| 비용: ${receipt['llm_cost']:.8f}"
    )

    print(
        json.dumps(
            receipt["receipt"],
            ensure_ascii=False,
            indent=2
        )
    )

    print("\n" + "=" * 60)


print("\n========== Vision 결과 ==========\n")

for vision in result["vision_results"]:
    print(
        f"{vision['filename']} "
        f"| Vision: {vision['vision_time']}초 "
        f"| 비용: ${vision['vision_cost']:.8f}"
    )

    print(
        json.dumps(
            vision["receipt"],
            ensure_ascii=False,
            indent=2
        )
    )

    print("\n" + "=" * 60)


create_excel(result)