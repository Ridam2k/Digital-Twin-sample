# run this in a quick script or Python REPL

from qdrant_client import QdrantClient
from qdrant_client import models
from qdrant_client.models import PayloadSchemaType
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME


from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# client.create_payload_index(
#     collection_name=COLLECTION_NAME,
#     field_name="personality_ns",
#     field_schema=PayloadSchemaType.KEYWORD,
# )

# client.create_payload_index(
#     collection_name=COLLECTION_NAME,
#     field_name="content_type",
#     field_schema=PayloadSchemaType.KEYWORD,
# )

# results, _ = client.scroll(
#     collection_name=COLLECTION_NAME,
#     scroll_filter=Filter(
#         must=[
#             FieldCondition(key="personality_ns", match=MatchValue(value="technical")),
#             FieldCondition(key="content_type",   match=MatchValue(value="documentation")),
#         ]
#     ),
#     limit=1000,
#     with_payload=["doc_title"],
#     with_vectors=False,
# )

# titles = sorted({p.payload["doc_title"] for p in results})
# for t in titles:
#     print(t)

# client.create_payload_index(
#     collection_name=COLLECTION_NAME,
#     field_name="file_name",
#     field_schema=PayloadSchemaType.KEYWORD,
# )

# client.create_payload_index(
#     collection_name=COLLECTION_NAME,
#     field_name="doc_title",
#     field_schema=PayloadSchemaType.KEYWORD,
# )
from qdrant_client import QdrantClient, models
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME

## Delete by doc title
# TARGET_DOC_TITLE = "Work Experience: Systems Engineering and Distributed Systems"

# client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# # 1. Count matching points
# match_filter = models.Filter(
#     must=[
#         models.FieldCondition(
#             key="doc_title",
#             match=models.MatchValue(value=TARGET_DOC_TITLE),
#         )
#     ]
# )

# results = client.scroll(
#     collection_name=COLLECTION_NAME,
#     scroll_filter=match_filter,
#     limit=100,
#     with_payload=True,
# )

# points = results[0]
# print(f"Found {len(points)} chunks with doc_title = '{TARGET_DOC_TITLE}'")

# for p in points:
#     print(f"  - ID: {p.id} | chunk_index: {p.payload.get('chunk_index')} | ns: {p.payload.get('personality_ns')}")

# if not points:
#     print("Nothing to delete.")
#     exit(0)

# # 2. Delete all matching points by filter
# client.delete(
#     collection_name=COLLECTION_NAME,
#     points_selector=models.FilterSelector(filter=match_filter),
# )

# print(f"\nDeleted {len(points)} points from collection '{COLLECTION_NAME}'.")

client.close()