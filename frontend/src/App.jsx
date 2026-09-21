import { useState } from "react";

const receiptData = {
  totalAmount: 50290,
  categories: [
    {
      name: "식비",
      amount: 46010,
      items: [
        { name: "농심)짜왕멀티 4입", amount: 3980 },
        { name: "남양)아침에우유 900ml", amount: 3960 },
        { name: "CJ)몽글몽글봉지순두부 350g*2", amount: 2650 },
        { name: "CJ)스팸라이트 120g", amount: 4950 },
        { name: "햇무 1개", amount: 3960 },
        { name: "CJ)비비고깊은사골곰탕 500g", amount: 5900 },
        { name: "한성)유부초밥박사 320g", amount: 3980 },
        { name: "대림)초특가 얇은사각 160g", amount: 990 },
        { name: "오뚜기)맛있는왕교자(김치) 468g*2", amount: 6980 },
        { name: "오뚜기정통 오리엔탈 210g", amount: 2680 },
        { name: "백설)식용유 1.8L", amount: 5980 },
      ],
    },
    {
      name: "생활비",
      amount: 4280,
      items: [{ name: "LG)사프란핑크용기 3.1L", amount: 4280 }],
    },
    {
      name: "기타",
      amount: 0,
      items: [],
    },
  ],
};

function formatAmount(amount) {
  return amount.toLocaleString("ko-KR");
}

function App() {
  // 여러 카테고리를 동시에 열 수 있도록 배열로 관리
  const [openCategories, setOpenCategories] = useState(["식비"]);

  const toggleCategory = (categoryName) => {
    setOpenCategories((current) => {
      if (current.includes(categoryName)) {
        // 이미 열려 있으면 닫기
        return current.filter((name) => name !== categoryName);
      }

      // 닫혀 있으면 추가해서 열기
      return [...current, categoryName];
    });
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <main className="mx-auto max-w-md px-4 py-6">
        {/* 제목 */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">장바구니</h1>

          <p className="mt-1 text-lg font-semibold text-gray-700">
            {formatAmount(receiptData.totalAmount)}원
          </p>
        </div>

        {/* 카테고리 */}
        <div className="space-y-3">
          {receiptData.categories.map((category) => {
            const isOpen = openCategories.includes(category.name);

            return (
              <div
                key={category.name}
                className="overflow-hidden rounded-xl bg-white shadow-sm"
              >
                {/* 카테고리 버튼 */}
                <button
                  type="button"
                  onClick={() => toggleCategory(category.name)}
                  className="flex w-full items-center justify-between px-4 py-4 text-left"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-gray-500">{isOpen ? "▼" : "▶"}</span>

                    <span className="font-semibold text-gray-900">
                      {category.name}
                    </span>
                  </div>

                  <span className="font-semibold text-gray-700">
                    {formatAmount(category.amount)}원
                  </span>
                </button>

                {/* 상품 목록 */}
                <div
                  className={`overflow-hidden transition-all duration-300 ease-in-out ${
                    isOpen ? "max-h-[1000px] opacity-100" : "max-h-0 opacity-0"
                  }`}
                >
                  <div className="border-t border-gray-100 px-4 pb-3">
                    {category.items.length === 0 ? (
                      <p className="py-4 text-sm text-gray-400">
                        상품이 없습니다.
                      </p>
                    ) : (
                      category.items.map((item) => (
                        <div
                          key={item.name}
                          className="flex items-center justify-between border-b border-gray-100 py-3 last:border-b-0"
                        >
                          <span className="pr-4 text-sm text-gray-700">
                            {item.name}
                          </span>

                          <span className="shrink-0 text-sm font-medium text-gray-900">
                            {formatAmount(item.amount)}원
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* 영수증 업로드 */}
        <label
          htmlFor="receipt-upload"
          className="mt-6 block cursor-pointer rounded-xl bg-black px-4 py-4 text-center font-semibold text-white"
        >
          영수증 사진 추가
        </label>

        <input
          id="receipt-upload"
          type="file"
          accept="image/*"
          className="hidden"
        />
      </main>
    </div>
  );
}

export default App;
