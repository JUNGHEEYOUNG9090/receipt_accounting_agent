from pathlib import Path

from app.graph.receipt_pipeline import receipt_pipeline
from create_excel import create_excel


BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "images"


def main():
    # images 폴더의 영수증 이미지 전체 탐색
    image_paths = sorted(
        [
            file
            for file in IMAGE_DIR.iterdir()
            if file.is_file()
            and file.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ],
        key=lambda x: x.name,
    )

    if not image_paths:
        print("images 폴더에 이미지가 없습니다.")
        return

    print("=" * 60)
    print(f"총 {len(image_paths)}개의 영수증을 처리합니다.")
    print("=" * 60)

    for image_path in image_paths:
        print(f"- {image_path.name}")

    print("\n[Pipeline 시작]\n")

    # LangGraph 실행
    result = receipt_pipeline.invoke(
        {
            "image_paths": [str(path) for path in image_paths],
            "ocr_results": [],
            "receipts": [],
            "vision_results": [],
        }
    )

    print("\n" + "=" * 60)
    print("[Pipeline 완료]")
    print("=" * 60)

    print(f"OCR 결과    : {len(result.get('ocr_results', []))}개")
    print(f"LLM 결과    : {len(result.get('receipts', []))}개")
    print(f"Vision 결과 : {len(result.get('vision_results', []))}개")

    # Excel 생성
    create_excel(result)

    print("\nExcel 생성 완료!")


if __name__ == "__main__":
    main()
