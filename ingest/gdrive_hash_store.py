import json
from pathlib import Path
from config import GDRIVE_HASH_STORE_PATH


def load_gdrive_hash_store() -> dict:
    """Load the Google Drive hash store"""
    path = Path(GDRIVE_HASH_STORE_PATH)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_gdrive_hash_store(store: dict) -> None:
    """Persist the Google Drive hash store to disk."""
    path = Path(GDRIVE_HASH_STORE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2))


def is_gdrive_changed(store: dict, file_id: str, modified_time: str) -> bool:
    """
    Returns True if the file is new or its modified_time has changed since last ingest.

    Args:
        store: The hash store dict
        file_id: Google Drive file ID
        modified_time: ISO 8601 timestamp from Google Drive API (e.g., "2024-01-15T10:30:00.000Z")
    """
    entry = store.get(file_id)
    if entry is None:
        return True
    return entry["modified_time"] != modified_time


def record_gdrive_file(store: dict, file_id: str, modified_time: str, point_ids: list[str]) -> None:
    """
    Record that a file was ingested with this modified_time and produced these Qdrant point IDs.

    Args:
        store: The hash store dict
        file_id: Google Drive file ID
        modified_time: ISO 8601 timestamp from Google Drive API
        point_ids: List of Qdrant point IDs generated from this file's chunks
    """
    store[file_id] = {
        "modified_time": modified_time,
        "point_ids": point_ids,
    }


def get_old_gdrive_point_ids(store: dict, file_id: str) -> list[str]:
    """
    Return the Qdrant point IDs previously produced by this file (for deletion).

    Args:
        store: The hash store dict
        file_id: Google Drive file ID

    Returns:
        List of point IDs, or empty list if file not found
    """
    entry = store.get(file_id)
    if entry is None:
        return []
    return entry.get("point_ids", [])
