from ingest.gdrive_reader import get_gdrive_reader
from ingest.chunker import tag_and_chunk
from ingest.embedder import upsert_nodes
from config import TECHNICAL_FOLDER_ID, NONTECHNICAL_FOLDER_ID, GITHUB_REPOS
from ingest.github_reader import fetch_repo_files, files_to_documents
from ingest.hash_store import (
    load_hash_store, save_hash_store,
    is_changed, record_file, get_old_point_ids,
)
from ingest.embedder import delete_points_by_ids, upsert_nodes
from ingest.chunker import tag_and_chunk

def ingest_folder(folder_id: str, personality_ns: str, content_type: str) -> None:
    print(f"\n[ingest] Starting: namespace='{personality_ns}', content_type='{content_type}'")
    reader = get_gdrive_reader(folder_id)
    docs = reader.load_data()
    print(f"[ingest] Loaded {len(docs)} documents.")

    nodes = tag_and_chunk(docs, personality_ns, content_type)
    print(f"[ingest] Produced {len(nodes)} chunks.")

    upsert_nodes(nodes)


def ingest_github(repos: list[str] = None) -> None:
    """
    Ingest GitHub repos with hash-based change detection.
    Only files whose git SHA changed since last run are re-embedded.
    """
    if repos is None:
        repos = GITHUB_REPOS

    store = load_hash_store()

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
                delete_points_by_ids(old_ids)
                changed_count += 1
            else:
                new_count += 1

            # Ingest the (new or changed) file
            docs  = files_to_documents([f])
            nodes = tag_and_chunk(docs, personality_ns="technical", content_type="project_writeup")
            upsert_nodes(nodes)

            # Record new point IDs and SHA in hash store
            new_ids = [node.node_id for node in nodes]
            record_file(store, key, f["git_sha"], new_ids)

        save_hash_store(store)
        print(
            f"[github] {repo_name} — "
            f"new: {new_count}, updated: {changed_count}, skipped (unchanged): {skipped_count}"
        )


if __name__ == "__main__":
    # Google Drive ingestion
    ingest_folder(TECHNICAL_FOLDER_ID,    "technical",    "project_writeup")
    ingest_folder(NONTECHNICAL_FOLDER_ID, "nontechnical", "notes")

    # GitHub ingestion 
    ingest_github()

    print("\n[ingest] Full ingestion complete.")
