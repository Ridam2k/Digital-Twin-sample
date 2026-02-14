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

TOP_K                 = 5
OUT_OF_SCOPE_THRESHOLD = 0.3
AMBIGUOUS_K_PER_NS = TOP_K

namespaces = ['technical', 'nontechnical']


@dataclass
class RetrievedChunk:
    text:        str
    score:       float
    doc_title:   str
    source_url:  str
    chunk_index: int
    personality_ns: str
    content_type:   str
    doc_id:      str  # Added for evaluation purposes



def _query_namespace(
    client:     QdrantClient,
    query_vec:  list[float],
    namespace:  str,
    limit:      int,
) -> list[RetrievedChunk]:
    """
    Run a single filtered Qdrant query for one namespace.
    Extracted so both retrieve() and the ambiguous branch can reuse it.
    """
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
        limit=limit,
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
            doc_id         = p.get("file id", ""),  # GoogleDriveReader uses "file id"
        ))
    return chunks


def retrieve(
    query:     str,
    namespace: str,                    # "technical" | "nontechnical" | "ambiguous"
) -> tuple[list[RetrievedChunk], bool]:
    """
    Retrieve top-k chunks from Qdrant.

    - For a definite namespace ("technical" / "nontechnical"):
        queries that namespace only, same behaviour as before.

    - For "ambiguous":
        queries ALL namespaces in `namespaces`, merges by score desc,
        returns the global top-K. The caller must pass `namespaces`.

    Returns:
        chunks       – list of RetrievedChunk, sorted by score desc
        out_of_scope – True if best score < OUT_OF_SCOPE_THRESHOLD
    """
    client      = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    embed_model = OpenAIEmbedding(model=EMBEDDING_MODEL)
    query_vec   = embed_model.get_text_embedding(query)

    if namespace == "ambiguous":
        if not namespaces:
            raise ValueError(
                "namespace='ambiguous' requires the `namespaces` list "
                "(e.g. ['technical', 'nontechnical'])."
            )
        # Query each namespace independently, then merge and re-rank.
        all_chunks: list[RetrievedChunk] = []
        for ns in namespaces:
            all_chunks.extend(
                _query_namespace(client, query_vec, ns, limit=AMBIGUOUS_K_PER_NS)
            )
        # Global re-rank by score; ties broken by namespace order in `namespaces`.
        chunks = sorted(all_chunks, key=lambda c: c.score, reverse=True)[:TOP_K]
    else:
        chunks = _query_namespace(client, query_vec, namespace, limit=TOP_K)

    out_of_scope = len(chunks) == 0 or chunks[0].score < OUT_OF_SCOPE_THRESHOLD
    return chunks, out_of_scope