# Expected metadata schema per chunk:
# {
#   "doc_id", "doc_title", "source_type", "source_url",
#   "personality_ns", "content_type", "last_modified",
#   "chunk_index", "chunk_total", "ingested_at"
# }

from datetime import datetime, timezone
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from config import CHUNK_SIZE, CHUNK_OVERLAP
import hashlib
import uuid


def tag_and_chunk(
    documents: list[Document],
    personality_ns: str,
    content_type: str,
) -> list:
    """
    Chunks documents and tags every node with namespace + content_type metadata.
    GoogleDriveReader already attaches: file_id, file_name, source_url, mime_type.
    """
    # Filter empty documents before chunking
    valid_docs = []
    for doc in documents:
        content = doc.get_content()
        if not content or not content.strip():
            print(f"[chunker] Warning: Empty document detected - {doc.metadata.get('file_name', 'unknown')}")
        else:
            valid_docs.append(doc)

    if not valid_docs:
        return []

    parser = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    nodes = parser.get_nodes_from_documents(valid_docs)
    chunk_total = len(nodes)
    ingested_at = datetime.now(timezone.utc).isoformat()

    for i, node in enumerate(nodes):
        node.metadata.update(
            {
                "personality_ns": personality_ns,
                "content_type":   content_type,
                "chunk_index":    i,
                "chunk_total":    chunk_total,
                "ingested_at":    ingested_at,
            }
        )
        # ✅ Deterministic ID
        file_id = None
        # GoogleDriveReader uses "file id" key in metadata (you already read it in main_ingest) :contentReference[oaicite:10]{index=10}
        if "file id" in node.metadata:
            file_id = node.metadata["file id"]
        else:
            # fall back to file_name to avoid crashing if metadata missing
            file_id = node.metadata.get("file_name", "unknown")

        raw = f"{file_id}|{personality_ns}|{content_type}|{i}"
        # Convert SHA-1 hash to UUID format for Qdrant compatibility
        hash_bytes = hashlib.sha1(raw.encode("utf-8")).digest()[:16]
        node.node_id = str(uuid.UUID(bytes=hash_bytes))

    return nodes
