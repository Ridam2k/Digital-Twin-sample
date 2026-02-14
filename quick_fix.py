# run this in a quick script or Python REPL

from qdrant_client import QdrantClient
from qdrant_client import models
from qdrant_client.models import PayloadSchemaType
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

client.create_payload_index(
    collection_name=COLLECTION_NAME,
    field_name="personality_ns",
    field_schema=PayloadSchemaType.KEYWORD,
)

print("Index created.")