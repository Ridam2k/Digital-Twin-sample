import openai
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, PointIdsList,
)
from config import (
    QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME,
    EMBEDDING_MODEL, OPENAI_API_KEY, EMBEDDING_DIM
)
import time
from qdrant_client.http.exceptions import ResponseHandlingException
from qdrant_client.models import PayloadSchemaType

# ── OpenAI client (used only for embeddings) ────────────────────────
_oai = openai.OpenAI(api_key=OPENAI_API_KEY)

EMBED_BATCH_SIZE = 128  # OpenAI allows up to 2048, but 128 is safe for memory


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def ensure_collection(client: QdrantClient) -> None:
    existing = [c.name for c in client.get_collections().collections]
    
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="personality_ns",
            field_schema=PayloadSchemaType.KEYWORD,
        )

        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="content_type",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        print(f"[embedder] Created collection: {COLLECTION_NAME}")


# ── Embedding helper ────────────────────────────────────────────────
def _embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Batch-embed via the OpenAI API directly.
    Chunks into EMBED_BATCH_SIZE to stay within request limits.
    """
    all_vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]
        resp = _oai.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        # resp.data is already sorted by index, but sort defensively
        sorted_data = sorted(resp.data, key=lambda d: d.index)
        all_vectors.extend([d.embedding for d in sorted_data])
    return all_vectors




def _upsert_with_retry(client: QdrantClient, points: list, retries: int = 3) -> None:
    for attempt in range(retries):
        try:
            # client.upsert(collection_name=COLLECTION_NAME, points=points)
            _upsert_with_retry(client, points)
            return
        except ResponseHandlingException as e:
            if attempt < retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s
                print(f"[embedder] Upsert failed ({e}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


# ── Upsert ──────────────────────────────────────────────────────────
def upsert_nodes(client: QdrantClient, nodes: list) -> None:
    """
    Embed and upsert LlamaIndex TextNode objects directly into Qdrant.

    Payload schema written here is the *single source of truth* and
    must stay aligned with what retriever.py reads:
        text, doc_title, source_url, personality_ns, content_type,
        chunk_index, chunk_total, ingested_at, file_name
    """
    if not nodes:
        return

    # Filter out nodes with empty/whitespace-only content
    valid_nodes = [
        node for node in nodes
        if node.get_content() and node.get_content().strip()
    ]

    if not valid_nodes:
        print("[embedder] Skipped batch - all nodes were empty.")
        return

    if len(valid_nodes) < len(nodes):
        print(f"[embedder] Filtered out {len(nodes) - len(valid_nodes)} empty nodes.")

    # client = get_qdrant_client()
    ensure_collection(client)

    texts = [node.get_content() for node in valid_nodes]
    vectors = _embed_texts(texts)

    def _extract_doc_title(meta: dict) -> str:
        for key in ("file path", "file_path"):
            val = meta.get(key)
            if val:
                return val.split("/")[-1]
        if meta.get("doc_title"):
            return meta["doc_title"]
        for key in ("file name", "file_name"):
            val = meta.get(key)
            if val:
                return val
        return "Unknown"

    def _extract_file_name(meta: dict, doc_title: str) -> str:
        for key in ("file name", "file_name"):
            val = meta.get(key)
            if val:
                return val
        for key in ("file path", "file_path"):
            val = meta.get(key)
            if val:
                return val.split("/")[-1]
        return "" if doc_title == "Unknown" else doc_title

    points = []
    for node, vector in zip(valid_nodes, vectors):
        meta = node.metadata
        doc_title = _extract_doc_title(meta)
        file_name = _extract_file_name(meta, doc_title)
        points.append(
            PointStruct(
                # Use the node_id that SentenceSplitter already assigned.
                # main_ingest.py records these IDs in the hash store for
                # incremental deletion, so they must match.
                id=node.node_id,
                vector=vector,
                payload={
                    # ── Core retrieval fields ──
                    "text":           node.get_content(),
                    "doc_title":      doc_title,
                    "source_url":     meta.get("source_url", ""),
                    "personality_ns": meta["personality_ns"],
                    "content_type":   meta["content_type"],
                    # ── Supplementary fields ──
                    "chunk_index":    meta.get("chunk_index", 0),
                    "chunk_total":    meta.get("chunk_total", 0),
                    "ingested_at":    meta.get("ingested_at", ""),
                    "file_name":      file_name,
                    "file_path":      meta.get("file_path") or meta.get("file path", ""),
                },
            )
        )

    # Qdrant client handles batching internally for large point lists
    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"[embedder] Upserted {len(points)} chunks.")


# ── Verify ──────────────────────────────────────────────────────────
def verify_points_exist(client: QdrantClient, point_ids: list[str]) -> tuple[bool, list[str]]:
    """
    Verify that all point IDs exist in Qdrant.

    Returns:
        (all_exist: bool, missing_ids: list[str])
    """
    if not point_ids:
        return True, []

    # client = get_qdrant_client()

    try:
        # Retrieve points by ID (doesn't fail if some missing)
        result = client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=point_ids,
            with_payload=False,
            with_vectors=False,
        )

        found_ids = {str(point.id) for point in result}
        requested_ids = set(point_ids)
        missing_ids = list(requested_ids - found_ids)

        return len(missing_ids) == 0, missing_ids
    except Exception as e:
        print(f"[embedder] Error verifying points: {e}")
        return False, point_ids


# ── Delete (unchanged) ──────────────────────────────────────────────
def delete_points_by_ids(client: QdrantClient, point_ids: list[str]) -> None:
    """Delete specific Qdrant points by their IDs (used when a file changes)."""
    if not point_ids:
        return
    # client = get_qdrant_client()
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=PointIdsList(points=point_ids),
    )
    print(f"[embedder] Deleted {len(point_ids)} stale chunks.")
