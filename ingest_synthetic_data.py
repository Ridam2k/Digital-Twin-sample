"""
Ingest synthetic JSON documents into Qdrant vector database.

This script:
1. Scans data/sources/ for JSON files
2. Loads and validates each document
3. Chunks using SentenceSplitter (768 tokens, 120 overlap)
4. Generates embeddings using text-embedding-3-small
5. Upserts to Qdrant collection with metadata
6. Tracks changes using SHA256 hash store

Usage:
    python scripts/ingest_synthetic_data.py [--sources-dir data/sources] [--force]

Options:
    --sources-dir DIR    Directory containing synthetic JSON files (default: data/sources)
    --force              Force re-ingestion of all files, ignoring hash store
"""

import argparse
import hashlib
import json
from pathlib import Path

from ingest.synthetic_reader import load_synthetic_document
from ingest.synthetic_hash_store import (
    load_synthetic_store,
    save_synthetic_store,
    is_synthetic_changed,
    record_synthetic_file,
    get_old_synthetic_point_ids,
)
from ingest.chunker import tag_and_chunk
from ingest.embedder import upsert_nodes, delete_points_by_ids


def compute_file_sha(file_path: Path) -> str:
    """
    Compute SHA256 hash of file contents.

    Args:
        file_path: Path to file

    Returns:
        str: Hex digest of SHA256 hash
    """
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def ingest_synthetic_data(sources_dir: str, force: bool = False) -> None:
    """
    Ingest all synthetic JSON documents from a directory into Qdrant.

    Args:
        sources_dir: Directory containing JSON files
        force: If True, re-ingest all files ignoring hash store
    """
    sources_path = Path(sources_dir)

    # Validate sources directory
    if not sources_path.exists():
        print(f"Error: Sources directory does not exist: {sources_dir}")
        print(f"Please run 'make generate' first to create synthetic documents.")
        return

    # Load hash store
    store = load_synthetic_store()

    # Statistics tracking
    stats = {"new": 0, "changed": 0, "skipped": 0, "errors": 0}

    # Scan for JSON files
    json_files = sorted(sources_path.glob("*.json"))

    if not json_files:
        print(f"No JSON files found in {sources_dir}")
        print(f"Please run 'make generate' first to create synthetic documents.")
        return

    print(f"\n{'='*80}")
    print(f"Synthetic Data Ingestion")
    print(f"{'='*80}")
    print(f"Sources directory: {sources_dir}")
    print(f"Found {len(json_files)} JSON files")
    print(f"Force re-ingest: {force}")
    print(f"{'='*80}\n")

    # Process each file
    for json_file in json_files:
        file_name = json_file.name
        current_sha = compute_file_sha(json_file)

        # Check if changed (skip if not forced and not changed)
        if not force and not is_synthetic_changed(store, file_name, current_sha):
            stats["skipped"] += 1
            print(f"[SKIP] {file_name} (unchanged)")
            continue

        print(f"\n[PROC] {file_name}")

        try:
            # Load document
            doc = load_synthetic_document(json_file)

            # Extract metadata for chunking
            personality_ns = doc.metadata["personality_ns"]
            content_type = doc.metadata["content_type"]

            print(f"  → personality_ns: {personality_ns}")
            print(f"  → content_type: {content_type}")

            # Delete old chunks if updating existing file
            old_point_ids = get_old_synthetic_point_ids(store, file_name)
            if old_point_ids:
                print(f"  → Deleting {len(old_point_ids)} old chunks...")
                delete_points_by_ids(old_point_ids)
                stats["changed"] += 1
            else:
                stats["new"] += 1

            # Chunk document
            nodes = tag_and_chunk([doc], personality_ns, content_type)
            print(f"  → Created {len(nodes)} chunks")

            # Upsert to Qdrant
            print(f"  → Embedding and upserting to Qdrant...")
            upsert_nodes(nodes)

            # Record in hash store
            new_point_ids = [node.node_id for node in nodes]
            record_synthetic_file(store, file_name, current_sha, new_point_ids)

            print(f"  ✓ Ingested successfully")

        except FileNotFoundError as e:
            print(f"  ✗ Error: {e}")
            stats["errors"] += 1
            continue

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"  ✗ Validation error: {e}")
            stats["errors"] += 1
            continue

        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            stats["errors"] += 1
            continue

    # Save hash store
    save_synthetic_store(store)

    # Print summary
    print(f"\n{'='*80}")
    print(f"Ingestion Complete")
    print(f"{'='*80}")
    print(f"  New files:           {stats['new']}")
    print(f"  Changed files:       {stats['changed']}")
    print(f"  Skipped (unchanged): {stats['skipped']}")
    print(f"  Errors:              {stats['errors']}")
    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest synthetic JSON documents into Qdrant vector database"
    )
    parser.add_argument(
        "--sources-dir",
        default="data/sources",
        help="Directory containing synthetic JSON files (default: data/sources)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-ingestion of all files, ignoring hash store",
    )
    args = parser.parse_args()

    ingest_synthetic_data(args.sources_dir, args.force)


if __name__ == "__main__":
    main()
