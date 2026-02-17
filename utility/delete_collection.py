from qdrant_client import QdrantClient
import sys
from pathlib import Path
from qdrant_client.models import Filter, FieldCondition, MatchValue, FilterSelector

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


### DELETE COLLECTION!
# client.delete_collection(collection_name=COLLECTION_NAME)


# DELETE BY CRITERIA!!
# delete_filter = Filter(
#     must=[
#         FieldCondition(key="personality_ns", match=MatchValue(value="technical")),
#         FieldCondition(key="content_type", match=MatchValue(value="code"))
#     ]
# )

# client.delete(
#     collection_name=COLLECTION_NAME,
#     points_selector= FilterSelector(filter=delete_filter)
#     )

# verification = client.count(
#     collection_name=COLLECTION_NAME,
#     count_filter=delete_filter,
#     exact=True # Ensures an accurate count rather than an estimate
# )

# print(f"Points remaining matching criteria: {verification.count}")
