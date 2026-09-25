import json

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment


OUTPUT_FILE = "receipt_comparison.xlsx"


# --------------------------------
# 실제값
# --------------------------------

GROUND_TRUTH = {
    "receipt_test_01.jpg": """
우림시장식자재마트
사업자번호:112-21-21467
대표자:손지현
주소:서울 중랑구 봉우재로71길 18
전화번호:02-493-8249

NO. 상품명 단가 수량 금액

001 햇 무 1개 990 1 990
002 25년햅쌀) 진품메뚜기쌀 20kg 59,800 1 59,800
003 오뚜기) 옛날자른당면 500g 6,980 1 6,980
004 CJ) 행복한콩단단한큰두부 800g 1,980 1 1,980
005 동서) 스위트콘 425g 1,180 1 1,180
006 오뚜기) 그린바질드레싱 215g 2,980 1 2,980
007 농심) 너구리얼큰한맛멀티 5입 4,580 1 4,580

할인금액:-45,910
면세물품:62,770
과세물품:14,291
부가세(VAT):1,429
합계:78,490

신용카드지불:78,490
고객:김용*
적립포인트:5,198
승인금액:78,490
승인번호:26494017
전표No:102335
거래NO:0920110840
계산원:박옥희(063)

2509201108402
""".strip(),

    "receipt_test_02.jpg": """
[구매] 2017-06-02 21:13

001 노브랜드 굿밀크우 1,680 1 1,680
002 스마트알뜰양복커버 2,590 1 2,590
003 농심 포스틱 84g 1,120 1 1,120
004 농심 올리브짜파게 3,850 1 3,850
005 산딸기 500g/박스 6,980 1 6,980
006 (G)서핑여워터슈NY 19,800 1 19,800
007 대여용부직포쇼핑백 500 1 500
008 호주꼭물오이스터블 14,720 1 14,720
009 오뚜기 콤비네이션 5,980 1 5,980
010 꼬깔큰허니버터132G 1,580 1 1,580
011 CJ미니드레싱골라담 3,980 1 3,980
012 청정원허브맛솔트( 1,980 1 1,980
013 태국미니아스파라거 4,580 1 4,580
014 롯데 수박바젤리 56 980 2 1,960
015 바리스타 쇼콜라 32 2,250 1 2,250

면세물품:27,960
과세물품:41,445
부가세:4,145
합계:73,550
""".strip(),

    "receipt_test_03.jpg": """
우림시장식자재마트

001 LG)샤프란핑크옹기 3.1L 4,280 1 4,280
002 농심)짜왕멀티 4입 3,980 1 3,980
003 남양)아짐에우유 900ml 1,980 2 3,960
004 CJ)몽굴몽굴뚱지순두부 350g*2 2,650 1 2,650
005 CJ)스팸라이트 120g 990 5 4,950
006 햇 무 1개 1,980 2 3,960
007 CJ)비비고깊은사골곰탕 500g 1,180 5 5,900
008 한성)유부초밥박사 320g 3,980 1 3,980
009 대림)초특가 얇은사각 160g 990 1 990
010 오뚜기)맛있는왕교자(김치) 468g*2 6,980 1 6,980
011 오뚜기정통 오리엔탈 210g 2,680 1 2,680
012 백설)식용유 1.8L 5,980 1 5,980

할인금액:-41,900
면세물품:10,570
과세물품:36,110
부가세:3,610
합계:50,290
""".strip(),

    "receipt_test_04.jpg": """
우림시장식자재마트
사업자번호:112-21-21467
대표자:손지현
주소:서울 중랑구 봉우재로71길 18
전화번호:02-493-8249

거래일시:26-09-20 10:23

001 햇 무 1개 990 1 990
002 25년햅쌀) 진품메뚜기쌀 20kg 59,800 1 59,800
003 오뚜기) 옛날자른당면 500g 6,980 1 6,980
004 CJ) 행복한콩단단한큰두부 800g 1,980 1 1,980
005 동서) 스위트콘 425g 1,180 1 1,180
006 오뚜기) 그린바질드레싱 215g 2,980 1 2,980
007 농심) 너구리얼큰한맛멀티 5입 4,580 1 4,580

할인금액:-45,910
면세물품:62,770
과세물품:14,291
부가세:1,429
합계:78,490
""".strip(),

    "receipt_test_05.jpg": """
우림시장식자재마트

거래일시:26-09-20 10:25

늘푸른계란(특란) 30구
8,800 1 8,800

합계:8,800
""".strip(),
}


# --------------------------------
# 테스트 이미지별 실제 촬영 조건
# --------------------------------

TEST_CONDITIONS = {
    "receipt_test_01.jpg": "가로(landscape) 촬영",
    "receipt_test_02.jpg": "가깝게 촬영 + 손가락 일부 포함",
    "receipt_test_03.jpg": "긴 영수증 + 좌우 여백 많음 + 배경에 흐릿한 사람",
    "receipt_test_04.jpg": "세로 촬영 + 빛/반사 영향",
    "receipt_test_05.jpg": "짧은 영수증 + 접힌 부분이 많음",
}


