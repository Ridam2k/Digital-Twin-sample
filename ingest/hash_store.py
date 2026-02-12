import json
from pathlib import Path
from config import HASH_STORE_PATH


def load_hash_store() -> dict:
    path = Path(HASH_STORE_PATH)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_hash_store(store: dict) -> None:
    path = Path(HASH_STORE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2))


def is_changed(store: dict, file_key: str, current_sha: str) -> bool:
    """Returns True if the file is new or its SHA has changed since last ingest."""
    entry = store.get(file_key)
    if entry is None:
        return True
    return entry["git_sha"] != current_sha


def record_file(store: dict, file_key: str, git_sha: str, point_ids: list[str]) -> None:
    """Record that a file was ingested with this SHA and produced these Qdrant point IDs."""
    store[file_key] = {
        "git_sha":   git_sha,
        "point_ids": point_ids,
    }


def get_old_point_ids(store: dict, file_key: str) -> list[str]:
    """Return the Qdrant point IDs previously produced by this file (for deletion)."""
    entry = store.get(file_key)
    if entry is None:
        return []
    return entry.get("point_ids", [])