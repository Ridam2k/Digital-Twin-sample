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

results, _ = client.scroll(
    collection_name=COLLECTION_NAME,
    scroll_filter=Filter(
        must=[
            FieldCondition(key="personality_ns", match=MatchValue(value="technical")),
            FieldCondition(key="content_type",   match=MatchValue(value="documentation")),
        ]
    ),
    limit=1000,
    with_payload=["doc_title"],
    with_vectors=False,
)

titles = sorted({p.payload["doc_title"] for p in results})
for t in titles:
    print(t)

client.close()