import json
import datetime as dt
from pathlib import Path

from qdrant_client import QdrantClient

from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME

OUTPUT_PATH = Path("data/doc_titles.json")
SCROLL_LIMIT = 1000


def fetch_unique_doc_titles(client: QdrantClient) -> list[str]:
    titles: set[str] = set()
    offset = None

    while True:
        points, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=SCROLL_LIMIT,
            with_payload=True,
            with_vectors=False,
            offset=offset,
        )
        if not points:
            break

        for p in points:
            payload = p.payload or {}
            title = (payload.get("doc_title") or payload.get("file_name") or "").strip()
            if title:
                titles.add(title)

        if next_offset is None:
            break
        offset = next_offset

    return sorted(titles)


def main() -> None:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    titles = fetch_unique_doc_titles(client)

    payload = {
        "collection_name": COLLECTION_NAME,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_unique_doc_titles": len(titles),
        "doc_titles": titles,
    }

    OUTPUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {len(titles)} unique doc_title values to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
