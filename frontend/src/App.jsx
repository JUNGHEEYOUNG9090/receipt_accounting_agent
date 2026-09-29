import { useEffect, useState } from "react";

function formatAmount(amount) {
  return (Number(amount) || 0).toLocaleString("ko-KR");
}

const categoryOptions = [
  { id: 1, name: "식사" },
  { id: 2, name: "카페/음료" },
  { id: 3, name: "식료품" },
  { id: 4, name: "주유" },
  { id: 5, name: "교통" },
  { id: 6, name: "생활용품" },
  { id: 7, name: "위생용품" },
  { id: 8, name: "의류" },
  { id: 9, name: "문구/사무용품" },
  { id: 10, name: "철물/공구" },
  { id: 11, name: "의료/약품" },
  { id: 12, name: "담배" },
  { id: 13, name: "기타" },
];
const loadReceipts = async (date, setReceipts) => {
  try {
    const response = await fetch(
      `http://localhost:8000/receipts?target_date=${date}`,
    );

    if (!response.ok) {
      throw new Error("영수증 조회에 실패했습니다.");
    }

    const data = await response.json();
    setReceipts(data.receipts || []);
  } catch (error) {
    console.error(error);
    alert("영수증 조회에 실패했습니다.");
  }
};
function App() {
  const [receipts, setReceipts] = useState([]);
  const [selectedDate, setSelectedDate] = useState(
    localStorage.getItem("selectedDate") ||
      new Date().toLocaleDateString("sv-SE"),
  );

  const [openCategories, setOpenCategories] = useState(["식사"]);

  // 품목 수정 상태
  const [editingItems, setEditingItems] = useState({});

  // 가게명 수정 상태
  const [editingMerchants, setEditingMerchants] = useState({});

  // 아이템별 카테고리 수정 상태
  const [editingItemCategories, setEditingItemCategories] = useState({});

  useEffect(() => {
    loadReceipts(selectedDate, setReceipts);
  }, [selectedDate]);

  const moveDate = (days) => {
    const date = new Date(selectedDate);

    date.setDate(date.getDate() + days);

    setSelectedDate(date.toISOString().split("T")[0]);
  };

  const toggleCategory = (categoryKey) => {
    setOpenCategories((current) => {
      if (current.includes(categoryKey)) {
        return current.filter((key) => key !== categoryKey);
      }

      return [...current, categoryKey];
    });
  };

  const buildCategories = (receipts) => {
    const categoryMap = {};

    receipts.forEach((receipt) => {
      // 품목이 있는 영수증
      receipt.items.forEach((item) => {
        const categoryId = item.categoryId;

        if (!categoryMap[categoryId]) {
          const category = categoryOptions.find(
            (option) => option.id === categoryId,
          );

          categoryMap[categoryId] = {
            categoryId,
            name: category?.name || "기타",
            amount: 0,
            receipts: [],
          };
        }

        categoryMap[categoryId].amount += Number(item.amount) || 0;

        let receiptGroup = categoryMap[categoryId].receipts.find(
          (group) => group.receiptId === receipt.receiptId,
        );

        if (!receiptGroup) {
          receiptGroup = {
            receiptId: receipt.receiptId,
            merchantName: receipt.merchantName,
            items: [],
          };

          categoryMap[categoryId].receipts.push(receiptGroup);
        }

        receiptGroup.items.push(item);
      });

      // 품목이 없는 영수증
      if (receipt.items.length === 0 && receipt.categoryId) {
        const categoryId = receipt.categoryId;

        if (!categoryMap[categoryId]) {
          const category = categoryOptions.find(
            (option) => option.id === categoryId,
          );

          categoryMap[categoryId] = {
            categoryId,
            name: category?.name || "기타",
            amount: 0,
            receipts: [],
          };
        }

        categoryMap[categoryId].amount += Number(receipt.totalAmount) || 0;

        categoryMap[categoryId].receipts.push({
          receiptId: receipt.receiptId,
          merchantName: receipt.merchantName,
          items: [],
        });
      }
    });

    return Object.values(categoryMap);
  };

  // -----------------------------
  // 품목 수정
  // -----------------------------

  const toggleItemEditing = (itemId) => {
    setEditingItems((current) => ({
      ...current,
      [itemId]: !current[itemId],
    }));
  };

  const changeItem = (receiptId, itemId, field, value) => {
    setReceipts((current) =>
      current.map((receipt) => {
        if (receipt.receiptId !== receiptId) {
          return receipt;
        }

        return {
          ...receipt,
          items: receipt.items.map((item) => {
            if (item.id !== itemId) {
              return item;
            }

            const updatedItem = {
              ...item,
              [field]: value,
            };

            const quantity = Number(updatedItem.quantity) || 0;
            const unitPrice = Number(updatedItem.unitPrice) || 0;

            updatedItem.amount = quantity * unitPrice;

            return updatedItem;
          }),
        };
      }),
    );
  };

  // -----------------------------
  // 가게명 수정
  // -----------------------------

  const toggleMerchantEditing = (receiptId) => {
    setEditingMerchants((current) => ({
      ...current,
      [receiptId]: !current[receiptId],
    }));
  };

  const changeMerchantName = (receiptId, value) => {
    setReceipts((current) =>
      current.map((receipt) =>
        receipt.receiptId === receiptId
          ? {
              ...receipt,
              merchantName: value,
            }
          : receipt,
      ),
    );
  };

  // -----------------------------
  // 아이템별 카테고리 수정
  // -----------------------------

  const toggleItemCategoryEditing = (itemId) => {
    setEditingItemCategories((current) => ({
      ...current,
      [itemId]: !current[itemId],
    }));
  };

  const changeItemCategory = (receiptId, itemId, categoryId) => {
    setReceipts((current) =>
      current.map((receipt) => {
        if (receipt.receiptId !== receiptId) {
          return receipt;
        }

        return {
          ...receipt,
          items: receipt.items.map((item) =>
            item.id === itemId
              ? {
                  ...item,
                  categoryId,
                }
              : item,
          ),
        };
      }),
    );

    // 변경한 카테고리 아코디언 자동 열기
    const categoryKey = `${receiptId}-${categoryId}`;

    setOpenCategories((current) => {
      if (current.includes(categoryKey)) {
        return current;
      }

      return [...current, categoryKey];
    });
  };

  // -----------------------------
  // 저장
  // -----------------------------

  const saveChanges = async () => {
    let targetDate = selectedDate;

    try {
      for (const receipt of receipts) {
        const response = await fetch(
          `http://localhost:8000/receipts/${receipt.receiptId}`,
          {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              merchantName: receipt.merchantName,
              transactionDate: receipt.transactionDate,
              supplyAmount: receipt.supplyAmount,
              vat: receipt.vat,
              totalAmount: receipt.totalAmount,
              discountAmount: receipt.discountAmount || 0,
              paymentMethod: receipt.paymentMethod,
              categoryId: receipt.categoryId,

              items: receipt.items.map((item) => ({
                id: item.id,
                name: item.name,
                quantity: item.quantity === "" ? null : Number(item.quantity),
                unitPrice:
                  item.unitPrice === "" ? null : Number(item.unitPrice),
                amount: Number(item.amount),
                categoryId: item.categoryId,
              })),
            }),
          },
        );

        if (!response.ok) {
          throw new Error(
            `영수증 저장에 실패했습니다. receipt_id=${receipt.receiptId}`,
          );
        }

        // 저장한 영수증의 날짜로 이동
        targetDate = receipt.transactionDate.slice(0, 10);
      }

      // 해당 날짜로 화면 이동
      setSelectedDate(targetDate);

      // DB에서 최신 데이터 다시 조회
      await loadReceipts(targetDate, setReceipts);

      alert("저장되었습니다.");
    } catch (error) {
      console.error(error);
      alert("저장에 실패했습니다.");
    }
  };

  const totalAmount = receipts.reduce(
    (sum, receipt) => sum + (Number(receipt.totalAmount) || 0),
    0,
  );

  const deleteItem = (receiptId, itemId) => {
    setReceipts((current) =>
      current.map((receipt) => {
        if (receipt.receiptId !== receiptId) {
          return receipt;
        }

        return {
          ...receipt,
          items: receipt.items.filter((item) => item.id !== itemId),
        };
      }),
    );
  };

  const addItem = (receiptId, categoryId) => {
    setReceipts((current) =>
      current.map((receipt) => {
        if (receipt.receiptId !== receiptId) {
          return receipt;
        }

        return {
          ...receipt,
          items: [
            ...receipt.items,
            {
              isNew: true,
              name: "",
              quantity: 1,
              unitPrice: 0,
              amount: 0,
              categoryId,
            },
          ],
        };
      }),
    );

    setEditingItems((current) => ({
      ...current,
    }));
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <main className="mx-auto max-w-md px-4 py-6">
        {/* 제목 */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">장바구니</h1>

          {/* 날짜 이동 */}
          <div className="mb-6 mt-4 flex items-center justify-between">
            <button
              type="button"
              onClick={() => moveDate(-1)}
              className="px-3 py-2 text-gray-500"
            >
              ◀
            </button>

            <span className="font-semibold text-gray-900">{selectedDate}</span>

            <button
              type="button"
              onClick={() => moveDate(1)}
              className="px-3 py-2 text-gray-500"
            >
              ▶
            </button>
          </div>

          <p className="text-lg font-semibold text-gray-700">
            {formatAmount(totalAmount)}원
          </p>
        </div>

        {/* 영수증 */}
        {buildCategories(receipts).map((category) => {
          const categoryKey = category.name;
          const isOpen = openCategories.includes(categoryKey);

          return (
            <div
              key={category.categoryId}
              className="mb-6 overflow-hidden rounded-xl bg-white shadow-sm"
            >
              {/* 카테고리 헤더 */}
              <div className="flex items-center justify-between px-4 py-4">
                <button
                  type="button"
                  onClick={() => toggleCategory(categoryKey)}
                  className="flex items-center gap-2"
                >
                  <span className="text-gray-500">{isOpen ? "▼" : "▶"}</span>
                </button>

                <span className="flex-1 px-2 text-sm font-semibold text-gray-900">
                  {category.name}
                </span>

                <span className="ml-3 font-semibold text-gray-700">
                  {formatAmount(category.amount)}원
                </span>
              </div>

              {/* 카테고리 내용 */}
              <div
                className={`overflow-hidden transition-all duration-300 ease-in-out ${
                  isOpen ? "max-h-[5000px] opacity-100" : "max-h-0 opacity-0"
                }`}
              >
                <div className="border-t border-gray-100 px-4 pb-3">
                  {/* 같은 카테고리의 영수증들 */}
                  {category.receipts.map((receipt) => (
                    <div
                      key={receipt.receiptId}
                      className="border-b border-gray-100 last:border-b-0"
                    >
                      {/* 가게명 */}
                      <div className="border-b border-gray-100 py-3">
                        {!editingMerchants[receipt.receiptId] ? (
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-400">
                              가게명
                            </span>

                            <p className="text-sm text-gray-700">
                              {receipt.merchantName}
                            </p>

                            <button
                              type="button"
                              onClick={() =>
                                toggleMerchantEditing(receipt.receiptId)
                              }
                              className="text-xs text-gray-400"
                            >
                              ✎ 수정
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <span className="shrink-0 text-xs text-gray-400">
                              가게명
                            </span>

                            <input
                              type="text"
                              value={receipt.merchantName || ""}
                              onChange={(e) =>
                                changeMerchantName(
                                  receipt.receiptId,
                                  e.target.value,
                                )
                              }
                              className="min-w-0 flex-1 rounded-lg border border-gray-300 px-2 py-2 text-sm"
                            />

                            <button
                              type="button"
                              onClick={() =>
                                toggleMerchantEditing(receipt.receiptId)
                              }
                              className="shrink-0 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-600"
                            >
                              ✓
                            </button>
                          </div>
                        )}
                      </div>

                      {/* 품목 */}
                      {receipt.items.length === 0 ? (
                        <div className="py-4">
                          <p className="text-sm text-gray-400">
                            상품이 없습니다.
                          </p>
                        </div>
                      ) : (
                        receipt.items.map((item) => {
                          const isEditing = editingItems[item.id];
                          const isCategoryEditing =
                            editingItemCategories[item.id];

                          const itemCategory = categoryOptions.find(
                            (option) => option.id === item.categoryId,
                          );

                          return (
                            <div
                              key={item.id}
                              className="border-b border-gray-100 py-3 last:border-b-0"
                            >
                              {/* 품목명 */}
                              {!isEditing ? (
                                <div className="flex items-center gap-2">
                                  <span className="truncate text-sm text-gray-700">
                                    {item.name}
                                  </span>

                                  <button
                                    type="button"
                                    onClick={() => toggleItemEditing(item.id)}
                                    className="shrink-0 text-xs text-gray-400"
                                  >
                                    ✎ 수정
                                  </button>
                                </div>
                              ) : (
                                <div className="flex items-center gap-2">
                                  <input
                                    type="text"
                                    value={item.name || ""}
                                    onChange={(e) =>
                                      changeItem(
                                        receipt.receiptId,
                                        item.id,
                                        "name",
                                        e.target.value,
                                      )
                                    }
                                    className="min-w-0 flex-1 rounded-lg border border-gray-300 px-2 py-2 text-sm"
                                  />

                                  <button
                                    type="button"
                                    onClick={() => toggleItemEditing(item.id)}
                                    className="shrink-0 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-600"
                                  >
                                    ✓
                                  </button>
                                </div>
                              )}

                              {/* 가게명 */}
                              <div className="mt-1 text-xs text-gray-400">
                                {receipt.merchantName}
                              </div>

                              {/* 수량 / 단가 */}
                              <div className="mt-2 flex items-center gap-3 text-xs text-gray-400">
                                <div className="flex items-center gap-1">
                                  <span>수량 :</span>

                                  {isEditing ? (
                                    <input
                                      type="number"
                                      min="1"
                                      value={item.quantity ?? ""}
                                      onChange={(e) =>
                                        changeItem(
                                          receipt.receiptId,
                                          item.id,
                                          "quantity",
                                          e.target.value,
                                        )
                                      }
                                      className="w-12 rounded border border-gray-300 px-1 py-1 text-center text-xs text-gray-700"
                                    />
                                  ) : (
                                    <span>{item.quantity ?? "-"}</span>
                                  )}
                                </div>

                                <div className="flex items-center gap-1">
                                  <span>단가 :</span>

                                  {isEditing ? (
                                    <input
                                      type="number"
                                      value={item.unitPrice ?? ""}
                                      onChange={(e) =>
                                        changeItem(
                                          receipt.receiptId,
                                          item.id,
                                          "unitPrice",
                                          e.target.value,
                                        )
                                      }
                                      className="w-20 rounded border border-gray-300 px-1 py-1 text-right text-xs text-gray-700"
                                    />
                                  ) : (
                                    <span>
                                      {item.unitPrice != null
                                        ? `${formatAmount(item.unitPrice)}원`
                                        : "-"}
                                    </span>
                                  )}
                                </div>
                              </div>

                              {/* 카테고리 */}
                              <div className="mt-2 flex items-center gap-2">
                                <span className="text-xs text-gray-400">
                                  카테고리
                                </span>

                                {!isCategoryEditing ? (
                                  <>
                                    <span className="text-xs text-gray-600">
                                      {itemCategory?.name || "기타"}
                                    </span>

                                    <button
                                      type="button"
                                      onClick={() =>
                                        toggleItemCategoryEditing(item.id)
                                      }
                                      className="text-xs text-gray-400"
                                    >
                                      ✎ 수정
                                    </button>
                                  </>
                                ) : (
                                  <>
                                    <select
                                      value={item.categoryId ?? ""}
                                      onChange={(e) => {
                                        changeItemCategory(
                                          receipt.receiptId,
                                          item.id,
                                          Number(e.target.value),
                                        );

                                        setEditingItemCategories((current) => ({
                                          ...current,
                                          [item.id]: false,
                                        }));
                                      }}
                                      className="rounded-lg border border-gray-300 px-2 py-1 text-xs text-gray-600"
                                    >
                                      {categoryOptions.map((option) => (
                                        <option
                                          key={option.id}
                                          value={option.id}
                                        >
                                          {option.name}
                                        </option>
                                      ))}
                                    </select>

                                    <button
                                      type="button"
                                      onClick={() =>
                                        toggleItemCategoryEditing(item.id)
                                      }
                                      className="rounded-lg border border-gray-200 px-2 py-1 text-xs text-gray-600"
                                    >
                                      ✓
                                    </button>
                                  </>
                                )}
                              </div>

                              {/* 금액 */}
                              <div className="mt-2 text-right text-sm font-medium text-gray-900">
                                {formatAmount(item.amount)}원
                              </div>

                              {/* 삭제 */}
                              <div className="mt-2 text-right">
                                <button
                                  type="button"
                                  onClick={() =>
                                    deleteItem(receipt.receiptId, item.id)
                                  }
                                  className="text-xs text-gray-400"
                                >
                                  ✕ 삭제
                                </button>
                              </div>
                            </div>
                          );
                        })
                      )}

                      {/* 아이템 추가 */}
                      <div className="border-t border-gray-100 py-2">
                        <button
                          type="button"
                          onClick={() =>
                            addItem(receipt.receiptId, category.categoryId)
                          }
                          className="w-full py-2 text-sm text-gray-500"
                        >
                          + 아이템 추가
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}

        {/* 저장 */}
        <button
          type="button"
          onClick={saveChanges}
          className="mt-6 w-full rounded-xl bg-black px-4 py-4 text-center font-semibold text-white"
        >
          저장
        </button>
      </main>
    </div>
  );
}

export default App;
