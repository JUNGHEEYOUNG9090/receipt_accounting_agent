from pathlib import Path

# 이 파일이 있는 위치 기준으로 images 폴더 찾기
BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "images"

# 지원할 이미지 확장자
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# 이미지 파일 찾기
image_files = sorted(
    [
        file
        for file in IMAGE_DIR.iterdir()
        if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS
    ],
    key=lambda x: x.name
)

if not image_files:
    print("images 폴더에 이미지 파일이 없습니다.")
    exit()

print(f"총 {len(image_files)}개의 이미지를 찾았습니다.")

# 파일명 변경
for index, old_file in enumerate(image_files, start=1):
    new_file = IMAGE_DIR / f"receipt_{index:03d}{old_file.suffix.lower()}"

    old_file.rename(new_file)

    print(f"{old_file.name} -> {new_file.name}")

print("\n파일명 변경 완료!")
