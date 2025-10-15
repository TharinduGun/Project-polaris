from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from chains import rag_answer, retrieve

app = FastAPI(title="Weaviate RAG API", version="1.0.0")

class QueryIn(BaseModel):
    query: str
    top_k: Optional[int] = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/search")
def search(body: QueryIn):
    ctx = retrieve(body.query, body.top_k or 5)
    return {"results": ctx}

@app.post("/ask")
def ask(body: QueryIn):
    res = rag_answer(body.query, body.top_k or 5)
    return res
