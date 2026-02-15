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


def tag_and_chunk(
    documents: list[Document],
    personality_ns: str,
    content_type: str,
) -> list:
    """
    Chunks documents and tags every node with namespace + content_type metadata.
    GoogleDriveReader already attaches: file_id, file_name, source_url, mime_type.
    """
    parser = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    nodes = parser.get_nodes_from_documents(documents)
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

    return nodes
