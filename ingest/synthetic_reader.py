"""
Reader for synthetic JSON documents.

Loads JSON files from data/sources/ and converts them to LlamaIndex Document objects
with proper metadata for ingestion into Qdrant.

Expected JSON structure:
{
    "doc_title": "Building a RAG Pipeline for IB Analysts",
    "source_url": "",
    "personality_ns": "technical",
    "content_type": "project_writeup",
    "body": "Long-form text content..."
}
"""

import json
from pathlib import Path
from typing import Union
from llama_index.core.schema import Document
from config import PERSONALITY_NAMESPACES


def load_synthetic_document(file_path: Union[str, Path]) -> Document:
    """
    Load a single synthetic JSON file and convert to LlamaIndex Document.

    Args:
        file_path: Path to JSON file

    Returns:
        Document: LlamaIndex Document with text and metadata

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
        KeyError: If required fields are missing
        ValueError: If field validation fails
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Synthetic document not found: {file_path}")

    # Load JSON
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in {path.name}: {e.msg}", e.doc, e.pos
        )

    # Validate required fields
    required_fields = ["doc_title", "personality_ns", "content_type", "body"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise KeyError(
            f"Missing required fields in {path.name}: {', '.join(missing)}"
        )

    # Validate personality_ns
    personality_ns = data["personality_ns"]
    if personality_ns not in PERSONALITY_NAMESPACES:
        raise ValueError(
            f"Invalid personality_ns '{personality_ns}' in {path.name}. "
            f"Must be one of: {PERSONALITY_NAMESPACES}"
        )

    # Validate body is non-empty
    body = data["body"].strip()
    if not body:
        raise ValueError(f"Empty body in {path.name}")

    # Create Document with metadata
    doc = Document(
        text=body,
        metadata={
            "doc_id": path.name,  # Use filename as unique ID
            "doc_title": data["doc_title"],
            "source_url": data.get("source_url", ""),  # Optional field
            "personality_ns": personality_ns,
            "content_type": data["content_type"],
            "source_type": "synthetic",  # Mark as synthetic data
            "file_name": path.name,
        },
    )

    return doc


def load_synthetic_documents(sources_dir: Union[str, Path]) -> list[Document]:
    """
    Load all synthetic JSON documents from a directory.

    Args:
        sources_dir: Directory containing JSON files

    Returns:
        list[Document]: List of LlamaIndex Documents

    Note:
        Skips invalid files with warnings rather than failing completely.
        This allows partial ingestion even if some files are malformed.
    """
    sources_path = Path(sources_dir)

    if not sources_path.exists():
        print(f"Warning: Sources directory does not exist: {sources_dir}")
        return []

    if not sources_path.is_dir():
        print(f"Warning: Sources path is not a directory: {sources_dir}")
        return []

    documents = []
    json_files = list(sources_path.glob("*.json"))

    for json_file in json_files:
        try:
            doc = load_synthetic_document(json_file)
            documents.append(doc)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Warning: Skipping {json_file.name}: {e}")
            continue
        except Exception as e:
            print(f"Warning: Unexpected error loading {json_file.name}: {e}")
            continue

    return documents
