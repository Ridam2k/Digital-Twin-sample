from ingest.gdrive_reader import get_gdrive_reader
from ingest.chunker import tag_and_chunk
from ingest.embedder import upsert_nodes, delete_points_by_ids, verify_points_exist
from ingest.github_reader import fetch_repo_files, files_to_documents
from ingest.hash_store import (
    load_hash_store, save_hash_store,
    is_changed, record_file, get_old_point_ids,
)
from ingest.gdrive_hash_store import (
    load_gdrive_hash_store, save_gdrive_hash_store,
    is_gdrive_changed, record_gdrive_file, get_old_gdrive_point_ids,
)
from ingest.synthetic_reader import load_synthetic_document
from ingest.synthetic_hash_store import (
    load_synthetic_store, save_synthetic_store,
    is_synthetic_changed, record_synthetic_file, get_old_synthetic_point_ids,
)

from config import TECHNICAL_FOLDER_ID, NONTECHNICAL_FOLDER_ID, GITHUB_REPOS, SOURCE_TYPES, SOURCE_TYPE_MIME_MAPPING, QDRANT_URL, QDRANT_API_KEY
from qdrant_client import QdrantClient
import os
import hashlib
from pathlib import Path

FORCE_REINDEX = os.getenv("FORCE_REINDEX", "0") == "1"
RESUME_MODE = os.getenv("RESUME_MODE", "0") == "1"


client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=30,
    http2=False,
)
    
    
def ingest_folder(folder_id: str, personality_ns: str, content_type: str) -> None:
    print(f"\n[ingest] Starting: namespace='{personality_ns}', content_type='{content_type}'")

    # Resolve MIME types from config
    mime_types = [SOURCE_TYPE_MIME_MAPPING[st] for st in SOURCE_TYPES if st in SOURCE_TYPE_MIME_MAPPING]

    reader = get_gdrive_reader(folder_id)
    docs = reader.load_data(mime_types=mime_types)  # filter at API level
    print(f"[gdrive] Loaded {len(docs)} documents from Google Drive.")

    store = load_gdrive_hash_store()
    
    new_count = 0
    changed_count = 0
    skipped_count = 0


    for doc in docs:
        file_id = doc.metadata.get("file id")
        modified_time = doc.metadata.get("modified at")

        #Skip files without proper metadata
        if not file_id or not modified_time:
            print(f"[gdrive] Warning: Skipping document without metadata: {doc.metadata.get('file_name', 'Unknown')}")
            continue

        # ✅ RESUME_MODE: Verify points exist in Qdrant before skipping
        if RESUME_MODE and file_id in store:
            old_ids = get_old_gdrive_point_ids(store, file_id)
            if old_ids:
                all_exist, missing_ids = verify_points_exist(client, old_ids)
                if all_exist:
                    print(f"[resume] ✓ Verified {len(old_ids)} points in Qdrant, skipping {file_id}")
                    skipped_count += 1
                    continue
                else:
                    print(f"[resume] ✗ Missing {len(missing_ids)} points for {file_id}, re-processing")
                    # Fall through to re-process
            else:
                print(f"[resume] Warning: {file_id} in store but has no point IDs, re-processing")
                # Fall through to re-process

        # ✅ Force mode: treat everything as changed
        changed = FORCE_REINDEX or is_gdrive_changed(store, file_id, modified_time)
        if not changed:
            skipped_count += 1
            continue

        # ✅ Always delete previous points if they exist in store
        old_ids = get_old_gdrive_point_ids(store, file_id)  
        if old_ids:
            delete_points_by_ids(client, old_ids)  
            changed_count += 1
        else:
            new_count += 1

        nodes = tag_and_chunk([doc], personality_ns, content_type)  
        upsert_nodes(client,nodes)  # 

        new_ids = [node.node_id for node in nodes]
        record_gdrive_file(store, file_id, modified_time, new_ids)
    
    save_gdrive_hash_store(store)
    print(f"[gdrive] {personality_ns} — new: {new_count}, updated: {changed_count}, skipped (unchanged): {skipped_count}")   
        

