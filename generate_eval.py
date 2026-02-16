import json
import hashlib
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Any

from openai import OpenAI
from qdrant_client import QdrantClient

from config import (
    OPENAI_PVT_KEY,
    QDRANT_URL,
    QDRANT_API_KEY,
    COLLECTION_NAME,
)

OUTPUT_FILE = Path("eval_set.json")
MODEL = "gpt-5.1"

client = OpenAI(api_key=OPENAI_PVT_KEY)
qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

SYSTEM_PROMPT = """
You are an evaluation dataset generator for a RAG-based digital twin system.
Generate realistic, diverse test queries to evaluate semantic retrieval.

Generate queries across three difficulty levels:
EASY (direct): lexically close; includes a keyword naturally.
MEDIUM (paraphrased): same intent, different phrasing; no direct keyword overlap.
HARD (inferential): indirect; requires bridging abstraction; not just synonyms.

Rules:
1) Output ONLY valid JSON (no markdown).
2) Each query must be answerable from the provided SOURCE TEXT.
3) Hard queries must be genuinely indirect.
4) Vary query length.
5) Do not echo seed field verbatim.
""".strip()

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def doc_title_hash(namespace: str, doc_title: str) -> str:
    # include namespace to avoid collisions across namespaces
    return sha256(f"{namespace}::{doc_title}".strip())

def extract_doc_title(payload: dict) -> str:
    file_path = payload.get("file_path") or payload.get("file path")
    if file_path:
        return file_path.split("/")[-1]
    title = payload.get("doc_title")
    if title:
        return title
    return (payload.get("file_name") or payload.get("file name") or "")

def build_user_prompt(source_text: str, doc_title: str, namespace: str,
                      n_easy: int = 1, n_medium: int = 1, n_hard: int = 1) -> str:
    return f"""
SOURCE DOCUMENT: {doc_title}
NAMESPACE: {namespace}

SOURCE TEXT:
\"\"\"
{source_text}
\"\"\"

Generate exactly {n_easy} EASY, {n_medium} MEDIUM, and {n_hard} HARD queries.

Return a JSON array with schema per item:
{{
  "query":      "<test query>",
  "namespace":  "{namespace}",
  "difficulty": "<easy|medium|hard>",
  "query_type": "<direct|paraphrased|inferential|cross_domain|behavioural>"
}}
""".strip()

def fetch_documents_from_qdrant() -> List[Dict[str, Any]]:
    """
    Reconstruct full documents by grouping chunks by (personality_ns, doc_title)
    """
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)

    offset = None
    while True:
        points, next_offset = qdrant.scroll(
            collection_name=COLLECTION_NAME,
            limit=1000,
            with_payload=True,
            with_vectors=False,
            offset=offset,
        )
        if not points:
            break

        for p in points:
            payload = p.payload or {}
            ns = payload.get("personality_ns")
            title = extract_doc_title(payload)
            text = payload.get("text") or ""
            if not ns or not title or not text.strip():
                continue

            grouped[(ns, title)].append({
                "text": text,
                "chunk_index": int(payload.get("chunk_index", 0)),
                "content_type": payload.get("content_type", ""),
                "source_url": payload.get("source_url", ""),
            })

        if next_offset is None:
            break
        offset = next_offset

    docs: List[Dict[str, Any]] = []
    for (ns, title), chunks in grouped.items():
        chunks_sorted = sorted(chunks, key=lambda c: c["chunk_index"])
        full_text = "\n".join(c["text"] for c in chunks_sorted)
        docs.append({
            "namespace": ns,
            "doc_title": title,
            "doc_title_hash": doc_title_hash(ns, title),
            "doc_hash": sha256(full_text),
            "full_text": full_text,
            "content_type": chunks_sorted[0].get("content_type", "") if chunks_sorted else "",
            "source_url": chunks_sorted[0].get("source_url", "") if chunks_sorted else "",
        })

    return docs

def main():
    docs = fetch_documents_from_qdrant()
    print(f"Found {len(docs)} reconstructed documents in Qdrant")

    all_rows: List[Dict[str, Any]] = []

    for doc in docs:
        ns = doc["namespace"]
        title = doc["doc_title"]
        full_text = doc["full_text"]

        print(f"Generating queries for: [{ns}] {title}")

        prompt = build_user_prompt(
            source_text=full_text,
            doc_title=title,
            namespace=ns,
            n_easy=1, n_medium=1, n_hard=1,
        )

        resp = client.chat.completions.create(
            model=MODEL,
            max_completion_tokens=800,
            temperature=0.7,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        generated_rows = json.loads(raw.strip())

        for row in generated_rows:
            row["gold"] = {
                "doc_title": title,
                "doc_title_hash": doc["doc_title_hash"],
                "doc_hash": doc["doc_hash"],
            }
            row.pop("expected_source", None)

        all_rows.extend(generated_rows)

    OUTPUT_FILE.write_text(json.dumps(all_rows, indent=2))
    print(f"\nDone. {len(all_rows)} total eval rows written to {OUTPUT_FILE}")

    by_difficulty = Counter(r["difficulty"] for r in all_rows)
    by_namespace = Counter(r["namespace"] for r in all_rows)
    print(f"Difficulty split: {dict(by_difficulty)}")
    print(f"Namespace split:  {dict(by_namespace)}")

if __name__ == "__main__":
    main()
