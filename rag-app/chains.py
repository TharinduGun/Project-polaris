from typing import List, Dict, Any
import weaviate
from weaviate.classes.init import AdditionalConfig
from weaviate.collections import Collection
from weaviate.embedded import EmbeddedOptions  # not used; just in case
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from settings import *

# OpenAI client
oai = OpenAI(api_key=OPENAI_API_KEY)

def embed_query(q: str) -> List[float]:
    """Create the query vector using the *same* model as indexing."""
    emb = oai.embeddings.create(model=EMBED_MODEL, input=q)
    return emb.data[0].embedding

def connect_weaviate() -> Collection:
    client = weaviate.WeaviateClient(
        url=WEAVIATE_URL,
        additional_config=AdditionalConfig(timeout=(10, 60))  # (connect, read)
    )
    return client.collections.get(WEAVIATE_COLLECTION)

def retrieve(query: str, k: int = TOP_K) -> List[Dict[str, Any]]:
    qvec = embed_query(query)
    coll = connect_weaviate()
    # return props you stored + pageContent (in our case "text")
    res = coll.query.near_vector(
        near_vector=qvec,
        limit=k,
        return_metadata=["distance"],
        return_properties=["text", "doc_id", "chunk_id", "source", "page", "mime_type"]
    )
    # v4 client returns .objects with .properties
    docs = []
    for obj in res.objects:
        p = obj.properties or {}
        docs.append({
            "text": p.get("text") or p.get("pageContent") or "",
            "doc_id": p.get("doc_id"),
            "chunk_id": p.get("chunk_id"),
            "source": p.get("source"),
            "page": p.get("page"),
            "mime_type": p.get("mime_type"),
            "score": obj.metadata.get("distance") if obj.metadata else None
        })
    return docs

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def generate_answer(query: str, contexts: List[Dict[str, Any]]) -> str:
    """Simple RAG: stuff top-k chunks and ask the model to answer with citations."""
    context_str = "\n\n---\n\n".join(
        f"[{i+1}] (doc:{c.get('doc_id')} p:{c.get('page')})\n{c['text']}"
        for i, c in enumerate(contexts)
    )
    prompt = f"""You are a helpful assistant. Use only the CONTEXT to answer.

QUESTION:
{query}

CONTEXT:
{context_str}

If the answer isn't in the context, say you don't know. End with short bullet citations like [1], [2]."""

    resp = oai.chat.completions.create(
        model=GEN_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()

def rag_answer(query: str, k: int = TOP_K) -> Dict[str, Any]:
    ctx = retrieve(query, k=k)
    answer = generate_answer(query, ctx)
    return {"answer": answer, "contexts": ctx}
