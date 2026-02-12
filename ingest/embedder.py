# ingest/embedder.py
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME, EMBEDDING_MODEL, OPENAI_API_KEY

def get_qdrant_client():
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

def ensure_collection(client: QdrantClient):
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )
        print(f"Created collection: {COLLECTION_NAME}")

def upsert_nodes(nodes: list):
    client = get_qdrant_client()
    ensure_collection(client)

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    embed_model = OpenAIEmbedding(model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY)

    VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True
    )
    print(f"Upserted {len(nodes)} chunks.")

def delete_points_by_ids(point_ids: list[str]) -> None:
    """Delete specific Qdrant points by their IDs (used when a file changes)."""
    if not point_ids:
        return
    client = get_qdrant_client()
    from qdrant_client.models import PointIdsList
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=PointIdsList(points=point_ids),
    )
    print(f"[embedder] Deleted {len(point_ids)} stale chunks.")