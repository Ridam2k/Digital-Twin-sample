"""
Checkpoint 1 — Collection exists with vectors
"""
from qdrant_client import QdrantClient
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
info = client.get_collection(COLLECTION_NAME)
print(info)
print(f"\n✅ Collection '{COLLECTION_NAME}' exists with {info.indexed_vectors_count} vectors and {info.points_count} chunks")
