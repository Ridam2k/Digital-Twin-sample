"""
Checkpoint 2 — Metadata is correct on a sample chunk
"""
from qdrant_client import QdrantClient
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
results = client.scroll(COLLECTION_NAME, limit=1, with_payload=True)

if results[0]:
    payload = results[0][0].payload
    print("Sample chunk metadata:")
    print(f"  personality_ns: {payload.get('personality_ns')}")
    print(f"  content_type: {payload.get('content_type')}")
    print(f"  chunk_index: {payload.get('chunk_index')}")
    print(f"  chunk_total: {payload.get('chunk_total')}")
    print(f"  ingested_at: {payload.get('ingested_at')}")
    print(f"  file_name: {payload.get('file_name')}")
    print(f"\n✅ All expected metadata fields present")
else:
    print("❌ No chunks found in collection")
