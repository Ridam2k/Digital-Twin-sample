# Metadata schema per chunk:
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
    nodes = parser.get_nodes_from_documents(valid_docs, show_progress=True)
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

        # Ensure doc_title is set for Google Drive docs (metadata uses "file path")
        file_path = node.metadata.get("file path") or node.metadata.get("file_path") #On revisting -> file_path
        file_name = node.metadata.get("file name") or node.metadata.get("file_name")
        if file_path:
            node.metadata["doc_title"] = file_path.split("/")[-1]
        elif not node.metadata.get("doc_title") and file_name:
            node.metadata["doc_title"] = file_name
        
        # Build a unique file_id for deterministic chunk UUIDs.
        # Google Drive docs have "file id"; GitHub docs have "doc_id".
        file_id = (
            node.metadata.get("file id")
            or node.metadata.get("doc_id")
            or node.metadata.get("file_name")
            or "unknown"
        )

        raw = f"{file_id}|{personality_ns}|{content_type}|{i}"
        
        # UUID format for Qdrant compatibility
        hash_bytes = hashlib.sha1(raw.encode("utf-8")).digest()[:16]
        node.node_id = str(uuid.UUID(bytes=hash_bytes)) 
        # set as node ID -> determinstic and idempotent IDs - allows me to upsert reliably, can keep references stable

    return nodes
