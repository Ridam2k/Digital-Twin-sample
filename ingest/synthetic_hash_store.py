"""
Hash store for synthetic JSON documents.

Tracks SHA256 content hashes and Qdrant point IDs to enable:
- Change detection (skip re-ingesting unchanged files)
- Efficient updates (delete old chunks, insert new ones)
- Deduplication (avoid wasteful re-embedding)

Store structure:
{
    "filename.json": {
        "content_sha": "a3f5c8...",           # SHA256 hash of file contents
        "point_ids": ["uuid1", "uuid2", ...]  # Qdrant point IDs for this file's chunks
    }
}
"""

import json
from pathlib import Path
from config import SYNTHETIC_HASH_STORE_PATH


def load_synthetic_store() -> dict:
    """
    Load the synthetic data hash store from disk.

    Returns:
        dict: Hash store mapping filenames to {content_sha, point_ids}
              Empty dict if store doesn't exist yet
    """
    path = Path(SYNTHETIC_HASH_STORE_PATH)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, Exception):
        # If store is corrupted, return empty dict and start fresh
        return {}


def save_synthetic_store(store: dict) -> None:
    """
    Persist the synthetic data hash store to disk.

    Args:
        store: Hash store dict to save
    """
    path = Path(SYNTHETIC_HASH_STORE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2))


def is_synthetic_changed(store: dict, file_name: str, current_sha: str) -> bool:
    """
    Check if a synthetic file has changed since last ingestion.

    Returns True if:
    - File is new (not in store)
    - File's SHA256 hash has changed

    Args:
        store: The hash store dict
        file_name: Filename (e.g., "technical_project_writeup_000.json")
        current_sha: SHA256 hash of current file contents

    Returns:
        bool: True if file should be re-ingested, False if unchanged
    """
    entry = store.get(file_name)
    if entry is None:
        return True  # New file
    return entry.get("content_sha") != current_sha


def record_synthetic_file(
    store: dict, file_name: str, content_sha: str, point_ids: list[str]
) -> None:
    """
    Record that a file was ingested with this SHA and produced these point IDs.

    Args:
        store: The hash store dict
        file_name: Filename (e.g., "technical_project_writeup_000.json")
        content_sha: SHA256 hash of file contents
        point_ids: List of Qdrant point IDs generated from this file's chunks
    """
    store[file_name] = {
        "content_sha": content_sha,
        "point_ids": point_ids,
    }


def get_old_synthetic_point_ids(store: dict, file_name: str) -> list[str]:
    """
    Get the Qdrant point IDs previously produced by this file (for deletion).

    Args:
        store: The hash store dict
        file_name: Filename (e.g., "technical_project_writeup_000.json")

    Returns:
        list[str]: List of point IDs, or empty list if file not found
    """
    entry = store.get(file_name)
    if entry is None:
        return []
    return entry.get("point_ids", [])
