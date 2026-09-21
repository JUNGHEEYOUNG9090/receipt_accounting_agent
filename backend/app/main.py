from fastapi import FastAPI

from app.graph.receipt_graph import receipt_graph

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Receipt Accounting Agent"}


@app.get("/test-agent")
def test_agent():
    result = receipt_graph.invoke({
        "message": "영수증"
    })

    return result