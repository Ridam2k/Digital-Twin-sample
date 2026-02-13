from dataclasses import dataclass
from qdrant_client import QdrantClient
from qdrant_client.models import models
from llama_index.embeddings.openai import OpenAIEmbedding
from config import (
    QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME,
    EMBEDDING_MODEL, OPENAI_API_KEY,
)
import os

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

TOP_K                 = 6
OUT_OF_SCOPE_THRESHOLD = 0.3


@dataclass
class RetrievedChunk:
    text:        str
    score:       float
    doc_title:   str
    source_url:  str
    chunk_index: int
    personality_ns: str
    content_type:   str


def retrieve(query: str, namespace: str) -> tuple[list[RetrievedChunk], bool]:
    """
    Retrieve top-k chunks from the given namespace.

    Returns:
        chunks      — list of RetrievedChunk, sorted by score desc
        out_of_scope — True if best score < OUT_OF_SCOPE_THRESHOLD
    """
    client      = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    embed_model = OpenAIEmbedding(model=EMBEDDING_MODEL)

    query_vec = embed_model.get_text_embedding(query)

    results = client.query_points(
    collection_name=COLLECTION_NAME,
    query=query_vec,
    query_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="personality_ns",
                match=models.MatchValue(value=namespace),
            )
            ]
        ),
        limit=TOP_K,
        with_payload=True,
    ).points
    

    chunks = []
    for r in results:
        p = r.payload
        chunks.append(RetrievedChunk(
            text           = p.get("_node_content", p.get("text", "")),
            score          = r.score,
            doc_title      = p.get("doc_title",   p.get("file_name", "Unknown")),
            source_url     = p.get("source_url",  ""),
            chunk_index    = p.get("chunk_index", 0),
            personality_ns = p.get("personality_ns", namespace),
            content_type   = p.get("content_type", ""),
        ))

    out_of_scope = len(chunks) == 0 or chunks[0].score < OUT_OF_SCOPE_THRESHOLD
    return chunks, out_of_scope