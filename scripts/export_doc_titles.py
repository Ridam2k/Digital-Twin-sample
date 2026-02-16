import json
import datetime as dt
from pathlib import Path

from qdrant_client import QdrantClient

from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
from ingest.gdrive_reader import RateLimitedGoogleDriveReader

OUTPUT_PATH = Path("data/doc_titles.json")
SCROLL_LIMIT = 1000
GDRIVE_HASH_STORE_PATH = Path("data/gdrive_hash_store.json")
GDRIVE_NAME_MAP_PATH = Path("data/gdrive_name_map.json")


def _load_gdrive_id_set() -> set[str]:
    if not GDRIVE_HASH_STORE_PATH.exists():
        return set()
    try:
        data = json.loads(GDRIVE_HASH_STORE_PATH.read_text())
        return set(data.keys())
    except Exception:
        return set()


def _load_gdrive_name_map() -> dict[str, str]:
    if not GDRIVE_NAME_MAP_PATH.exists():
        return {}
    try:
        return json.loads(GDRIVE_NAME_MAP_PATH.read_text())
    except Exception:
        return {}


def _save_gdrive_name_map(name_map: dict[str, str]) -> None:
    GDRIVE_NAME_MAP_PATH.write_text(json.dumps(name_map, indent=2))


def _resolve_gdrive_names(file_ids: list[str]) -> dict[str, str]:
    if not file_ids:
        return {}
    name_map = _load_gdrive_name_map()
    missing = [fid for fid in file_ids if fid not in name_map]
    if not missing:
        return name_map

    if not Path("token.json").exists() or not Path("credentials.json").exists():
        return name_map

    reader = RateLimitedGoogleDriveReader(
        credentials_path="credentials.json",
        token_path="token.json",
        folder_id=None,
    )

    for fid in missing:
        try:
            info = reader.get_resource_info(fid)
            file_path = (info.get("file_path") or "").strip()
            name = file_path.split("/")[-1] if file_path else fid
            name_map[fid] = name
        except Exception:
            name_map[fid] = fid

    _save_gdrive_name_map(name_map)
    return name_map


def _maybe_append_ext(name: str, ext: str) -> str:
    if not ext:
        return name
    if name.lower().endswith(f".{ext.lower()}"):
        return name
    return f"{name}.{ext}"


def _extract_title_from_payload(payload: dict) -> str:
    file_path = payload.get("file_path") or payload.get("file path")
    if file_path:
        return file_path.split("/")[-1]
    return (payload.get("doc_title") or payload.get("file_name") or "").strip()


def _resolve_titles(titles: list[str]) -> list[str]:
    gdrive_ids = _load_gdrive_id_set()
    ids_to_resolve = []
    for t in titles:
        if t in gdrive_ids:
            ids_to_resolve.append(t)
            continue
        if "." in t:
            stem = t.rsplit(".", 1)[0]
            if stem in gdrive_ids:
                ids_to_resolve.append(stem)

    name_map = _resolve_gdrive_names(ids_to_resolve)
    mapped = set()
    for t in titles:
        if t in name_map:
            mapped.add(name_map[t])
            continue
        if "." in t:
            stem, ext = t.rsplit(".", 1)
            if stem in name_map:
                mapped.add(_maybe_append_ext(name_map[stem], ext))
                continue
        mapped.add(t)

    return sorted(mapped)


def fetch_unique_doc_titles(client: QdrantClient) -> list[str]:
    titles: set[str] = set()
    offset = None

    while True:
        points, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=SCROLL_LIMIT,
            with_payload=["doc_title", "file_name", "file_path", "file path"],
            with_vectors=False,
            offset=offset,
        )
        if not points:
            break

        for p in points:
            payload = p.payload or {}
            title = _extract_title_from_payload(payload)
            if title:
                titles.add(title)

        if next_offset is None:
            break
        offset = next_offset

    return _resolve_titles(sorted(titles))


def main() -> None:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    titles = fetch_unique_doc_titles(client)
    client.close()

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