def create_excel(result):

    wb = Workbook()

    # ========================================
    # 결과 데이터 매핑
    # ========================================

    ocr_map = {
        item["filename"]: item
        for item in result["ocr_results"]
    }

    llm_map = {
        item["filename"]: item
        for item in result["receipts"]
    }

    vision_map = {
        item["filename"]: item
        for item in result["vision_results"]
    }

    # ========================================
    # 1. 비교결과
    # ========================================

    ws = wb.active
    ws.title = "비교결과"

    ws.append([
        "파일명",
        "필드",
        "실제값",
        "OCR 결과",
        "LLM 결과",
        "Vision 결과",
    ])

    for filename in ocr_map:

        ocr_data = ocr_map[filename]

        ocr_text = ocr_data.get(
            "ocr_text",
            ""
        )

        llm_data = llm_map.get(
            filename,
            {}
        )

        llm_receipt = llm_data.get(
            "receipt",
            {}
        )

        vision_data = vision_map.get(
            filename,
            {}
        )

        vision_receipt = vision_data.get(
            "receipt",
            {}
        )

        # LLM JSON 전체
        llm_text = ""

        if llm_receipt:
            llm_text = json.dumps(
                llm_receipt,
                ensure_ascii=False,
                indent=2
            )

        # Vision JSON 전체
        vision_text = ""

        if vision_receipt:
            vision_text = json.dumps(
                vision_receipt,
                ensure_ascii=False,
                indent=2
            )

        ws.append([
            filename,
            "OCR 전체 결과",
            GROUND_TRUTH.get(
                filename,
                ""
            ),
            ocr_text,
            llm_text,
            vision_text,
        ])

    # ========================================
    # 2. 성능
    # ========================================

    perf = wb.create_sheet("성능")

    perf.append([
        "파일명",
        "OCR 시간(초)",
        "LLM 시간(초)",
        "Vision 시간(초)",
        "전체 시간(초)",
        "LLM 비용",
        "Vision 비용",
        "Vision 호출 여부",
    ])

    for filename in ocr_map:

        ocr_data = ocr_map[filename]

        ocr_time = ocr_data.get(
            "ocr_time",
            ""
        )

        llm_data = llm_map.get(
            filename,
            {}
        )

        vision_data = vision_map.get(
            filename,
            {}
        )

        llm_time = llm_data.get(
            "llm_time",
            ""
        )

        vision_time = vision_data.get(
            "vision_time",
            ""
        )

        # OCR + LLM + Vision
        times = [
            value
            for value in [
                ocr_time,
                llm_time,
                vision_time,
            ]
            if value != ""
        ]

        if times:
            total_time = round(
                sum(times),
                3
            )
        else:
            total_time = ""

        vision_called = (
            "O"
            if vision_data
            else "X"
        )

        perf.append([
            filename,
            ocr_time,
            llm_time,
            vision_time,
            total_time,
            llm_data.get(
                "llm_cost",
                ""
            ),
            vision_data.get(
                "vision_cost",
                ""
            ),
            vision_called,
        ])

    # ========================================
    # 3. 테스트 조건
    # ========================================

    condition_ws = wb.create_sheet(
        "테스트조건"
    )

    condition_ws.append([
        "파일명",
        "촬영 조건",
    ])

    for filename, condition in TEST_CONDITIONS.items():

        condition_ws.append([
            filename,
            condition,
        ])

    # ========================================
    # 스타일
    # ========================================

    header_fill = PatternFill(
        fill_type="solid",
        fgColor="D9EAF7",
    )

    for sheet in wb.worksheets:

        sheet.freeze_panes = "A2"

        for cell in sheet[1]:

            cell.font = Font(
                bold=True
            )

            cell.fill = header_fill

            cell.alignment = Alignment(
                horizontal="center",
                vertical="center",
            )

        for row in sheet.iter_rows():

            for cell in row:

                cell.alignment = Alignment(
                    vertical="top",
                    wrap_text=True,
                )

    # ========================================
    # 비교결과 열 너비
    # ========================================

    comparison_widths = {
        "A": 24,
        "B": 18,
        "C": 70,
        "D": 70,
        "E": 70,
        "F": 70,
    }

    for column, width in comparison_widths.items():

        ws.column_dimensions[column].width = width

    # ========================================
    # 성능 열 너비
    # ========================================

    perf_widths = {
        "A": 24,
        "B": 16,
        "C": 16,
        "D": 18,
        "E": 16,
        "F": 16,
        "G": 16,
        "H": 18,
    }

    for column, width in perf_widths.items():

        perf.column_dimensions[column].width = width

    # ========================================
    # 테스트 조건 열 너비
    # ========================================

    condition_ws.column_dimensions["A"].width = 24
    condition_ws.column_dimensions["B"].width = 60

    # ========================================
    # 필터
    # ========================================

    ws.auto_filter.ref = ws.dimensions
    perf.auto_filter.ref = perf.dimensions
    condition_ws.auto_filter.ref = condition_ws.dimensions

    # ========================================
    # 저장
    # ========================================

    wb.save(OUTPUT_FILE)

    print(
        f"\nExcel 생성 완료 : {OUTPUT_FILE}"
    )