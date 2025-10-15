import os
from dotenv import load_dotenv

load_dotenv()

WEAVIATE_URL       = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_COLLECTION= os.getenv("WEAVIATE_COLLECTION", "DocChunk")
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
EMBED_MODEL        = os.getenv("EMBED_MODEL", "text-embedding-3-small")
GEN_MODEL          = os.getenv("GEN_MODEL", "gpt-4o-mini")
TOP_K              = int(os.getenv("TOP_K", "5"))
