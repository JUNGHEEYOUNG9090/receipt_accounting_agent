from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class ReceiptState(TypedDict):
    message: str


def process_receipt(state: ReceiptState):
    return {
        "message": f"{state['message']} → 영수증 처리 완료"
    }


builder = StateGraph(ReceiptState)

builder.add_node("process_receipt", process_receipt)

builder.add_edge(START, "process_receipt")
builder.add_edge("process_receipt", END)

receipt_graph = builder.compile()