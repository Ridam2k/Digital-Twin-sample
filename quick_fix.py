# run this in a quick script or Python REPL

from qdrant_client import QdrantClient
from qdrant_client import models
from qdrant_client.models import PayloadSchemaType
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# client.create_payload_index(
#     collection_name=COLLECTION_NAME,
#     field_name="personality_ns",
#     field_schema=PayloadSchemaType.KEYWORD,
# )

# print("Index created.")
try:
    # Use a MatchAll filter to select all points for deletion
    delete_result = client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.MatchAllCondition() # This condition matches all points
                ]
            )
        ),
        wait=True, # Wait for the operation to complete
    )
    print(f"Deletion operation completed with status: {delete_result.status}")
except Exception as e:
    print(f"Error during point deletion: {e}")
