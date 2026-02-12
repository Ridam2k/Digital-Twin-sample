from ingest.gdrive_reader import get_gdrive_reader
from ingest.chunker import tag_and_chunk
from ingest.embedder import upsert_nodes
from config import TECHNICAL_FOLDER_ID, NONTECHNICAL_FOLDER_ID


def ingest_folder(folder_id: str, personality_ns: str, content_type: str) -> None:
    print(f"\n[ingest] Starting: namespace='{personality_ns}', content_type='{content_type}'")
    reader = get_gdrive_reader(folder_id)
    docs = reader.load_data()
    print(f"[ingest] Loaded {len(docs)} documents.")

    nodes = tag_and_chunk(docs, personality_ns, content_type)
    print(f"[ingest] Produced {len(nodes)} chunks.")

    upsert_nodes(nodes)


if __name__ == "__main__":
    ingest_folder(TECHNICAL_FOLDER_ID,    "technical",    "project_writeup")
    ingest_folder(NONTECHNICAL_FOLDER_ID, "nontechnical", "notes")
    print("\n[ingest] Day 1 ingestion complete.")