def ingest_github(repos: list[str] = None) -> None:
    """
    Ingest GitHub repos with hash-based change detection.
    Only files whose git SHA changed since last run are re-embedded.
    """
    if repos is None:
        repos = GITHUB_REPOS

    store = load_hash_store()

    # Define code file extensions
    CODE_EXTENSIONS = {".py", ".js", ".jsx", ".css", ".html", ".ipynb"}

    for repo_name in repos:
        print(f"\n[github] Ingesting repo: {repo_name}")
        files = fetch_repo_files(repo_name)

        new_count     = 0
        changed_count = 0
        skipped_count = 0

        for f in files:
            key = f["file_key"]

            if not is_changed(store, key, f["git_sha"]):
                skipped_count += 1
                continue

            # Delete old chunks if this is an update (not a new file)
            old_ids = get_old_point_ids(store, key)
            if old_ids:
                delete_points_by_ids(client, old_ids)
                changed_count += 1
            else:
                new_count += 1

            # Detect content_type based on file extension
            ext = f["extension"]
            content_type = "code" if ext in CODE_EXTENSIONS else "documentation"

            # Ingest the (new or changed) file
            docs  = files_to_documents([f])
            nodes = tag_and_chunk(docs, personality_ns="technical", content_type=content_type)
            upsert_nodes(client, nodes)

            # Record new point IDs and SHA in hash store
            new_ids = [node.node_id for node in nodes]
            record_file(store, key, f["git_sha"], new_ids)

        save_hash_store(store)
        print(
            f"[github] {repo_name} — "
            f"new: {new_count}, updated: {changed_count}, skipped (unchanged): {skipped_count}"
        )


def compute_file_sha(file_path: Path) -> str:
    """
    Compute SHA256 hash of file contents.

    Args:
        file_path: Path to file

    Returns:
        str: Hex digest of SHA256 hash
    """
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def ingest_synthetic(sources_dir: str = "data/sources") -> None:
    """
    Ingest synthetic JSON documents with hash-based change detection.
    Only files whose SHA256 hash changed since last run are re-embedded.
    """
    print(f"\n[synthetic] Starting synthetic data ingestion")

    sources_path = Path(sources_dir)

    # Validate sources directory
    if not sources_path.exists():
        print(f"[synthetic] Warning: Sources directory does not exist: {sources_dir}")
        return

    # Scan for JSON files
    json_files = sorted(sources_path.glob("*.json"))

    if not json_files:
        print(f"[synthetic] Warning: No JSON files found in {sources_dir}")
        return

    print(f"[synthetic] Found {len(json_files)} JSON files")

    # Load hash store
    store = load_synthetic_store()

    new_count = 0
    changed_count = 0
    skipped_count = 0
    error_count = 0

    for json_file in json_files:
        file_name = json_file.name

        try:
            # Compute current file hash
            current_sha = compute_file_sha(json_file)

            # Check if changed (skip if not forced and not changed)
            changed = FORCE_REINDEX or is_synthetic_changed(store, file_name, current_sha)
            if not changed:
                skipped_count += 1
                continue

            # Delete old chunks if this is an update (not a new file)
            # old_ids = get_old_synthetic_point_ids(store, file_name)
            # if old_ids:
            #     delete_points_by_ids(client, old_ids)
            #     changed_count += 1
            # else:
            new_count += 1

            # Load document
            doc = load_synthetic_document(json_file)

            # Extract metadata for chunking
            personality_ns = doc.metadata["personality_ns"]
            content_type = "documentation"

            # Chunk document
            nodes = tag_and_chunk([doc], personality_ns, content_type)

            # Upsert to Qdrant
            upsert_nodes(client, nodes)

            # Record in hash store
            new_ids = [node.node_id for node in nodes]
            record_synthetic_file(store, file_name, current_sha, new_ids)

        except (FileNotFoundError, KeyError, ValueError) as e:
            print(f"[synthetic] Warning: Skipping {file_name} - {e}")
            error_count += 1
            continue
        except Exception as e:
            print(f"[synthetic] Warning: Unexpected error processing {file_name} - {e}")
            error_count += 1
            continue

    # Save hash store
    save_synthetic_store(store)

    print(
        f"[synthetic] synthetic — "
        f"new: {new_count}, updated: {changed_count}, skipped (unchanged): {skipped_count}, errors: {error_count}"
    )


if __name__ == "__main__":
    # Google Drive ingestion
    try:
        # ingest_folder( TECHNICAL_FOLDER_ID,    "technical",    "documentation")
        # ingest_folder(NONTECHNICAL_FOLDER_ID, "nontechnical", "documentation")
        # ingest_github()
        ingest_synthetic()
    finally:
        client.close()

    print("\n[ingest] Full ingestion complete.")
